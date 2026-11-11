#!/usr/bin/env python3
"""Words with their times between two source seconds, and the quietest 5 ms point near given times (2026-10-31, story edits).

  python3 -I words_at.py WORK A B             words from qc/words.json that start in [A, B]
  python3 -I words_at.py WORK --quiet T [T ...] [--win 0.35]
        for each T, the quietest 5 ms of qc/master16k.wav (the synced master) within +-win s (RMS dB), so remove/keep edges land between words
"""
import json, sys
import numpy as np
from scipy.io import wavfile
W = sys.argv[1]
if "--quiet" not in sys.argv:
    a, b = float(sys.argv[2]), float(sys.argv[3])
    for t0, t1, w in json.load(open(f"{W}/qc/words.json"))["words"]:
        if a <= t0 <= b: print(f"{t0:8.2f} {t1:8.2f}  {w}")
    sys.exit()
win = float(sys.argv[sys.argv.index("--win") + 1]) if "--win" in sys.argv else 0.35
ts = [float(x) for x in sys.argv[sys.argv.index("--quiet") + 1:] if not x.startswith("--") and x != str(win)]
sr, x = wavfile.read(f"{W}/qc/master16k.wav", mmap=True)   # the 16-bit mono copy of master_synced.wav (24-bit cannot mmap)
for t in ts:
    i0, i1 = int(max(0, t - win) * sr), int((t + win) * sr)
    seg = np.asarray(x[i0:i1], dtype=np.float64)
    if seg.ndim > 1: seg = seg.mean(1)
    seg /= 32768.0
    h = int(sr * 0.005); n = len(seg) // h
    db = 10 * np.log10((seg[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    k = int(np.argmin(db)); print(f"{t:8.2f} -> {(i0 + k * h + h / 2) / sr:8.3f}  {db[k]:6.1f} dB  (window min of {n} frames)")
