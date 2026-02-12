#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".project_root" ]]; then
  echo "ERROR: This script must be run from the project root directory." >&2
  exit 1
fi

# --- CONFIG ---
PROJECT_DIR="$(pwd)"
EXP="overcooked_design"
TASKS_FILE="${TASKS_FILE:-${PROJECT_DIR}/project_code/bash/${EXP}/final_config_tasks.txt}"
OUTDIR="${OUTDIR:-$SCRATCH/environment_design/${EXP}/final_outputs}"
N_SEEDS="${N_SEEDS:-100}"
SEED_START="${SEED_START:-42}"
TEST_MODE="${TEST_MODE:-0}"  # 1 = generate only 8 test tasks (2 configs, 2 placements, 2 dishes)

# Path to final configs
CONFIGS_DIR="${PROJECT_DIR}/stimuli/overcooked_design/final_configs"

mkdir -p "$(dirname "$TASKS_FILE")" "$OUTDIR" "$OUTDIR/csvs"

echo "[gen] Building task list for final configs → $TASKS_FILE"
echo "[gen] Configs directory: $CONFIGS_DIR"
echo "[gen] Seeds per task: $N_SEEDS"
echo "[gen] Seed start: $SEED_START"
echo "[gen] Test mode: $TEST_MODE (1 = only 8 test tasks)"

# Verify configs directory exists
if [[ ! -d "$CONFIGS_DIR" ]]; then
  echo "ERROR: Configs directory not found: $CONFIGS_DIR" >&2
  exit 1
fi

# Count config files
NUM_CONFIGS=$(ls -1 "$CONFIGS_DIR"/*.json 2>/dev/null | wc -l)
if (( NUM_CONFIGS == 0 )); then
  echo "ERROR: No JSON config files found in $CONFIGS_DIR" >&2
  exit 1
fi

echo "[gen] Found $NUM_CONFIGS config files"

# Clear existing file
> "$TASKS_FILE"

TASK_COUNT=0

# Determine which configs and placements to use
if (( TEST_MODE == 1 )); then
  # Test mode: only 2 configs (first 2 alphabetically)
  CONFIG_FILES=($(ls -1 "$CONFIGS_DIR"/*.json | head -2))
  PLACEMENT_IDS=(5 8)  # Only placements 5 and 8
  echo "[gen] TEST MODE: Using ${#CONFIG_FILES[@]} configs and ${#PLACEMENT_IDS[@]} placements"
else
  # Full mode: all configs, all placements
  CONFIG_FILES=("$CONFIGS_DIR"/*.json)
  PLACEMENT_IDS=($(seq 0 11))
fi

# Enumerate all config files
for config_file in "${CONFIG_FILES[@]}"; do
  config_id=$(basename "$config_file" .json)

  # For each placement and dish
  for placement_id in "${PLACEMENT_IDS[@]}"; do
    for dish in "TomatoSalad" "OnionSalad"; do
      # Output CSV for this specific combination
      OUTPUT_CSV="${OUTDIR}/csvs/${config_id}_p${placement_id}_${dish}.csv"

      # Build command
      CMD="python3 ${PROJECT_DIR}/project_code/python/overcooked_design/run_single_config_placement.py"
      CMD="$CMD --config-path $config_file"
      CMD="$CMD --placement-id $placement_id"
      CMD="$CMD --dish $dish"
      CMD="$CMD --n-seeds $N_SEEDS"
      CMD="$CMD --seed-start $SEED_START"
      CMD="$CMD --output-csv $OUTPUT_CSV"

      echo "$CMD" >> "$TASKS_FILE"
      TASK_COUNT=$((TASK_COUNT + 1))
    done
  done
done

if (( TEST_MODE == 1 )); then
  EXPECTED=8  # 2 configs × 2 placements × 2 dishes
  echo "[gen] Wrote $TASK_COUNT tasks to $TASKS_FILE"
  echo "[gen] Expected: 2 configs × 2 placements × 2 dishes = $EXPECTED tasks (TEST MODE)"
else
  EXPECTED=$((NUM_CONFIGS * 12 * 2))
  echo "[gen] Wrote $TASK_COUNT tasks to $TASKS_FILE"
  echo "[gen] Expected: $NUM_CONFIGS configs × 12 placements × 2 dishes = $EXPECTED tasks"
fi

if (( TASK_COUNT != EXPECTED )); then
  echo "WARNING: Task count mismatch (got $TASK_COUNT, expected $EXPECTED)" >&2
fi

echo "[gen] Sample tasks (first 3):"
head -3 "$TASKS_FILE" 2>/dev/null || true
