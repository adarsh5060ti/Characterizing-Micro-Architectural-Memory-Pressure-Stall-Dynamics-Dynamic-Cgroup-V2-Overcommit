# PSI-Shed: Proactive Acceleration-Aware Memory Pressure Stall Avoidance in Dense Cloud Multi-Tenancy

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Linux: 6.8+ (MGLRU)](https://img.shields.io/badge/Kernel-Linux%206.8%2B%20(MGLRU)-orange.svg)](https://www.kernel.org/)
[![Status: Peer-Reviewed Reproduction](https://img.shields.io/badge/Reproducibility-Verified%20(0%20errors)-success.svg)](reproduce.py)

Official open-source artifact and replication repository for the research paper:  
> **"Characterizing Micro-Architectural Memory Pressure Stall Dynamics, Dynamic Cgroup V2 Overcommit, and Tail-Resilient Eviction Avoidance in Dense Cloud Multi-Tenancy"**  
> *Devarsh Patel, Adarsh Singh, and Umamaheshwari M*  
> School of Computer Science & Engineering (SCOPE), Vellore Institute of Technology (VIT), Vellore, Tamil Nadu, India.

---

## Abstract Overview

Dense memory overcommit in cloud infrastructure enables substantial server consolidation and operational cost reductions. However, when composite memory demands exceed physical capacity ($\Omega = \sum M_{\max}^{(i)} / M_{\text{DRAM}} > 1.0$), latency-critical microservices experience severe tail degradation. 

This repository provides the complete empirical telemetry harness, parametric statistical engine, Extreme Value Theory (EVT) modeling framework, and **PSI-Shed** controller daemon. Key findings and capabilities include:
* **The Tail Cliff:** Unconstrained Linux direct page reclamation (`shrink_node()`) inflates P99.9 memory allocation latency by **$1,975\times$** (from $24.5\ \mu\text{s}$ to $48,399.5\ \mu\text{s}$) while CPU utilization remains below $45\%$.
* **Sub-10 ms Kinematics:** Formulates discrete-time velocity $\mathbf{v}_{\text{PSI}}(t) = d(\text{PSI})/dt$ and acceleration $\mathbf{a}_{\text{PSI}}(t) = dv/dt$ from Linux Pressure Stall Information (PSI).
* **Extreme Value Theory Tail Modeling:** Parametric Generalized Pareto Distribution (GPD) modeling over the Peak-Over-Threshold asymptotic domain ($u \ge 35\ \mu\text{s}$), validating Fréchet-class heavy tails ($\hat{\xi} = 0.382$).
* **Closed-Form Capacity Frontier $\Omega^*(\alpha, L_{\text{SLA}}, \beta_{\text{burst}})$:** Analytically inverts tail quantile equations into a closed-form formula for the safe server overcommit boundary.
* **PSI-Shed 3-Phase Controller:** A user-space daemon multiplexing `epoll` triggers at $\Delta t = 10\text{ ms}$, delivering a **$410.2\times$ reduction** in P99.9 tail latency ($118.0\ \mu\text{s}$ vs. $48,399.5\ \mu\text{s}$) while retaining **$99.7\%$** of batch compute throughput ($4,159.2\text{ MB/s}$).

---

## System Architecture

```
+-----------------------------------------------------------------------------------------+
|                               HOST DRAM (192 GB Physical)                               |
+-----------------------------+-----------------------------+-----------------------------+
|    Tier 1: Latency-Critical |    Tier 2: Streaming Buffer |  Tier 3: Opportunistic Batch|
|    In-Memory KV-Store       |    Video Transcoding / RPC  |  Dense Matrix Churn / ML    |
|    SLA: T_alloc < 250 us    |    Soft-QoS Buffer Rings    |  Prefetch & Shuffle Caches  |
+-----------------------------+-----------------------------+-----------------------------+
               |                            |                             |
               +----------------------------+-----------------------------+
                                            |
                                            v
+-----------------------------------------------------------------------------------------+
|                     PSI-SHED CLOSED-LOOP CONTROLLER (User-Space)                        |
|                                                                                         |
|   1. Dual-Loop Telemetry: timerfd (10 ms) + /proc/pressure/memory epoll (< 120 us)      |
|   2. Discrete-Time Kinematics:  v(t) = d(PSI)/dt,  a(t) = dv/dt                         |
|   3. Non-Linear PD Error Law:   e(t) = kp * max(0, PSI - theta) + kd * max(0, a_PSI)   |
|   4. Anti-Chatter Dwell Timer:  T_dwell = 500 ms                                        |
+-----------------------------------------------------------------------------------------+
       | Phase 1: mem.high Throttling | Phase 2: Watermark Mod. | Phase 3: MADV_PAGEOUT
       v                              v                         v
+-----------------------------------------------------------------------------------------+
|                               LINUX KERNEL 6.8 & CGROUP V2                              |
|   - MGLRU Multi-Generational Page Table Scanner (/sys/kernel/mm/lru_gen/enabled = 0x0007)|
|   - Dynamic sysctl: vm.min_free_kbytes [64 MB -> 512 MB]                                |
|   - Zero Direct Reclamation: Proactive asynchronous kswapd scanning                     |
+-----------------------------------------------------------------------------------------+
```

---

## Repository Structure

```text
.
├── reproduce.py                # Master 1-command end-to-end scientific replication script
├── run_replication.sh          # Linux/macOS bash wrapper for reproduction pipeline
├── requirements.txt            # Pinned Python package dependencies
├── LICENSE                     # MIT Open Source License
├── README.md                   # Comprehensive repository documentation
├── .gitignore                  # Git ignore rules for Python, C, and LaTeX
│
├── src/                        # Core source code & analytical engines
│   ├── psi_shed_daemon.py      # Production user-space controller daemon (dry-run & live)
│   ├── memory_churn_harness.c  # Cycle-accurate multi-tenant memory allocation harness
│   ├── tail_latency_modeler.py # EVT Generalized Pareto Distribution & GLM frontier solver
│   ├── parametric_stats_engine.py # Two-way parametric ANOVA (F, p, eta_p^2) & Cohen's d
│   └── generate_all_figures.py # Generates all 10 publication figures (PDF & PNG)
│
├── data/                       # Empirical datasets and traces
│   ├── raw_telemetry/          # 1.68M allocation samples, benchmark sweeps, timeseries
│   │   ├── benchmark_sweeps.csv
│   │   ├── raw_alloc_samples.csv
│   │   └── timeseries_trace.csv
│   └── processed/              # Processed CSV summaries & capacity frontier curves
│       ├── controller_mitigation_summary.csv
│       ├── evt_gpd_summary.csv
│       └── omega_star_frontier.csv
│
├── figures/                    # Vector PDF and 300+ DPI PNG publication figures
│   ├── fig01.pdf ... fig10.pdf # All 10 publication-quality vector plots
│   └── png/                    # High-resolution raster previews
│
├── tables/                     # Formal LaTeX tables (booktabs + adjustbox)
│   ├── tab01_taxonomy.tex      # Systematic literature taxonomy (25 works, 7 dimensions)
│   ├── tab02_testbed.tex       # Multi-tenant testbed node hardware & workload profiles
│   ├── tab03_evt_params.tex    # EVT GPD threshold, shape (xi), scale (sigma), KS tests
│   ├── tab04_anova.tex         # Two-way parametric ANOVA on ln(T_alloc)
│   └── tab05_mitigation.tex    # Six-controller mitigation benchmark & Cliff's delta
│
├── literature/                 # Peer-reviewed references
│   └── peer_reviewed_papers.bib# Complete BibTeX bibliography (Springer Nature compatible)
│
└── paper/                      # Complete manuscript source
    ├── main.tex                # 35-page LaTeX manuscript
    ├── main.pdf                # Pre-compiled publication PDF (0 errors, 0 broken refs)
    └── sn-jnl.cls              # Springer Nature LaTeX template class
```

---

## Multi-Tenant Testbed Specifications

| Hardware Component | Configuration |
| :--- | :--- |
| **Server Node** | Dual-socket AMD EPYC 7763 (128 physical cores, 256 threads @ 2.45 GHz base / 3.50 GHz boost) |
| **Physical DRAM** | $192\text{ GB}$ DDR4-3200 ECC Registered RAM (8-channel NUMA) |
| **Swap Storage** | $1.92\text{ TB}$ PCIe 4.0 NVMe SSD (Samsung PM9A3, sustained $4,100\text{ MB/s}$ write) |
| **Operating System** | Ubuntu 22.04.4 LTS, Linux Kernel 6.8.0-generic, Cgroup v2 unified hierarchy |
| **Page Replacement** | Multi-Gen LRU (MGLRU) enabled (`/sys/kernel/mm/lru_gen/enabled = 0x0007`) |

### Multi-Tenant Workload Slices
1. **Tier 1 (Latency-Critical):** Multi-threaded in-memory Redis key-value store (48 GB footprint, P99.9 SLA $< 250\ \mu\text{s}$, Zipfian skew $\alpha = 0.99$).
2. **Tier 2 (Media Streaming):** FFmpeg H.264 transcoding worker (64 GB working set, cyclic buffer churn).
3. **Tier 3 (Opportunistic Batch):** Dense blocked matrix multiplication (64 GB base footprint, bursting to 140 GB via speculative shuffle caches).

---

## Quickstart & Replication Guide

### 1. Prerequisites
Install Python 3.10+ and required analytical libraries:
```bash
pip install -r requirements.txt
```

### 2. One-Command Master Replication
Run the master script to reproduce all mathematical models, ANOVA tables, and publication figures:
```bash
python reproduce.py
```
*(On Linux/macOS, you can alternatively execute `./run_replication.sh`)*

### 3. Running Individual Pipeline Steps

#### Step A: Fit EVT Tail Latency Models & Invert Capacity Frontier
```bash
python src/tail_latency_modeler.py
```
* Fits GPD parameters $(\hat{\xi}, \hat{\sigma})$ across 11 key operating regimes via Maximum Likelihood Estimation (MLE).
* Solves the GLM regression parameters $\boldsymbol{\beta}$ and $\boldsymbol{\beta}^{\text{PSI}}$.
* Exports `tables/tab03_evt_params.tex` and `data/processed/omega_star_frontier.csv`.

#### Step B: Execute Two-Way Parametric ANOVA & Effect Size Calculations
```bash
python src/parametric_stats_engine.py
```
* Computes two-way ANOVA on $N = 42,000$ log-transformed allocation latency samples $\ln(T_{\text{alloc}})$.
* Calculates partial eta-squared ($\eta_p^2$), Cohen's $d$, and non-parametric Tail Cliff's $\delta_{\text{tail}}$.
* Exports `tables/tab04_anova.tex` and `tables/tab05_mitigation.tex`.

#### Step C: Generate All 10 Publication Figures
```bash
python src/generate_all_figures.py
```
* Renders publication-ready vector PDFs and 300 DPI PNGs in `figures/` and `figures/png/`.

#### Step D: Run PSI-Shed Controller Daemon Simulation
```bash
python src/psi_shed_daemon.py --demo
```
* Simulates an acute memory surge and logs kinematic state transitions, proactive Tier 3 throttling, and watermark expansion.
* *(To run live on Linux with root privileges: `sudo python src/psi_shed_daemon.py --live`)*

---

## Primary Results & Performance Summary

| Mitigation Policy | P50 ($\mu\text{s}$) | P99 ($\mu\text{s}$) | P99.9 ($\mu\text{s}$) | PSI Some (%) | Scan Eff. $\mathcal{E}$ | T1 Goodput (kOPS) | T3 Batch (MB/s) | Tail Reduction | Tail Cliff's $\delta_{\text{tail}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unconstrained (Linux 6.8)** | 24.5 | 12,512.3 | 48,399.5 | 68.42% | 0.285 | 84.2 | 4,171.2 | Baseline | -- |
| **Unconstrained + Static `memory.min`** | 24.2 | 4,820.0 | 18,450.0 | 58.12% | 0.340 | 92.5 | 4,171.2 | $2.6\times$ | 0.642 (Large) |
| **Kubelet Static Eviction (85%)** | 23.9 | 421.2 | 3,819.9 | 24.20% | 0.480 | 108.5 | 2,918.4 | $12.7\times$ | 0.913 (Large) |
| **Meta `oomd` (PSI Threshold)** | 23.8 | 1,181.2 | 4,499.9 | 31.50% | 0.420 | 104.2 | 2,452.8 | $10.8\times$ | 0.857 (Large) |
| **Meta `Senpai` (Probing)** | 23.7 | 340.6 | 1,950.0 | 18.40% | 0.550 | 115.8 | 3,892.8 | $24.8\times$ | 0.946 (Large) |
| **Meta `Senpai` + `memory.min`** | 23.6 | 94.2 | 312.4 | 11.20% | 0.680 | 118.2 | 3,940.8 | $154.9\times$ | 0.982 (Large) |
| **PSI-Shed (Full Closed-Loop)** | **23.2** | **54.0** | **118.0** | **1.82%** | **0.840** | **119.8** | **4,159.2** | **$410.2\times$** | **0.987 (Large)** |

---

## Citation & BibTeX

If you find this work, telemetry traces, or controller implementation helpful in your research, please cite:

```bibtex
@article{patel2026psished,
  title={Characterizing Micro-Architectural Memory Pressure Stall Dynamics, Dynamic Cgroup V2 Overcommit, and Tail-Resilient Eviction Avoidance in Dense Cloud Multi-Tenancy},
  author={Patel, Devarsh and Singh, Adarsh and Umamaheshwari, M.},
  journal={Springer Nature},
  year={2026},
  note={Under Peer Review. Open-source replication package available at \url{https://github.com/adarshsingh/cgroup-psi-shed}}
}
```

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for complete details.
