#!/usr/bin/env bash
# Runs the whole preprocessing, including the recorded manual cuts.
# Run from the repository root: bash code/preprocessing/run_all.sh

set -euo pipefail

PYTHON="${PYTHON:-python3}"
PREPROCESSING_DIR="code/preprocessing"

"$PYTHON" "$PREPROCESSING_DIR/main.py" data/raw data/work data/clean \
    --manual-cuts "$PREPROCESSING_DIR/resources/08_manual_cuts.json" \
    --final-dir data/final
