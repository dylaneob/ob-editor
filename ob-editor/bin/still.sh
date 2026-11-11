#!/bin/bash
# still.sh IDX TIME CROP|none [OUTNAME] -> graded 960x540 still of the source at TIME
W="${OB_W:-/Volumes/T7/OB-EDITS/C4352-edit}"
C="$3"; [ "$C" = "none" ] && C=""
OUT="${4:-$W/stills/shot_$1.jpg}"
ffmpeg -nostdin -loglevel error -y -ss "$2" -i "${OB_SRC:-/Volumes/T7/C4352.MP4}" -i ~/ob-editor/luts/ob_grade_warmtan_hald.png \
  -filter_complex "[0:v]${C}scale=960:540[v];[v][1:v]haldclut=interp=tetrahedral" -frames:v 1 -q:v 3 "$OUT"
