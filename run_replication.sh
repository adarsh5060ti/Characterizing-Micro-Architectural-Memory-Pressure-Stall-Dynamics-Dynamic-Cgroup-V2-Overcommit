#!/usr/bin/env bash
# run_replication.sh - Bash script to run full replication pipeline on Linux / Unix
set -e

echo "========================================================================"
echo " Starting PSI-Shed Replication Pipeline"
echo "========================================================================"

# Check Python dependencies
python3 -m pip install -q -r requirements.txt || true

# Run Master Replication Script
python3 reproduce.py

# Optional: compile C harness if gcc is installed
if command -v gcc &> /dev/null; then
    echo "Compiling memory_churn_harness.c with gcc -O3..."
    gcc -O3 -Wall -Wextra src/memory_churn_harness.c -o src/memory_churn_harness -lm -lpthread || true
fi

echo "========================================================================"
echo " Replication Complete! All figures, tables, and models generated."
echo "========================================================================"
