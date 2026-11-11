#!/bin/bash
# assemble_when_free.sh WORK OUT LOG -> runs assemble.py WORK OUT --keep once no other session is rendering
# (the 8 GB Mac crashed with two 4K renders on 2026-10-16). Environment (OB_SRC, OB_MASTER, OB_MUSIC, ...) passes through.
W="$1"; OUT="$2"; LOG="$3"
# 2026-11-03 Mac mini M5 Pro 64 GB: wait only while OB_MAX_RENDERS (default 3) renders already run (was: wait for zero, 8 GB Air)
busy() { [ "$(pgrep -f "bin/assemble[.]py|react_render[.]py|lecture_render[.]py|tier_render[.]py|hyperframes render" | wc -l | tr -d " ")" -ge "${OB_MAX_RENDERS:-3}" ]; }
echo "waiting for other renders ($(date +%H:%M))" >> "$LOG"
clear=0; while [ $clear -lt 2 ]; do if busy; then clear=0; else clear=$((clear + 1)); fi; sleep 20; done
echo "machine free, starting ($(date +%H:%M))" >> "$LOG"
cd ~/ob-editor || exit 1
python3 -I bin/assemble.py "$W" "$OUT" --keep >> "$LOG" 2>&1
echo "exit $? ($(date +%H:%M))" >> "$LOG"
