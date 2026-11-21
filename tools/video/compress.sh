#!/usr/bin/env bash
# Compress the showcase video into a desktop and a mobile variant.
# Requires ffmpeg (https://ffmpeg.org). Run from the repo root:
#   bash tools/video/compress.sh
# Output (used automatically after: python tools/build.py):
#   assets/spacesoft-showcase-1280.mp4   desktop, max 1280 px wide (target < 800 KB)
#   assets/spacesoft-showcase-720.mp4    mobile,  max 720 px wide  (target < 400 KB)
set -euo pipefail
IN="${1:-assets/spacesoft-showcase.mp4}"

encode () { # <max-width> <crf> <out>
  ffmpeg -y -hide_banner -loglevel warning -i "$IN" \
    -an \
    -vf "scale='min($1,iw)':-2:flags=lanczos,fps=30" \
    -c:v libx264 -preset veryfast -crf "$2" -profile:v high -pix_fmt yuv420p \
    -movflags +faststart \
    "$3"
  printf '%-40s %6d KB\n' "$3" $(( $(wc -c < "$3") / 1024 ))
}

encode 1280 28 assets/spacesoft-showcase-1280.mp4
encode 720  30 assets/spacesoft-showcase-720.mp4

echo "If the 1280 file is still above 800 KB, raise the CRF (29-31) or use '-preset slow',"
echo "which compresses better at the same quality. Then run: python tools/build.py"
