#!/usr/bin/env bash
#SBATCH --job-name=overcooked-final
#SBATCH --output=/scratch/users/%u/environment_design/overcooked_design/final_outputs/logs/%x.%A_%a.out
#SBATCH --error=/scratch/users/%u/environment_design/overcooked_design/final_outputs/logs/%x.%A_%a.err
#SBATCH --partition=hns
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G

set -euo pipefail
echo "Array $SLURM_ARRAY_JOB_ID task $SLURM_ARRAY_TASK_ID on $SLURM_NODELIST"
date

# ----- Modules (robust) -----
source /share/software/user/open/lmod/lmod/init/bash
module --ignore_cache purge
module --ignore_cache load python/3.9.0

# ----- Python user-site visibility -----
export PATH="$HOME/.local/bin:$PATH"
PY_USER_SITE="$(python3 -m site --user-site)"
export PYTHONUSERBASE="$HOME/.local"
export PYTHONPATH="$PY_USER_SITE:${PYTHONPATH-}"
unset PYTHONNOUSERSITE

# ----- Headless + single-threaded -----
export SDL_VIDEODRIVER=dummy
export MPLBACKEND=Agg
export SDL_AUDIODRIVER=dummy
export AUDIODRIVER=dummy
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

PROJECT_DIR="${PROJECT_DIR:-$HOME/src/environment_design}"
TASKS_FILE="${TASKS_FILE:-$PROJECT_DIR/project_code/bash/overcooked_design/final_config_tasks.txt}"
OUTDIR_DEFAULT="${OUTDIR:-/scratch/users/$USER/environment_design/overcooked_design/final_outputs}"
OVERWRITE_RESULTS="${OVERWRITE_RESULTS:-0}"   # 1 = force rerun even if CSV exists
N_SEEDS="${N_SEEDS:-100}"                     # Expected number of seeds per CSV

# Ensure dirs
mkdir -p "$OUTDIR_DEFAULT" "$OUTDIR_DEFAULT/logs" "$OUTDIR_DEFAULT/csvs"
cd "$PROJECT_DIR"

# Add gym-cooking to PYTHONPATH
export PYTHONPATH="${PROJECT_DIR}/gym-cooking:${PYTHONPATH}"

# ----- Map array index → tasks.txt line via OFFSET -----
OFFSET="${OFFSET:-0}"
LINE_IDX=$(( SLURM_ARRAY_TASK_ID + OFFSET ))
CMD="$(sed -n "${LINE_IDX}p" "$TASKS_FILE" || true)"
if [[ -z "${CMD:-}" ]]; then
  echo "No command for line $LINE_IDX (OFFSET=$OFFSET, TASK_ID=$SLURM_ARRAY_TASK_ID)"
  exit 0
fi

# ----- Parse expected output CSV path from the command -----
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

CSV_FILE="$(get_arg --output-csv || true)"

# Skip if the expected CSV exists and is complete (unless OVERWRITE_RESULTS=1)
if [[ "${OVERWRITE_RESULTS}" != "1" ]] && [[ -n "${CSV_FILE:-}" && -f "$CSV_FILE" ]]; then
  # Check row count (should be N_SEEDS + 1 header)
  ROW_COUNT=$(wc -l < "$CSV_FILE")
  EXPECTED=$((N_SEEDS + 1))
  if (( ROW_COUNT == EXPECTED )); then
    echo "SKIP (complete with $N_SEEDS rows): $CSV_FILE"
    exit 0
  else
    echo "RERUN (incomplete: $ROW_COUNT rows, expected $EXPECTED): $CSV_FILE"
  fi
fi

echo "Running (line $LINE_IDX): $CMD"
echo "Expected CSV: ${CSV_FILE}"
$CMD

echo "Done"
date
