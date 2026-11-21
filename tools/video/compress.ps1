# Windows version of compress.sh. Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File tools\video\compress.ps1
param([string]$In = "assets/spacesoft-showcase.mp4")
$ErrorActionPreference = "Stop"

function Encode([int]$MaxWidth, [int]$Crf, [string]$Out) {
  ffmpeg -y -hide_banner -loglevel warning -i $In -an `
    -vf "scale='min($MaxWidth,iw)':-2:flags=lanczos,fps=30" `
    -c:v libx264 -preset veryfast -crf $Crf -profile:v high -pix_fmt yuv420p `
    -movflags +faststart $Out
  "{0,-40} {1,6} KB" -f $Out, [math]::Round((Get-Item $Out).Length / 1KB)
}

Encode 1280 28 "assets/spacesoft-showcase-1280.mp4"
Encode 720  30 "assets/spacesoft-showcase-720.mp4"
"Then run: python tools/build.py"
