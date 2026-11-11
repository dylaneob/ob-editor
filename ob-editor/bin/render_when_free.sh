#!/bin/bash
# Render reels one at a time, only once no other session is rendering (the 8 GB Mac crashed with two renders on 2026-10-16).
#   render_when_free.sh WORK LOG NAME [NAME ...]     (runs lecture_render.py WORK NAME for each NAME)
W="$1"; LOG="$2"; shift 2
# 2026-11-03 Mac mini M5 Pro 64 GB: wait only while OB_MAX_RENDERS (default 3) renders already run (was: wait for zero, 8 GB Air)
busy() { [ "$(pgrep -f "assemble.py|react_render.py|hyperframes render /Volumes/T7/OB-EDITS/C4[^1]" | wc -l | tr -d " ")" -ge "${OB_MAX_RENDERS:-3}" ]; }
echo "waiting for other renders ($(date +%H:%M))" >> "$LOG"
clear=0; while [ $clear -lt 2 ]; do if busy; then clear=0; else clear=$((clear + 1)); fi; sleep 30; done
echo "machine free, starting ($(date +%H:%M))" >> "$LOG"
cd ~/ob-editor || exit 1
for n in "$@"; do python3 -I bin/lecture_render.py "$W" "$n" >> "$LOG" 2>&1 || { echo "exit 1 ($n)" >> "$LOG"; exit 1; }; done
echo "exit 0 ($(date +%H:%M))" >> "$LOG"
