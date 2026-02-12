#!/usr/bin/env bash
#SBATCH --job-name=overcooked-arr
#SBATCH --output=/scratch/users/%u/environment_design/s1_design_inference/logs/%x.%A_%a.out
#SBATCH --error=/scratch/users/%u/environment_design/s1_design_inference/logs/%x.%A_%a.err
#SBATCH --partition=hns
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G

set -euo pipefail
echo "Array $SLURM_ARRAY_JOB_ID task $SLURM_ARRAY_TASK_ID on $SLURM_NODELIST"
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
TASKS_FILE="${TASKS_FILE:-$PROJECT_DIR/project_code/bash/s1_design_inference/tasks.txt}"
OUTDIR_DEFAULT="${OUTDIR:-/scratch/users/$USER/environment_design/s1_design_inference}"
OVERWRITE_RESULTS="${OVERWRITE_RESULTS:-0}"   # 1 = force rerun even if pickle exists

# ensure dirs
mkdir -p "$OUTDIR_DEFAULT" "$OUTDIR_DEFAULT/logs"
cd "$PROJECT_DIR"

# ----- Map array index → tasks.txt line via OFFSET -----
OFFSET="${OFFSET:-0}"
LINE_IDX=$(( SLURM_ARRAY_TASK_ID + OFFSET ))
CMD="$(sed -n "${LINE_IDX}p" "$TASKS_FILE" || true)"
if [[ -z "${CMD:-}" ]]; then
  echo "No command for line $LINE_IDX (OFFSET=$OFFSET, TASK_ID=$SLURM_ARRAY_TASK_ID)"
  exit 0
fi

# ----- Parse expected output pickle path from the command -----
# Assumes no spaces in values; true for our args.
read -r -a TOKS <<< "$CMD"
get_arg() {
  local key="$1"; local i
  for ((i=0;i<${#TOKS[@]};i++)); do
    if [[ "${TOKS[$i]}" == "$key" && $((i+1)) -lt ${#TOKS[@]} ]]; then
      printf '%s\n' "${TOKS[$((i+1))]}"
      return 0
    fi
  done
  return 1
}

OUTDIR_CMD="$(get_arg --output-dir || true)"
PREFIX="$(get_arg --output-prefix || true)"
SEED="$(get_arg --seed || true)"
OUTDIR_EFF="${OUTDIR_CMD:-$OUTDIR_DEFAULT}"
PICKLE="${OUTDIR_EFF}/pickles/${PREFIX}-seed=${SEED}.pkl"

# Skip if the expected pickle exists (unless OVERWRITE_RESULTS=1)
if [[ "${OVERWRITE_RESULTS}" != "1" ]] && [[ -n "${PREFIX:-}" && -n "${SEED:-}" && -f "$PICKLE" ]]; then
  echo "SKIP (already exists): $PICKLE"
  exit 0
fi

echo "Running (line $LINE_IDX): $CMD"
echo "Expected pickle: ${PICKLE}"
srun --export=ALL /bin/bash -c "source /share/software/user/open/lmod/lmod/init/bash && module load python/3.9.0 && export PYTHONPATH='${PROJECT_DIR}/gym-cooking:${PYTHONPATH}' && $CMD"

echo "Done"
date