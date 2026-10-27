#!/usr/bin/env python3
"""
reproduce.py - One-Command Master Scientific Replication Script

Replicates all empirical findings, EVT tail latency models, parametric ANOVA statistics,
closed-form safe overcommit frontiers, controller benchmarks, and publication figures
for the paper:
"Characterizing Micro-Architectural Memory Pressure Stall Dynamics, Dynamic Cgroup V2
Overcommit, and Tail-Resilient Eviction Avoidance in Dense Cloud Multi-Tenancy"

Usage:
    python reproduce.py
"""

import os
import sys
import subprocess
import time

def print_banner(text):
    print("\n" + "=" * 75)
    print(f"  {text}")
    print("=" * 75)

def run_step(step_name, cmd):
    print(f"\n>>> Running: {step_name}...")
    start = time.time()
    res = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    if res.returncode != 0:
        print(f" [ERROR] {step_name} failed in {elapsed:.2f}s:")
        print(res.stderr)
        return False
    else:
        print(f" [SUCCESS] {step_name} completed in {elapsed:.2f}s.")
        if res.stdout.strip():
            # Print brief excerpt of stdout
            lines = res.stdout.strip().split("\n")
            excerpt = lines[:4] + (["..."] if len(lines) > 8 else []) + (lines[-3:] if len(lines) > 8 else lines[4:])
            for line in excerpt:
                print(f"    {line}")
        return True

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    print_banner("cgroup-psi-shed: Complete Scientific Replication Pipeline")
    print(" Authors: Devarsh Patel, Adarsh Singh, Umamaheshwari M (VIT Vellore)")
    print(f" Working Directory: {root_dir}")

    # Step 1: EVT Tail Modeling & GLM Frontier
    if not run_step("EVT Tail Latency Modeler (GPD & GLM Frontier)", ["src/tail_latency_modeler.py"]):
        sys.exit(1)

    # Step 2: Parametric ANOVA & Effect Sizes
    if not run_step("Two-Way Parametric ANOVA & Mitigation Analysis", ["src/parametric_stats_engine.py"]):
        sys.exit(1)

    # Step 3: Publication Figure Generation
    if not run_step("Generate 10 Publication-Quality Figures (Vector PDF & PNG)", ["src/generate_all_figures.py"]):
        sys.exit(1)

    # Step 4: PSI-Shed Controller Daemon Simulation
    if not run_step("PSI-Shed Daemon Non-Linear Control Law Verification", ["src/psi_shed_daemon.py", "--demo"]):
        sys.exit(1)

    print_banner("ALL SCIENTIFIC ARTIFACTS REPRODUCED SUCCESSFULLY")
    print(" Generated Artifacts:")
    print("  - Figures: figures/fig01.pdf through figures/fig10.pdf (and figures/png/)")
    print("  - Tables:  tables/tab01_taxonomy.tex through tables/tab05_mitigation.tex")
    print("  - Data:    data/processed/omega_star_frontier.csv, evt_gpd_summary.csv")
    print("=" * 75)

if __name__ == "__main__":
    main()
