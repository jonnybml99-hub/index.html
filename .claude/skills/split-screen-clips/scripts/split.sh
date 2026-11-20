#!/bin/bash
# Build a vertical 1080x1920 short from a 1920x1080 stream/gameplay segment.
#
# Usage:
#   split.sh INPUT.mp4 OUTPUT.mp4 "TITLE" [CAPTION]
#
# Layouts (env LAYOUT):
#   facecam  (default) title band on top, streamer facecam (top, 1080x800),
#            white divider, gameplay (bottom, 1080x740), blurred gameplay behind.
#   gameplay no facecam: title band, large gameplay (1080x1080), optional
#            caption text under it (e.g. "Location: Vice Beach, north pier").
#
# Crop boxes on the 1920x1080 source, as w:h:x:y (override per video):
#   CAM   facecam box          default 321:238:45:463  (Speed stream overlay)
#   GAME  gameplay box         default 1330:912:390:90 (skips overlay, logo, HUD)
#   GAMESQ gameplay box for LAYOUT=gameplay  default 1080:1080:420:0
#
# Example:
#   CAM=400:300:1500:700 split.sh in.mp4 out.mp4 "Bro left the BABY"
#   LAYOUT=gameplay split.sh in.mp4 out.mp4 "Paul Walker's car in GTA 6" "Location: ..."
set -euo pipefail
IN="$1"; OUT="$2"; TITLE="${3:-}"; CAPTION="${4:-}"
LAYOUT="${LAYOUT:-facecam}"
CAM="${CAM:-321:238:45:463}"
GAME="${GAME:-1330:912:390:90}"
GAMESQ="${GAMESQ:-1080:1080:420:0}"
FONT="${FONT:-$(fc-match -f '%{file}' 'Inter Display:bold' 2>/dev/null || true)}"
[ -f "$FONT" ] || FONT=$(fc-match -f '%{file}' 'sans:bold')

TF=$(mktemp); CF=$(mktemp); trap 'rm -f "$TF" "$CF"' EXIT
printf '%s' "$TITLE" > "$TF"; printf '%s' "$CAPTION" > "$CF"

TXT="drawtext=fontfile=$FONT:textfile=$TF:fontsize=58:fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y=45"

if [ "$LAYOUT" = "facecam" ]; then
  FILTER="
[0:v]split=3[a][b][c];
[a]crop=1440:960:240:60,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.15[bg];
[b]crop=$CAM,scale=1080:800:flags=lanczos,unsharp=5:5:0.8[cam];
[c]crop=$GAME,scale=1080:740:flags=lanczos[game];
[bg][cam]overlay=0:150[t1];
[t1][game]overlay=0:960,
drawbox=x=0:y=950:w=1080:h=10:color=white@0.9:t=fill,
$TXT[v]"
elif [ "$LAYOUT" = "gameplay" ]; then
  CAPTXT=""
  if [ -n "$CAPTION" ]; then
    CAPTXT=",drawtext=fontfile=$FONT:textfile=$CF:fontsize=50:fontcolor=yellow:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1500"
  fi
  FILTER="
[0:v]split=2[a][c];
[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.2[bg];
[c]crop=$GAMESQ,scale=1080:1080:flags=lanczos[game];
[bg][game]overlay=0:380,
$TXT$CAPTXT[v]"
else
  echo "unknown LAYOUT=$LAYOUT" >&2; exit 1
fi

ffmpeg -v error -y -i "$IN" -filter_complex "$FILTER" \
  -map "[v]" -map 0:a? -c:v libx264 -preset medium -crf 20 -r 30 \
  -c:a aac -b:a 160k -movflags +faststart "$OUT"
echo "wrote $OUT"
