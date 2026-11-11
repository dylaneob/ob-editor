#!/bin/bash
# still_hd.sh ID TIME CROP|none OUT -> graded 1920x1080 still
C="$3"; [ "$C" = "none" ] && C=""
ffmpeg -nostdin -loglevel error -y -ss "$2" -i "${OB_SRC:-/Volumes/T7/C4352.MP4}" -i ~/ob-editor/luts/ob_grade_warmtan_hald.png \
  -filter_complex "[0:v]${C}scale=1920:1080[v];[v][1:v]haldclut=interp=tetrahedral" -frames:v 1 -q:v 2 "$4"
