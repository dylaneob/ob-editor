#!/bin/bash
# lstill.sh TAKE TIME CROP|none LUT OUT -> graded 1080x1920 still
C="$3"; [ "$C" = "none" ] && C=""
ffmpeg -nostdin -loglevel error -y -ss "$2" -i "/Volumes/T7/$1.MP4" -i "$4" \
  -filter_complex "[0:v]${C}scale=1080:1920:flags=lanczos[v];[v][1:v]haldclut=interp=tetrahedral" -frames:v 1 -q:v 3 "$5"
