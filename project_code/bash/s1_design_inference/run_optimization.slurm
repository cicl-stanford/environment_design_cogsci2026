#!/bin/bash
#SBATCH --job-name=overcooked-select-start-locations
#SBATCH --output=/scratch/users/%u/environment_design/s1_design_inference/logs/starts/%x.%A_%a.out
#SBATCH --error=/scratch/users/%u/environment_design/s1_design_inference/logs/starts/%x.%A_%a.err
#SBATCH --partition=hns
#SBATCH --time=2:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G

set -euo pipefail
echo "Computing start locations for job $SLURM_JOB_ID on $SLURM_NODELIST"
date

# ----- Modules (robust) -----
source /share/software/user/open/lmod/lmod/init/bash
module --ignore_cache purge
module --ignore_cache load python/3.9.0 || module --ignore_cache load python/3.12.1

# ----- Python user-site visibility -----
export PATH="$HOME/.local/bin:$PATH"
PY_USER_SITE="$(python3 -m site --user-site)"
export PYTHONUSERBASE="$HOME/.local"
export PYTHONPATH="$PY_USER_SITE:${PYTHONPATH-}"
unset PYTHONNOUSERSITE

# ----- Headless + 1-threaded BLAS -----
export SDL_VIDEODRIVER=dummy
export MPLBACKEND=Agg
export SDL_AUDIODRIVER=dummy
export AUDIODRIVER=dummy
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

PROJECT_DIR="${PROJECT_DIR:-$HOME/src/environment_design}"
LOG_DIR="${OUTDIR:-/scratch/users/$USER/environment_design/s1_design_inference/logs/starts}"

# ensure dirs
mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

# Run the comprehensive start location finder
python3 project_code/python/s1_design_inference/find_start_locations.py \
  --output "project_code/bash/s1_design_inference/start_locations.json" \
  --seeds 3

echo "Start location optimization completed successfully"

