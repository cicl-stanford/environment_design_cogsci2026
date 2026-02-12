#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".project_root" ]]; then
  echo "ERROR: This script must be run from the project root directory." >&2
  exit 1
fi

# --- CONFIG ---
PROJECT_DIR="$(pwd)"
EXP="overcooked_design"
OUTDIR="${OUTDIR:-$SCRATCH/environment_design/${EXP}/final_outputs}"
OUTPUT_FILE="${OUTPUT_FILE:-${OUTDIR}/planning_model_outputs.csv}"

# Check if csvs directory exists
if [[ ! -d "${OUTDIR}/csvs" ]]; then
  echo "ERROR: CSVs directory not found: ${OUTDIR}/csvs" >&2
  exit 1
fi

# Count CSV files
NUM_CSVS=$(ls -1 "${OUTDIR}/csvs"/*.csv 2>/dev/null | wc -l)
if (( NUM_CSVS == 0 )); then
  echo "ERROR: No CSV files found in ${OUTDIR}/csvs" >&2
  exit 1
fi

echo "[aggregate] Found ${NUM_CSVS} CSV files in ${OUTDIR}/csvs"
echo "[aggregate] Aggregating to ${OUTPUT_FILE}"

# Extract header from first CSV file
first_csv=("${OUTDIR}/csvs"/*.csv)
head -1 "${first_csv[0]}" > "${OUTPUT_FILE}"

# Append all data rows (skip headers)
tail -n +2 -q "${OUTDIR}/csvs"/*.csv >> "${OUTPUT_FILE}"

# Verify output
TOTAL_LINES=$(wc -l < "${OUTPUT_FILE}")
EXPECTED_LINES=$(( NUM_CSVS * 100 + 1 ))  # 100 seeds per CSV + 1 header

echo "[aggregate] Output file: ${OUTPUT_FILE}"
echo "[aggregate] Total lines: ${TOTAL_LINES}"
echo "[aggregate] Expected: ${EXPECTED_LINES} (1 header + ${NUM_CSVS} CSVs × 100 seeds)"

if (( TOTAL_LINES == EXPECTED_LINES )); then
  echo "[aggregate] ✓ Row count matches expected value"
else
  echo "[aggregate] WARNING: Row count mismatch!" >&2
  echo "[aggregate]   Got: ${TOTAL_LINES}, Expected: ${EXPECTED_LINES}" >&2
fi

# Show file size
FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo "[aggregate] File size: ${FILE_SIZE}"

# Show sample rows
echo "[aggregate] Sample rows (first 3 data rows):"
head -4 "${OUTPUT_FILE}" | tail -3
