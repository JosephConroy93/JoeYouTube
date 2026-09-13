#!/usr/bin/env bash
# grab-frames.sh — pull N still frames from a YouTube video without downloading the whole file.
#
# usage: grab-frames.sh <url> <out-dir> <label> [timestamps]
#   timestamps: comma list of MM:SS (or SS), or "auto:N" (default auto:5) to spread N
#               timestamps evenly between 8% and 92% of the duration.
# output: <out-dir>/<label>-NN-<mmss>.png  (one per timestamp), plus a line per frame on stdout:
#         FRAME <path> <timestamp>
# Every download uses --download-sections (a ~4 s window) — never the full video.
set -euo pipefail
# YouTube bot-gates anonymous yt-dlp on some networks; set YTDLP_EXTRA="--cookies-from-browser edge" (or firefox/chrome) to pass browser cookies.
extra=${YTDLP_EXTRA:-}
url="$1"; out="$2"; label="$3"; ts="${4:-auto:5}"
mkdir -p "$out"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch" 2>/dev/null || true' EXIT

dur="$(yt-dlp $extra --print duration --no-warnings "$url" | head -1)"
if ! [[ "$dur" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then echo "ERROR: could not read duration ($dur)" >&2; exit 1; fi
dur="${dur%.*}"

to_sec() { local t="$1"; if [[ "$t" == *:* ]]; then IFS=: read -r m s <<<"$t"; echo $((10#$m*60+10#$s)); else echo "$t"; fi; }
fmt()    { printf '%02d%02d' $(( $1/60 )) $(( $1%60 )); }

secs=()
if [[ "$ts" == auto:* ]]; then
  n="${ts#auto:}"; lo=$(( dur*8/100 )); hi=$(( dur*92/100 ))
  for ((i=0;i<n;i++)); do secs+=( $(( lo + (hi-lo)*i/(n-1>0?n-1:1) )) ); done
else
  IFS=, read -ra parts <<<"$ts"; for p in "${parts[@]}"; do secs+=( "$(to_sec "$p")" ); done
fi

i=0
for s in "${secs[@]}"; do
  i=$((i+1)); e=$((s+4))
  clip="$scratch/$i.mp4"
  yt-dlp $extra -f "best[height<=720]" --download-sections "*${s}-${e}" --force-keyframes-at-cuts \
         -o "$clip" "$url" --no-warnings --quiet || { echo "WARN: download failed at ${s}s" >&2; continue; }
  png="$out/$(printf '%s-%02d-%s.png' "$label" "$i" "$(fmt "$s")")"
  ffmpeg -y -ss 1 -i "$clip" -frames:v 1 -q:v 2 "$png" -loglevel error
  echo "FRAME $png $(fmt "$s")"
done
