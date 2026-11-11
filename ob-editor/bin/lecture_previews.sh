#!/bin/bash
# Phone previews for the lecture delivery page (Artifact files max 15 MB each): each A master at 720x1280,
# two-pass x264 ~1.35 Mbps + 96k AAC (~14 MB for 75 s), the first 9 s of each V, and the covers.
# The full-quality files stay on T7; these exist only to watch on a phone.
#   lecture_previews.sh T7_OUT_DIR DEST_DIR
set -euo pipefail
src="$1"; dst="$2"; mkdir -p "$dst"
for n in L05 L02 HZ; do
  pl="$dst/pass_$n"
  ffmpeg -nostdin -loglevel error -y -i "$src/${n}_A.mp4" -vf scale=720:1280:flags=lanczos -c:v libx264 -preset slow -b:v 1350k \
    -pass 1 -passlogfile "$pl" -an -f mp4 /dev/null
  ffmpeg -nostdin -loglevel error -y -i "$src/${n}_A.mp4" -vf scale=720:1280:flags=lanczos -c:v libx264 -preset slow -b:v 1350k \
    -maxrate 2000k -bufsize 3000k -pass 2 -passlogfile "$pl" -c:a aac -b:a 96k -movflags +faststart "$dst/${n}_A.mp4"
  ffmpeg -nostdin -loglevel error -y -t 9 -i "$src/${n}_V.mp4" -vf scale=720:1280:flags=lanczos -c:v libx264 -preset slow -crf 23 \
    -maxrate 2500k -bufsize 4000k -c:a aac -b:a 96k -movflags +faststart "$dst/${n}_V8.mp4"
  ffmpeg -nostdin -loglevel error -y -i "$src/${n}_cover.jpg" -vf scale=720:1280:flags=lanczos -q:v 4 "$dst/${n}_cover.jpg"
  rm -f "$pl"*
  echo "$n: A $(( $(stat -f %z "$dst/${n}_A.mp4") / 1000000 )) MB, V8 $(( $(stat -f %z "$dst/${n}_V8.mp4") / 1000 )) KB"
done
