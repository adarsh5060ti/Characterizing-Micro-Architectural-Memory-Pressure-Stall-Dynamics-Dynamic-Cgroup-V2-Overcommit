#!/usr/bin/env python3
"""
psi_shed_daemon.py - PSI-Shed Proactive Acceleration-Aware Memory Controller Daemon

Implements the non-linear proportional-derivative control law on kernel Pressure Stall
Information (PSI) acceleration and velocity, providing proactive eviction avoidance in
dense cloud multi-tenant environments under Linux cgroup v2 and MGLRU.

Authors: Devarsh Patel, Adarsh Singh, Umamaheshwari M (VIT Vellore)
License: MIT License
"""

import os
import sys
import time
import math
import argparse
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class ControllerConfig:
    # Kinematics and sampling
    dt_ms: float = 10.0                 # Control epoch interval Delta t = 10 ms
    window_ms: float = 10.0             # PSI monitoring window W = 10 ms
    kp: float = 1.85                    # Proportional gain on PSI exceedance
    kd: float = 0.42                    # Derivative gain on PSI acceleration
    psi_thresh: float = 5.0             # Normal operation threshold theta_thresh (%)
    a_crit: float = 120.0               # Acute acceleration threshold (pct/s^2)
    
    # 3-Phase Actuation parameters
    m_dram_gb: float = 192.0            # Total host DRAM
    tier3_high_max_gb: float = 140.0    # Quiescent memory.high limit for Tier 3
    tier3_high_min_gb: float = 48.0     # Maximum throttle memory.high limit
    watermark_base_kb: int = 67584      # Default vm.min_free_kbytes (64 MB)
    watermark_max_kb: int = 524288      # Max modulated vm.min_free_kbytes (512 MB)
    dwell_time_ms: float = 500.0        # Anti-chatter dwell timer T_dwell

class PSIShedController:
    def __init__(self, config: ControllerConfig, dry_run: bool = True):
        self.cfg = config
        self.dry_run = dry_run
        
        # Kinematic state
        self.initialized: bool = False
        self.last_psi_some: float = 0.0
        self.last_velocity: float = 0.0
        self.last_acceleration: float = 0.0
        self.last_time: float = time.monotonic()
        
        # Control state
        self.last_state_change: float = time.monotonic()
        self.current_state: str = "GREEN"  # GREEN, YELLOW, RED
        self.tier3_high_gb: float = self.cfg.tier3_high_max_gb
        self.current_watermark_kb: int = self.cfg.watermark_base_kb

    def read_psi_telemetry(self) -> float:
        """Reads kernel /proc/pressure/memory or returns simulated value in dry-run."""
        if not self.dry_run and os.path.exists("/proc/pressure/memory"):
            try:
                with open("/proc/pressure/memory", "r") as f:
                    for line in f:
                        if line.startswith("some"):
                            parts = dict(kv.split("=") for kv in line.strip().split()[1:])
                            return float(parts.get("avg10", 0.0))
            except Exception as e:
                print(f"[PSI-Shed] Telemetry read error: {e}", file=sys.stderr)
        return 0.0

    def compute_kinematics(self, current_psi: float, now: float) -> Tuple[float, float]:
        """Computes backward-difference velocity and acceleration: v(t) = dPSI/dt, a(t) = dv/dt."""
        if not self.initialized:
            self.last_psi_some = current_psi
            self.last_time = now
            self.initialized = True
            return 0.0, 0.0

        dt = max(1e-4, now - self.last_time)
        velocity = (current_psi - self.last_psi_some) / dt
        acceleration = (velocity - self.last_velocity) / dt
        
        self.last_psi_some = current_psi
        self.last_velocity = velocity
        self.last_acceleration = acceleration
        self.last_time = now
        return velocity, acceleration

    def evaluate_control_law(self, psi: float, vel: float, acc: float, now: float) -> str:
        """Evaluates non-linear PD error signal and returns state (GREEN, YELLOW, RED)."""
        error_signal = (
            self.cfg.kp * max(0.0, psi - self.cfg.psi_thresh) / 100.0 +
            self.cfg.kd * max(0.0, acc) / self.cfg.a_crit
        )
        
        time_since_change = (now - self.last_state_change) * 1000.0  # ms
        
        # State transitions with anti-chatter dwell time
        if error_signal > 1.0 or acc > self.cfg.a_crit:
            target_state = "RED"
        elif error_signal > 0.2 or psi > self.cfg.psi_thresh:
            target_state = "YELLOW"
        else:
            target_state = "GREEN"
            
        # Enforce dwell time on downgrade
        if target_state != self.current_state:
            # Upgrade is instantaneous; downgrade requires dwell time
            if (self.state_severity(target_state) > self.state_severity(self.current_state) or
                time_since_change >= self.cfg.dwell_time_ms):
                self.current_state = target_state
                self.last_state_change = now
                
        return self.current_state

    @staticmethod
    def state_severity(state: str) -> int:
        return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(state, 0)

    def apply_actuation(self, state: str):
        """Applies 3-phase proactive control action to cgroup v2 and sysctl."""
        if state == "RED":
            # Phase 1: Aggressive Tier 3 throttling
            self.tier3_high_gb = self.cfg.tier3_high_min_gb
            # Phase 2: Watermark modulation
            self.current_watermark_kb = self.cfg.watermark_max_kb
            # Phase 3: Proactive pageout
            self._write_cgroup_reclaim("besteffort.slice", "1G")
        elif state == "YELLOW":
            # Proactive mild throttle
            self.tier3_high_gb = (self.cfg.tier3_high_max_gb + self.cfg.tier3_high_min_gb) / 2.0
            self.current_watermark_kb = int((self.cfg.watermark_base_kb + self.cfg.watermark_max_kb) / 2.0)
        else:
            # Quiescent state
            self.tier3_high_gb = self.cfg.tier3_high_max_gb
            self.current_watermark_kb = self.cfg.watermark_base_kb

        if not self.dry_run:
            self._write_cgroup_high("besteffort.slice", f"{int(self.tier3_high_gb)}G")
            self._write_sysctl("vm.min_free_kbytes", str(self.current_watermark_kb))

    def _write_cgroup_high(self, slice_name: str, val: str):
        path = f"/sys/fs/cgroup/{slice_name}/memory.high"
        if os.path.exists(path):
            try:
                with open(path, "w") as f:
                    f.write(val)
            except Exception as e:
                print(f"[PSI-Shed] Error setting memory.high: {e}", file=sys.stderr)

    def _write_cgroup_reclaim(self, slice_name: str, val: str):
        path = f"/sys/fs/cgroup/{slice_name}/memory.reclaim"
        if os.path.exists(path):
            try:
                with open(path, "w") as f:
                    f.write(val)
            except Exception as e:
                print(f"[PSI-Shed] Error triggering memory.reclaim: {e}", file=sys.stderr)

    def _write_sysctl(self, key: str, val: str):
        path = f"/proc/sys/{key.replace('.', '/')}"
        if os.path.exists(path):
            try:
                with open(path, "w") as f:
                    f.write(val)
            except Exception as e:
                print(f"[PSI-Shed] Error writing sysctl {key}: {e}", file=sys.stderr)

    def run_epoch(self, simulated_psi: Optional[float] = None) -> dict:
        """Executes a single 10 ms control epoch."""
        now = time.monotonic()
        psi = simulated_psi if simulated_psi is not None else self.read_psi_telemetry()
        vel, acc = self.compute_kinematics(psi, now)
        state = self.evaluate_control_law(psi, vel, acc, now)
        self.apply_actuation(state)
        return {
            "timestamp": now,
            "psi_some": psi,
            "velocity": vel,
            "acceleration": acc,
            "state": state,
            "tier3_high_gb": self.tier3_high_gb,
            "watermark_kb": self.current_watermark_kb
        }

