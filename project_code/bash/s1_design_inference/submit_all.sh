#!/usr/bin/env bash
set -euo pipefail

#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".project_root" ]]; then
  echo "ERROR: This script must be run from the project root directory." >&2
  exit 1
fi

PROJECT_DIR="$(pwd)"
GEN="${GEN:-${PROJECT_DIR}/project_code/bash/s1_design_inference/gen_tasks.sh}"
TASKS_FILE="${TASKS_FILE:-${PROJECT_DIR}/project_code/bash/s1_design_inference/tasks.txt}"
SLURM_FILE="${SLURM_FILE:-${PROJECT_DIR}/project_code/bash/s1_design_inference/run_overcooked_array.slurm}"
LOGROOT="${LOGROOT:-/scratch/users/$USER/environment_design/s1_design_inference}"

# tuneables
CHUNK="${CHUNK:-900}"             # max task IDs per submission
CONCURRENCY="${CONCURRENCY:-300}" # %X throttle for each array
SEEDS="${SEEDS:-20}"              # passed to generator
OVERWRITE="${OVERWRITE:-0}"       # 1 = submit all (ignore existing pickles)
REGEN="${REGEN:-0}"               # 1 = rebuild tasks.txt first

# Optional positionals
case "${1-}" in overwrite) OVERWRITE=1 ;; esac
case "${2-}" in regen)     REGEN=1     ;; esac

# 1) Ensure start locations are computed before running model jobs
START_LOCATIONS_FILE="${PROJECT_DIR}/project_code/bash/s1_design_inference/start_locations.json"
if [[ ! -f "$START_LOCATIONS_FILE" || "$REGEN" == "1" ]]; then
  echo "[start] computing optimal start locations for all trials..."
  START_LOCATIONS_SLURM="${PROJECT_DIR}/project_code/bash/s1_design_inference/run_optimization.slurm"
  sbatch "$START_LOCATIONS_SLURM"
  echo "[start] start location job submitted. Please wait for completion before running main jobs."
  exit 0
fi

# 2) (re)generate tasks.txt if asked/missing
if [[ ! -f "$TASKS_FILE" || "$REGEN" == "1" ]]; then
  echo "[gen] building task list → $TASKS_FILE"
  SEEDS="$SEEDS" "$GEN"
else
  echo "[gen] using existing $TASKS_FILE (REGEN=0)"
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

# 2) Build list of missing lines (those whose pickle does NOT exist)
#    Do this entirely in awk + test to avoid subshell/set -e pitfalls.
MISSING_IDX_FILE="$(mktemp)"
trap 'rm -f "$MISSING_IDX_FILE"' EXIT

awk -v dflt="$LOGROOT" -v out="$MISSING_IDX_FILE" '
{
  odir=""; pref=""; seed="";
  for(i=1;i<=NF;i++){
    if($i=="--output-dir")    odir=$(i+1);
    if($i=="--output-prefix") pref=$(i+1);
    if($i=="--seed")          seed=$(i+1);
  }
  if(odir=="") odir=dflt;
  pick=odir "/pickles/" pref "-seed=" seed ".pkl";
  # Use system() to test existence; status 0 = exists
  cmd = "test -f \047" pick "\047";
  status = system(cmd);
  if (status != 0) {
    print NR >> out;
  }
}
END { }' "$TASKS_FILE"

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
echo "OVERWRITE=$OVERWRITE (1 = re-run even if pickle exists)"

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
    sbatch --export=OFFSET="$OFFSET",OVERWRITE_RESULTS="1" --array="$ARR_SPEC" "$SLURM_FILE"
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
    echo "Batch $((b+1))/$BATCHES: indices $((s+1))..$e of $MISSING → ${RANGES/%/,} (trimmed)"
    sbatch --export=OFFSET="0",OVERWRITE_RESULTS="0" --array="${RANGES}%${CONCURRENCY}" "$SLURM_FILE"
  done
fi

echo "All submissions done."