#!/bin/bash
# Run the remaining lecture renders only once no other session is rendering (8 GB Mac: two renders at once
# ran it out of memory on 2026-10-16 and crashed the app). Waits for assemble.py / react_render.py /
# HyperFrames renders of other projects to be gone for 60 s straight, then renders one job at a time.
#   lecture_queue_when_free.sh WORK LOG
W="$1"; LOG="$2"
# 2026-11-03 Mac mini M5 Pro 64 GB: wait only while OB_MAX_RENDERS (default 3) renders already run (was: wait for zero, 8 GB Air)
busy() { [ "$(pgrep -f "assemble.py|react_render.py|hyperframes render /Volumes/T7/OB-EDITS/C43" | wc -l | tr -d " ")" -ge "${OB_MAX_RENDERS:-3}" ]; }
echo "waiting for other renders to finish ($(date +%H:%M))" >> "$LOG"
clear=0
while [ $clear -lt 2 ]; do
  if busy; then clear=0; else clear=$((clear + 1)); fi
  sleep 30
done
echo "machine free, starting ($(date +%H:%M))" >> "$LOG"
cd ~/ob-editor || exit 1
python3 -I bin/lecture_render.py "$W" HZ >> "$LOG" 2>&1 || { echo "exit 1 (HZ)" >> "$LOG"; exit 1; }
python3 -I bin/lecture_render.py "$W" L05 >> "$LOG" 2>&1 || { echo "exit 1 (L05)" >> "$LOG"; exit 1; }
for n in L05 L02 HZ; do
  python3 -I bin/lecture_render.py "$W" "$n" --flash "$W/${n}V_flash.json" >> "$LOG" 2>&1 || { echo "exit 1 (${n}V)" >> "$LOG"; exit 1; }
done
echo "exit 0 ($(date +%H:%M))" >> "$LOG"
