#!/usr/bin/env bash
set -u

OUT_DIR="out"
mkdir -p "$OUT_DIR"

TMP="$(mktemp -d)"
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT

# 1×1 opaque black GIF (hex) -> we resize it to canvas
GIF_HEX='47494638396101000100f00000ffffff00000021f90400000000002c00000000010001000002024401003b'

# create tiny black GIF using xxd or perl
if command -v xxd >/dev/null 2>&1; then
  printf '%s' "$GIF_HEX" | xxd -r -p > "$TMP/black1x1.gif"
elif command -v perl >/dev/null 2>&1; then
  GIF_HEX="$GIF_HEX" perl -we 'print pack "H*", $ENV{GIF_HEX}' > "$TMP/black1x1.gif"
else
  echo "Need either xxd or perl to create the black frame." >&2
  exit 1
fi

shopt -s nullglob
any=0
for f in *.gif; do
  any=1
  echo "Processing: $f"

  # logical screen size (e.g., 560x560)
  CANVAS="$(gifsicle --info "$f" 2>/dev/null | awk '/logical screen/ {print $3; exit}')"
  if [[ -z "${CANVAS:-}" ]]; then
    echo "  ! Could not determine canvas size. Skipping." >&2
    continue
  fi

  # make a black frame at the canvas size
  if ! gifsicle --resize "$CANVAS" "$TMP/black1x1.gif" > "$TMP/black_canvas.gif" 2>/dev/null; then
    echo "  ! Failed to create black canvas. Skipping." >&2
    continue
  fi

  # count frames
  NFRAMES="$(gifsicle --info "$f" 2>/dev/null | awk '/image #[0-9]+/ {n++} END{print n+0}')"
  if [[ "${NFRAMES:-0}" -lt 1 ]]; then
    echo "  ! No frames detected. Skipping." >&2
    continue
  fi

  out="$OUT_DIR/${f##*/}"

  if [[ "$NFRAMES" -ge 2 ]]; then
    last=$((NFRAMES-1))
    penult=$((NFRAMES-2))
    # keep 0..last-1 unchanged; set last to 2.00s; append black 1.00s
    if gifsicle \
         "$f" "#0-${penult}" \
         --delay=100 "$f" "#${last}" \
         --delay=50 "$TMP/black_canvas.gif" \
         > "$out" 2>/dev/null; then
      echo "  → Wrote: $out"
    else
      echo "  ! gifsicle failed on $f. Skipping." >&2
      rm -f "$out"
    fi
  else
    # single-frame: set it to 2s, then append black 1s
    if gifsicle \
         --delay=200 "$f" "#0" \
         --delay=100 "$TMP/black_canvas.gif" \
         > "$out" 2>/dev/null; then
      echo "  → Wrote: $out"
    else
      echo "  ! gifsicle failed on $f. Skipping." >&2
      rm -f "$out"
    fi
  fi
done

if [[ "$any" -eq 0 ]]; then
  echo "No *.gif files found in this directory."
fi
