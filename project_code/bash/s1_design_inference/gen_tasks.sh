#!/usr/bin/env bash
set -euo pipefail

#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".project_root" ]]; then
  echo "ERROR: This script must be run from the project root directory." >&2
  exit 1
fi

# --- CONFIG ---
PROJECT_DIR="$(pwd)"
EXP="${EXP:-s1_design_inference}"
TASKS_FILE="${TASKS_FILE:-${PROJECT_DIR}/project_code/bash/${EXP}/tasks.txt}"
SEEDS="${SEEDS:-20}"   # override via: SEEDS=50 ./gen_tasks.sh
OUTDIR="${OUTDIR:-$SCRATCH/environment_design/${EXP}}"   # <- write results to SCRATCH
START_LOCATIONS_FILE="${PROJECT_DIR}/project_code/bash/${EXP}/start_locations.json"

# --- Lmod / Python module (robust) ---
source /share/software/user/open/lmod/lmod/init/bash
module --ignore_cache purge
module --ignore_cache load python/3.9.0 || module --ignore_cache load python/3.12.1

# User-site visibility
export PATH="$HOME/.local/bin:$PATH"
PY_USER_SITE="$(python3 -c 'import site; print(site.getusersitepackages())')"
export PYTHONPATH="${PY_USER_SITE}:${PYTHONPATH-}"

# Headless graphics
export SDL_VIDEODRIVER=dummy
export MPLBACKEND=Agg

cd "$PROJECT_DIR"

ORCH="project_code/python/${EXP}/model_runs.py"
if [[ ! -f "$ORCH" ]]; then
  echo "ERROR: Orchestrator not found: $ORCH" >&2
  exit 1
fi

mkdir -p "$(dirname "$TASKS_FILE")" "$OUTDIR"

# Check if start locations exist
if [[ ! -f "$START_LOCATIONS_FILE" ]]; then
  echo "ERROR: Start locations file not found: $START_LOCATIONS_FILE" >&2
  echo "Please run find_start_locations.py first to generate start locations." >&2
  exit 1
fi

echo "[gen] building task list → $TASKS_FILE"

# First, generate the base task list
python3 "$ORCH" --seeds "$SEEDS" --jobs 1 --dry-run 2>/dev/null \
| awk '/^DRY-RUN:/{sub(/^DRY-RUN:[ ]*/,""); print}' \
| sed 's/^python[[:space:]]/python3 /' \
| awk -v outdir="$OUTDIR" '
  # replace the value that follows --output-dir with our SCRATCH path
  {
    for (i=1; i<=NF; i++) {
      if ($i=="--output-dir" && (i+1)<=NF) { $(i+1)=outdir }
    }
    print
  }
' > "${TASKS_FILE}.txt"

# Now modify the task list to include start locations
echo "[gen] adding start locations for model tasks..."

python3 -c "
import json
import sys
import re

# Load start locations data
try:
    with open('$START_LOCATIONS_FILE', 'r') as f:
        start_locations_data = json.load(f)
except:
    print('Error: Could not load start locations file: $START_LOCATIONS_FILE', file=sys.stderr)
    sys.exit(1)

# Create lookup dictionary keyed by trial_id
location_cache = {}
for item in start_locations_data:
    location_cache[item['trial_id']] = item

# Process each line in the task file
with open('${TASKS_FILE}.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Extract level file to determine trial_id
        parts = line.split()
        level_file = None
        for i, part in enumerate(parts):
            if part == '--level' and i + 1 < len(parts):
                level_file = parts[i + 1]
                break

        if level_file:
            # Extract trial_id from level file path
            level_name = level_file.split('/')[-1]  # Get filename
            trial_match = re.match(r'(trial_\d+)\.txt$', level_name)
            if trial_match:
                trial_id = trial_match.group(1)

                # Look up start locations for this trial
                if trial_id in location_cache:
                    trial_data = location_cache[trial_id]

                    # Add start location arguments based on number of agents
                    if '--num-agents 1' in line or '--num-start-locations 1' in line:
                        # Single agent - use agent1_location
                        if trial_data.get('agent1_location'):
                            line += f' --start-location-model1 \"{trial_data[\"agent1_location\"]}\"'
                    elif '--num-agents 2' in line or '--num-start-locations 2' in line:
                        # Two agents - use both locations if available
                        if trial_data.get('agent1_location'):
                            line += f' --start-location-model1 \"{trial_data[\"agent1_location\"]}\"'
                        if trial_data.get('agent2_location'):
                            line += f' --start-location-model2 \"{trial_data[\"agent2_location\"]}\"'
                else:
                    print(f'Warning: Start locations not found for {trial_id}, using auto-placement.', file=sys.stderr)

        print(line)
" > "$TASKS_FILE"

# Clean up temporary file
rm -f "${TASKS_FILE}.txt"

NLINES=$(wc -l < "$TASKS_FILE" || echo 0)
echo "[gen] wrote $NLINES tasks to $TASKS_FILE"
head -3 "$TASKS_FILE" 2>/dev/null || true