#!/usr/bin/env python3
"""Piece edges for a cut script's sync model from qc/lag_curve.json (2026-10-31, the 10-30 night takes).
The MOTIV lag can wander (C4401 2: -15, -8, -16, -10, then -31 ms by the end) instead of drifting in one line, so a single
line misses mid-take shots by ~8 ms and the in-shot GCC check then rejects the right measurement. This splits the curve
where a robust line stops fitting: greedy left to right, each piece grows while the lower-envelope 15 s medians stay within
TOL ms of its own line fit (min piece MIN s). Prints the STEPS list for story/cut_cfg.json.

  python3 -I lag_steps.py WORK [--tol 2.0] [--min 45]
"""
import json, sys
import numpy as np
W = sys.argv[1]
tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 2.0
mn = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 45.0
p = np.array([q for q in json.load(open(f"{W}/qc/lag_curve.json"))["pts"] if q[2] >= 8.0])
t, l = p[:, 0], p[:, 1]
cent, med = [], []
for a in np.arange(t.min(), t.max(), 15.0):
    m = (t >= a) & (t < a + 15)
    if m.sum() >= 6:
        v = l[m]; lo = np.percentile(v, 25); cent.append(a + 7.5); med.append(float(np.median(v[v <= lo + 1.5])))
cent, med = np.array(cent), np.array(med)
steps, i0 = [], 0
while i0 < len(cent) - 1:
    j = i0 + 1
    while j + 1 < len(cent):
        k, b = np.polyfit(cent[i0:j + 2], med[i0:j + 2], 1)
        if np.max(np.abs(med[i0:j + 2] - (k * cent[i0:j + 2] + b))) > tol and cent[j] - cent[i0] >= mn: break
        j += 1
    if j + 1 >= len(cent): break
    steps.append(round(float((cent[j] + cent[j + 1]) / 2), 1)); i0 = j + 1
print("15 s medians:", " ".join(f"{c:.0f}:{m:+.1f}" for c, m in zip(cent, med)))
print("STEPS", json.dumps(steps))
