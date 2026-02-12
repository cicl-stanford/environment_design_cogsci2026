#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".project_root" ]]; then
  echo "ERROR: This script must be run from the project root directory." >&2
  exit 1
fi

PROJECT_DIR="$(pwd)"
GEN="${GEN:-${PROJECT_DIR}/project_code/bash/overcooked_design/gen_tasks.sh}"
TASKS_FILE="${TASKS_FILE:-${PROJECT_DIR}/project_code/bash/overcooked_design/final_config_tasks.txt}"
SLURM_FILE="${SLURM_FILE:-${PROJECT_DIR}/project_code/bash/overcooked_design/run_array.slurm}"
LOGROOT="${LOGROOT:-/scratch/users/$USER/environment_design/overcooked_design/final_outputs}"

# Tuneables
CHUNK="${CHUNK:-288}"              # Max task IDs per submission
CONCURRENCY="${CONCURRENCY:-300}"  # %X throttle for each array
N_SEEDS="${N_SEEDS:-100}"          # Seeds per task
SEED_START="${SEED_START:-42}"     # Starting seed
TEST_MODE="${TEST_MODE:-0}"        # 1 = test mode (8 tasks, 3 seeds)
OVERWRITE="${OVERWRITE:-0}"        # 1 = submit all (ignore existing CSVs)
REGEN="${REGEN:-0}"                # 1 = rebuild tasks.txt first

# Optional positionals
case "${1-}" in overwrite) OVERWRITE=1 ;; esac
case "${2-}" in regen)     REGEN=1     ;; esac

# 1) (re)generate tasks.txt if asked/missing
if [[ ! -f "$TASKS_FILE" || "$REGEN" == "1" ]]; then
  echo "[gen] Building task list → $TASKS_FILE"
  N_SEEDS="$N_SEEDS" SEED_START="$SEED_START" TEST_MODE="$TEST_MODE" "$GEN"
else
  echo "[gen] Using existing $TASKS_FILE (REGEN=0)"
fi

NLINES=$(wc -l < "$TASKS_FILE" || echo 0)
(( NLINES > 0 )) || { echo "No tasks in $TASKS_FILE"; exit 2; }

# Helper to compress integer list to SLURM ranges (e.g., 5-9,12,20-22)
compress_ranges() {
  awk '
    NR==1 {s=$1; p=$1; next}
    {
      if ($1==p+1) { p=$1; next }
      printf (s==p ? "%s," : "%s-%s,", s, p);
      s=$1; p=$1
    }
    END { if (NR) printf (s==p ? "%s" : "%s-%s", s, p) }
  '
}

# 2) Build list of missing lines (those whose CSV does NOT exist or is incomplete)
MISSING_IDX_FILE="$(mktemp)"
trap 'rm -f "$MISSING_IDX_FILE"' EXIT

awk -v dflt="$LOGROOT" -v out="$MISSING_IDX_FILE" -v n_seeds="$N_SEEDS" '
{
  csv_file="";
  for(i=1;i<=NF;i++){
    if($i=="--output-csv") csv_file=$(i+1);
  }
  if (csv_file != "") {
    # Check existence AND row count
    cmd1 = "test -f \047" csv_file "\047";
    status1 = system(cmd1);
    if (status1 == 0) {
      # File exists, check row count (excluding header: should be n_seeds)
      cmd2 = "wc -l < \047" csv_file "\047 | awk \047{print $1-1}\047";
      cmd2 | getline row_count;
      close(cmd2);
      if (row_count != n_seeds) {
        print NR >> out;  # Incomplete
      }
    } else {
      print NR >> out;  # Missing
    }
  } else {
    print NR >> out;
  }
}' "$TASKS_FILE"

# Count
MISSING=$(wc -l < "$MISSING_IDX_FILE" || echo 0)
EXISTING=$(( NLINES - MISSING ))

echo "Total tasks:    $NLINES"
echo "Already done:   $EXISTING"
if [[ "$OVERWRITE" == "1" ]]; then
  echo "Will be run:    $NLINES (OVERWRITE=1)"
else
  echo "Will be run:    $MISSING"
fi
echo "OVERWRITE=$OVERWRITE (1 = re-run even if CSV exists)"

# 3) Submit
if [[ "$OVERWRITE" == "1" ]]; then
  # Submit full coverage in CHUNK-sized spans
  CHUNKS=$(( (NLINES + CHUNK - 1) / CHUNK ))
  echo "Submitting ALL $NLINES tasks in $CHUNKS chunk(s) of up to $CHUNK (%$CONCURRENCY)"
  for ((i=0; i<CHUNKS; i++)); do
    OFFSET=$(( i * CHUNK ))
    SPAN=$(( NLINES - OFFSET ))
    (( SPAN > CHUNK )) && SPAN=$CHUNK
    ARR_SPEC="1-${SPAN}%${CONCURRENCY}"
    echo "Chunk $((i+1))/$CHUNKS: lines $((OFFSET+1))..$((OFFSET+SPAN)), OFFSET=$OFFSET, ARRAY=$ARR_SPEC"
    sbatch --export=OFFSET="$OFFSET",OVERWRITE_RESULTS="1",N_SEEDS="$N_SEEDS" --array="$ARR_SPEC" "$SLURM_FILE"
  done
else
  # Submit only missing indices in groups of size CHUNK
  if (( MISSING == 0 )); then
    echo "Nothing to run. Exiting."
    exit 0
  fi
  echo "Submitting only missing $MISSING task(s) with concurrency %$CONCURRENCY"
  mapfile -t IDX < <(sort -n "$MISSING_IDX_FILE")
  BATCHES=$(( (MISSING + CHUNK - 1) / CHUNK ))
  for ((b=0; b<BATCHES; b++)); do
    s=$(( b * CHUNK ))
    e=$(( s + CHUNK ))
    (( e > MISSING )) && e=$MISSING
    printf "%s\n" "${IDX[@]:s:e-s}" | compress_ranges > /tmp/ranges.$$
    RANGES=$(cat /tmp/ranges.$$); rm -f /tmp/ranges.$$
    echo "Batch $((b+1))/$BATCHES: indices $((s+1))..$e of $MISSING → ${RANGES}"
    sbatch --export=OFFSET="0",OVERWRITE_RESULTS="0",N_SEEDS="$N_SEEDS" --array="${RANGES}%${CONCURRENCY}" "$SLURM_FILE"
  done
fi

echo "All submissions done."
echo ""
echo "Monitor progress with:"
echo "  squeue -u \$USER"
echo "  tail -f $LOGROOT/logs/overcooked-final.*.out"
echo ""
echo "After completion, aggregate CSVs:"
echo "  bash project_code/bash/overcooked_design/aggregate_csvs.sh"
echo ""
echo "Transfer to local:"
echo "  rsync -avP sherlock:$LOGROOT/final_model_outputs.csv ./"
