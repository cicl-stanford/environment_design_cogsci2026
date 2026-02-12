#!/usr/bin/env bash
# submit_brms.sh
#
# Submission helper for BRMS model fitting on Sherlock.
# Runs preprocessing, then submits array job for all 11 models.
#
# Usage:
#   bash submit_brms.sh [--skip-preprocess]

set -euo pipefail

# ----- Configuration -----
PROJECT_DIR="${PROJECT_DIR:-$HOME/src/environment_design}"
SCRATCH_DIR="/scratch/users/$USER/environment_design/brms"
DATA_DIR="$SCRATCH_DIR/data"
OUTPUT_DIR="$SCRATCH_DIR/output"
BEHAVIORAL_DATA_DIR="$PROJECT_DIR/data/overcooked_design"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLURM_SCRIPT="$SCRIPT_DIR/run_brms.slurm"
R_SCRIPT_DIR="$PROJECT_DIR/project_code/R/overcooked_design"

# Parse arguments
SKIP_PREPROCESS=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-preprocess)
      SKIP_PREPROCESS=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: bash submit_brms.sh [--skip-preprocess]"
      exit 1
      ;;
  esac
done

echo "========================================"
echo "BRMS Model Fitting Submission"
echo "========================================"
echo ""
echo "Project dir: $PROJECT_DIR"
echo "Scratch dir: $SCRATCH_DIR"
echo "Data dir: $DATA_DIR"
echo "Output dir: $OUTPUT_DIR"
echo ""

# ----- Create directories -----
mkdir -p "$DATA_DIR" "$OUTPUT_DIR" "$SCRATCH_DIR/logs"

# ----- Load R module -----
source /share/software/user/open/lmod/lmod/init/bash
module --ignore_cache purge
module --ignore_cache load R/4.2.0

# ----- Run preprocessing -----
if [[ $SKIP_PREPROCESS -eq 0 ]]; then
  echo "========================================"
  echo "Step 1: Preprocessing data"
  echo "========================================"
  echo ""

  # Check that behavioral data exists
  if [[ ! -f "$BEHAVIORAL_DATA_DIR/behavioral_results/design_data.csv" ]]; then
    echo "ERROR: Behavioral data not found at:"
    echo "  $BEHAVIORAL_DATA_DIR/behavioral_results/design_data.csv"
    echo ""
    echo "Make sure data is synced to Sherlock first."
    exit 1
  fi

  ml R/4.4.2
  
  Rscript "$R_SCRIPT_DIR/preprocess_for_brms.R" \
    --data-dir "$BEHAVIORAL_DATA_DIR" \
    --output-dir "$DATA_DIR"

  echo ""
  echo "Preprocessing complete."
  echo ""
else
  echo "Skipping preprocessing (--skip-preprocess flag set)"
  echo ""

  # Verify preprocessed data exists
  if [[ ! -f "$DATA_DIR/df.long.rds" ]]; then
    echo "ERROR: Preprocessed data not found at $DATA_DIR/df.long.rds"
    echo "Run without --skip-preprocess to generate it."
    exit 1
  fi
fi

# ----- Submit array job -----
echo "========================================"
echo "Step 2: Submitting SLURM array job"
echo "========================================"
echo ""
echo "Models to fit (10 total):"
echo "  1-4:   base condition (full, oracle, inference_ablation, efficiency_ablation)"
echo "  5-8:   communicative condition (full, oracle, inference_ablation, efficiency_ablation)"
echo "  9:     baseline (uniform)"
echo "  10:    H4 model (placement_id)"
echo ""
echo "Resources per job:"
echo "  CPUs: 64 (16 chains x 4 threads)"
echo "  Memory: 64GB"
echo "  Time: 8 hours"
echo ""

# Export paths for SLURM script
export PROJECT_DIR DATA_DIR OUTPUT_DIR

# Submit the job
JOB_ID=$(sbatch --parsable "$SLURM_SCRIPT")

echo "Submitted array job: $JOB_ID"
echo ""

# ----- Print monitoring commands -----
echo "========================================"
echo "Monitoring Commands"
echo "========================================"
echo ""
echo "Check job status:"
echo "  squeue -u \$USER"
echo ""
echo "Check specific job:"
echo "  squeue -j $JOB_ID"
echo ""
echo "View logs:"
echo "  ls $SCRATCH_DIR/logs/"
echo "  tail -f $SCRATCH_DIR/logs/brms-fit.${JOB_ID}_*.out"
echo ""
echo "Cancel all jobs:"
echo "  scancel $JOB_ID"
echo ""

# ----- Print rsync commands -----
echo "========================================"
echo "After Jobs Complete"
echo "========================================"
echo ""
echo "Check output files:"
echo "  ls -la $OUTPUT_DIR/"
echo ""
echo "Expected outputs:"
echo "  - brms_fit_{cond}_{model}.rds (8 files)"
echo "  - brms_fit_baseline.rds (1 file)"
echo "  - brms_fit_h4.rds (1 file)"
echo "  - loo_{cond}_{model}.rds (8 files)"
echo "  - loo_baseline.rds (1 file)"
echo ""
echo "Rsync results to local machine:"
echo "  rsync -avP sherlock:$OUTPUT_DIR/*.rds /path/to/local/model_cache/"
echo ""
echo "========================================"
