#!/bin/bash
# Render tier reels one at a time, once no other render is running (8 GB Mac: two renders at once crashed it on 2026-10-16).
#   tier_render_queue.sh WORK LOG NAME:OUT.mp4 [NAME:OUT.mp4 ...]      (launch detached; see tier_render.py)
W="$1"; LOG="$2"; shift 2
# 2026-11-03 Mac mini M5 Pro 64 GB: wait only while OB_MAX_RENDERS (default 3) renders already run (was: wait for zero, 8 GB Air)
busy() { [ "$(pgrep -f "assemble.py|react_render.py|lecture_render.py|hyperframes render" | wc -l | tr -d " ")" -ge "${OB_MAX_RENDERS:-3}" ]; }
echo "waiting for other renders ($(date +%H:%M))" >> "$LOG"
clear=0; while [ $clear -lt 2 ]; do if busy; then clear=0; else clear=$((clear + 1)); fi; sleep 15; done
echo "machine free, starting ($(date +%H:%M))" >> "$LOG"
cd ~/ob-editor || exit 1
for job in "$@"; do
  n="${job%%:*}"; o="${job#*:}"
  HYPERFRAMES_RENDER_DETACHED=1 python3 -I bin/tier_render.py "$W" "$n" --out "$o" >> "$LOG" 2>&1 || { echo "exit 1 ($n)" >> "$LOG"; exit 1; }
done
echo "exit 0 ($(date +%H:%M))" >> "$LOG"
