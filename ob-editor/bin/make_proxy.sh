#!/bin/bash
# make_proxy.sh SRC [OUT]
# One-time low-res copy of a camera file, next to it: SRC dir / NAME.proxy.mp4, 960x540, H.264, a key frame every 15 frames, no B-frames,
# every frame kept (same frame count and same timestamps as SRC, so frame N and time T mean the same thing in both), no audio, colour
# tags copied. A still comes out of it in about 50 ms against about 480 ms from the 4K file (measured 2026-10-21, 10x), and it is about
# 100x smaller on a talking head (a 20 s window of C4367: 1.2 MB, so roughly 230 MB for the whole 63-minute file; more with motion).
# Never overwrites: an existing proxy that is newer than SRC is left alone (PROXY_FORCE=1 to redo it). Written to NAME.proxy.mp4.part
# first, then renamed. Run it ONCE per camera file, not during a 4K render (it decodes the whole file: 10 to 50 minutes for C4367 depending
# on load; the 20 s test window ran at 35 frames a second with 2 threads on a busy machine).
#
# WHO READS THE PROXY (and how). The proxy is for looking, never for delivering: finals, thumbnails, hero stills and anything that
# ships read the 4K source.
#   reads the proxy
#     stills for mocks and breakdown sheets (bin/still.sh, stills.py, story/shot_stills.py, mock_shots.js inputs): they output 960x540
#       or smaller, so a proxy frame is enough. Point them at it with OB_SRC=/path/NAME.proxy.mp4. Their crop strings are written in 4K
#       pixels (punch-in: crop=3200:1800:320:120), so multiply every number by 960/3840 = 0.25 (crop=800:450:80:30) or put
#       scale=3840:2160 in front of the old crop; a 1080p still taken from the proxy is an upscale, use the source for those.
#     breakdown contact sheets, frame strips and eye strips (facestrips.py, frame_sheet.py): same OB_SRC and crop rule.
#     gaze scans (bin/gaze_raw.py): NOT worth it. On a 20 s window of C4367 a proxy scan (--crop 400:325:275:88 --width 800, the same
#       face region at a quarter of the size) agreed with the 4K rows on 93% of samples (pupil_y off by 0.03 on average), found all 6
#       runs and added 2, and was only about 1.5x faster (the Vision pass costs as much as the decode). Scan the 4K file, once per raw take.
#     head_clear.py (face boxes for overlay slots): reads OB_SRC but reports 4K coordinates; do NOT point it at the proxy.
#   reads the 4K source: assemble.py and every render, thumb_frames.py, hero and thumbnail stills, match_grade.py, sync_av.py, vmaf and
#     any QC that measures the final picture, doc/clip prep that is cut from the original file.
# Optional environment: PROXY_FORCE=1, PROXY_W=960 (width; height follows, rounded to even), PROXY_CRF=24, PROXY_HW=1 (hardware decode:
# faster, not bit-identical), PROXY_THREADS=0 (ffmpeg threads; 2 while another job runs), PROXY_SS=sec PROXY_T=sec (encode only a window, for
# tests; the frame times then start at 0 in the proxy).
set -u
SRC="${1:-}"; [ -f "$SRC" ] || { echo "usage: make_proxy.sh SRC [OUT]   (SRC must be a file)" >&2; exit 2; }
FF=/opt/homebrew/bin/ffmpeg; FP=/opt/homebrew/bin/ffprobe
dir="$(cd "$(dirname "$SRC")" && pwd)"; base="$(basename "$SRC")"; stem="${base%.*}"
OUT="${2:-$dir/$stem.proxy.mp4}"; PART="$OUT.part"
W="${PROXY_W:-960}"; CRF="${PROXY_CRF:-24}"; THR="${PROXY_THREADS:-0}"
if [ -e "$OUT" ] && [ "$OUT" -nt "$SRC" ] && [ "${PROXY_FORCE:-0}" != "1" ]; then echo "proxy exists and is newer than the source, left alone: $OUT"; exit 0; fi
# source facts (container header only)
probe() { "$FP" -v error -select_streams v:0 -show_entries "stream=$1" -of csv=p=0 "$SRC" 2>/dev/null | head -1; }
sw=$(probe width); sh=$(probe height); nb=$(probe nb_frames); cs=$(probe color_space); ct=$(probe color_transfer); cp=$(probe color_primaries)
[ -n "${sw:-}" ] && [ -n "${sh:-}" ] || { echo "make_proxy: ffprobe cannot read a video stream in $SRC" >&2; exit 2; }
H=$(( (W * sh / sw + 1) / 2 * 2 ))
VF="scale=${W}:${H}:flags=area,format=yuv420p"
TAGS=(); [ "${cs:-}" = "bt709" ] && TAGS+=(-colorspace bt709); [ "${ct:-}" = "bt709" ] && TAGS+=(-color_trc bt709); [ "${cp:-}" = "bt709" ] && TAGS+=(-color_primaries bt709)
WIN=(); IN=(); [ -n "${PROXY_SS:-}" ] && IN+=(-ss "$PROXY_SS"); [ -n "${PROXY_T:-}" ] && WIN+=(-t "$PROXY_T")
HW=(); [ "${PROXY_HW:-0}" = "1" ] && HW=(-hwaccel videotoolbox)
mkdir -p "$(dirname "$OUT")"
echo "proxy: $SRC (${sw}x${sh}, $nb frames) -> $OUT (${W}x${H}, CRF $CRF, key frame every 15)"
t0=$(date +%s)
"$FF" -nostdin -hide_banner -loglevel error -stats -stats_period 10 -y -threads "$THR" ${HW[@]+"${HW[@]}"} ${IN[@]+"${IN[@]}"} -i "$SRC" ${WIN[@]+"${WIN[@]}"} -map 0:v:0 -an -sn -dn \
  -vf "$VF" -fps_mode passthrough -c:v libx264 -preset veryfast -crf "$CRF" -profile:v high -pix_fmt yuv420p -bf 0 -g 15 \
  -x264-params keyint=15:min-keyint=15:scenecut=0 ${TAGS[@]+"${TAGS[@]}"} -video_track_timescale 30000 -movflags +faststart \
  -metadata comment="proxy of $base: ${W}x${H}, for looking only, never deliver" -f mp4 "$PART"
