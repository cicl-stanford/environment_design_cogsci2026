#!/usr/bin/env bash
#SBATCH --job-name=brms-fit
#SBATCH --output=/scratch/users/%u/environment_design/brms/logs/%x.%A_%a.out
#SBATCH --error=/scratch/users/%u/environment_design/brms/logs/%x.%A_%a.err
#SBATCH --partition=hns
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --array=1-10

# BRMS Model Fitting for Overcooked Design Analysis
#
# Array job that fits one of 10 BRMS models:
#   1-4:   base condition (full, oracle, inference_ablation, efficiency_ablation)
#   5-8:   communicative condition (full, oracle, inference_ablation, efficiency_ablation)
#   9:     baseline (uniform)
#   10:    H4 model (placement_id)
#
# Each job uses 64 cores: 16 chains x 4 threads per chain

set -euo pipefail

echo "========================================"
echo "Array Job: $SLURM_ARRAY_JOB_ID"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE"
echo "========================================"
date

# ----- Modules -----
ml R/4.4.2
ml gcc/14.2.0
export TBB_CXX_TYPE=gcc
export CC=gcc
export CXX=g++

# ----- Configuration -----
PROJECT_DIR="${PROJECT_DIR:-$HOME/src/environment_design}"
DATA_DIR="${DATA_DIR:-/scratch/users/$USER/environment_design/brms/data}"
OUTPUT_DIR="${OUTPUT_DIR:-/scratch/users/$USER/environment_design/brms/output}"
R_SCRIPT_DIR="$PROJECT_DIR/project_code/R/overcooked_design"

# MCMC settings (optimized for 64 cores)
N_CHAINS=16
N_ITER=4000
THREADS_PER_CHAIN=4

# Ensure directories exist
mkdir -p "$OUTPUT_DIR" "$DATA_DIR"
mkdir -p "/scratch/users/$USER/environment_design/brms/logs"

# ----- Map array index to model ID -----
declare -a MODEL_IDS=(
  "base_full"
  "base_oracle"
  "base_inference_ablation"
  "base_efficiency_ablation"
  "comm_full"
  "comm_oracle"
  "comm_inference_ablation"
  "comm_efficiency_ablation"
  "baseline"
  "h4"
)

# Array is 1-indexed
MODEL_ID="${MODEL_IDS[$((SLURM_ARRAY_TASK_ID - 1))]}"

echo ""
echo "Model ID: $MODEL_ID"
echo "Data dir: $DATA_DIR"
echo "Output dir: $OUTPUT_DIR"
echo ""

# ----- Check for preprocessed data -----
if [[ ! -f "$DATA_DIR/df.long.rds" ]]; then
  echo "ERROR: Preprocessed data not found at $DATA_DIR/df.long.rds"
  echo "Run preprocessing first: Rscript preprocess_for_brms.R"
  exit 1
fi

# ----- Run model fitting -----
echo "Starting model fitting..."
echo ""

Rscript "$R_SCRIPT_DIR/fit_brms_model.R" \
  --model-id "$MODEL_ID" \
  --data-dir "$DATA_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --chains "$N_CHAINS" \
  --iter "$N_ITER" \
  --threads-per-chain "$THREADS_PER_CHAIN"

echo ""
echo "========================================"
echo "Job complete"
date
echo "========================================"
