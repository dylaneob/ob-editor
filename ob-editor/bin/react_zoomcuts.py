#!/usr/bin/env python3
"""Zoom cuts inside long OB shots (C4354, 2026-10-17): a shot over 10 s is split at pauses between sentences into 5-11 s
pieces that alternate wide / punch-in, so long talking stretches keep moving (retention). The audio is untouched: every
split sits on the quietest 20 ms frame of a real pause (< -45 dB, from the close mic), preferring sentence ends.

  python3 -I react_zoomcuts.py WORK_DIR [--apply]   (keeps qc/react_cutlist_pre_zoom.json)
"""
import json, os, re, shutil, sys
import numpy as np
from scipy.io import wavfile
W = sys.argv[1]; FPS = 30000 / 1001; fr = lambda t: int(round(t * FPS)); ft = lambda f: f * 1001 / 30000
CL = json.load(open(f"{W}/react_cutlist.json")); words = json.load(open(f"{W}/mic_words_clean.json"))["words"]
sr, x = wavfile.read(f"{W}/mic16.wav"); x = x.astype(np.float64) / 32768; H = int(0.02 * sr); n = len(x) // H
db = 10 * np.log10((x[:n * H].reshape(n, H) ** 2).mean(1) + 1e-12)


def pauses(a, b):
    """(time, is_sentence_end) at quiet points between words inside [a, b]"""
    ws = [w for w in words if a <= w[0] < b]; out = []
    for w, nx in zip(ws, ws[1:]):
        lo, hi = w[1] - 0.05, nx[0] + 0.05
        i0, i1 = int(lo / 0.02), max(int(lo / 0.02) + 1, int(hi / 0.02))
        if i1 - i0 < 2: continue
        j = i0 + int(np.argmin(db[i0:i1]))
        if db[j] < -45: out.append(((j + 0.5) * 0.02, bool(re.search(r"[.?!]$", w[2]))))
    return out


new, log = [], []
for s in CL["shots"]:
    d = s["src_out"] - s["src_in"]
    if s["layout"] != "ob" or d <= 10: new.append(s); continue
    P = [p for p in pauses(s["src_in"], s["src_out"]) if s["src_in"] + 4 < p[0] < s["src_out"] - 4]
    cuts, t = [], s["src_in"]
    while s["src_out"] - t > 11:
        c = [p for p in P if t + 5 <= p[0] <= t + 11]
        if not c: c = [p for p in P if t + 4 <= p[0] <= t + 14]
        if not c: break
        best = min(c, key=lambda p: (not p[1], abs(p[0] - (t + 8))))   # sentence ends first, then nearest to 8 s
        cuts.append(best[0]); t = best[0]
    if not cuts: new.append(s); continue
    edges = [s["src_in"]] + [round(c, 3) for c in cuts] + [s["src_out"]]; f = s.get("framing", "wide")
    for k in range(len(edges) - 1):
        new.append(dict(s, src_in=edges[k], src_out=edges[k + 1], framing=f, zoomcut=k > 0)); f = "punch" if f == "wide" else "wide"
    log.append(f"OB {s['src_in']:7.1f}-{s['src_out']:7.1f} ({d:4.0f}s) -> {len(edges) - 1} pieces")
# neighbours across a split never share a framing
for a, b in zip(new, new[1:]):
    if b.get("zoomcut") and a["layout"] == "ob" and a.get("framing") == b.get("framing"): b["framing"] = "punch" if a["framing"] == "wide" else "wide"
fe = 0
for s in new:
    m = fr(s["dur"]) if s["layout"] == "insert" else max(0, fr(s["src_out"]) - fr(s["src_in"]))
    s["edit_in"], s["edit_out"] = round(ft(fe), 4), round(ft(fe + m), 4); fe += m
print("\n".join(log)); print(f"{len(CL['shots'])} -> {len(new)} shots; length {ft(fe):.3f} s (unchanged: zoom cuts only)")
if "--apply" not in sys.argv: print("dry run"); sys.exit()
shutil.copy2(f"{W}/react_cutlist.json", f"{W}/qc/react_cutlist_pre_zoom.json")
CL["shots"] = new; CL["total"] = round(ft(fe), 3); json.dump(CL, open(f"{W}/react_cutlist.json", "w"), indent=1); print("applied")