rc=$?; [ $rc -eq 0 ] || { echo "make_proxy: ffmpeg failed (exit $rc); partial file left at $PART" >&2; exit $rc; }
# checks: frame count (the whole file only), size, key frame spacing
pn=$("$FP" -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 "$PART")
keys=$("$FP" -v error -select_streams v:0 -show_entries packet=flags -of csv=p=0 "$PART" | grep -c '^K')
sz=$(stat -f %z "$PART"); el=$(( $(date +%s) - t0 ))
if [ -z "${PROXY_SS:-}${PROXY_T:-}" ] && [ -n "${nb:-}" ] && [ "$nb" != "N/A" ] && [ "$pn" != "$nb" ]; then
  # a header count can include frames an edit list hides (a stream-copied cut): then the durations must still agree to 1.5 frames
  sd=$(probe duration); pd=$("$FP" -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$PART" | head -1)
  if awk -v a="$sd" -v b="$pd" 'BEGIN { d = a - b; if (d < 0) d = -d; exit !(d < 0.05) }'; then
    echo "note: header says $nb frames, the proxy has $pn, durations agree ($sd s vs $pd s): hidden pre-roll in the source, fine"
  else
    echo "make_proxy: FRAME COUNT MISMATCH: source $nb frames / $sd s, proxy $pn frames / $pd s. Left at $PART, not renamed." >&2; exit 3
  fi
fi
mv "$PART" "$OUT"
echo "proxy done: $OUT  ${W}x${H}  $pn frames  $keys key frames (one per $(( pn / (keys > 0 ? keys : 1) )) frames)  $(( sz / 1048576 )) MB  ${el}s"