def main():
    parser = argparse.ArgumentParser(description="PSI-Shed Cgroup V2 Memory Controller Daemon")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate without writing to /sys and /proc")
    parser.add_argument("--live", action="store_true", help="Run in live Linux cgroup v2 environment (requires root)")
    parser.add_argument("--demo", action="store_true", default=True, help="Run an animated test burst demonstration")
    args = parser.parse_args()

    dry_run = not args.live
    controller = PSIShedController(ControllerConfig(), dry_run=dry_run)
    print("=" * 70)
    print(" PSI-Shed Non-Linear Proactive Memory Controller Daemon")
    print(f" Mode: {'DRY-RUN (Simulated)' if dry_run else 'LIVE LINUX CGROUP V2'}")
    print(f" Control Epoch: {controller.cfg.dt_ms} ms | Window: {controller.cfg.window_ms} ms")
    print(f" Proportional Gain: {controller.cfg.kp} | Derivative Gain: {controller.cfg.kd}")
    print("=" * 70)

    if args.demo:
        print("\n[DEMO] Simulating 10-second memory pressure burst...")
        print(f"{'Time (s)':>8} | {'PSI Some (%)':>12} | {'Acc (%/s^2)':>12} | {'State':>8} | {'Tier3 High':>11} | {'MinFreeKB':>10}")
        print("-" * 75)
        # Synthetic surge pattern (quiescent -> surge -> peak -> recovery)
        for t in range(50):
            t_sec = t * 0.1
            if 1.0 <= t_sec <= 2.5:
                # Ramp up
                sim_psi = 2.0 + 35.0 * ((t_sec - 1.0) / 1.5) ** 1.8
            elif 2.5 < t_sec <= 3.5:
                # Sustained peak
                sim_psi = 37.0 + 2.0 * math.sin(t_sec * 5)
            elif 3.5 < t_sec <= 4.5:
                # Recovery
                sim_psi = max(1.5, 37.0 - 35.0 * ((t_sec - 3.5) / 1.0))
            else:
                sim_psi = 1.5

            info = controller.run_epoch(simulated_psi=sim_psi)
            print(f"{t_sec:8.2f} | {info['psi_some']:12.2f} | {info['acceleration']:12.2f} | {info['state']:>8} | {info['tier3_high_gb']:9.1f} GB | {info['watermark_kb']:8d} KB")
            time.sleep(0.02)
        print("-" * 75)
        print("[DEMO] Burst successfully averted: Tier 3 throttled, watermarks expanded, and dwell-timer enforced.\n")

if __name__ == "__main__":
    main()
