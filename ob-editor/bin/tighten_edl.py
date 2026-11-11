#!/usr/bin/env python3
"""Tight cuts for talking-head EDLs (OB 2026-10-16: "little dead space after full sentences").

  python3 tighten_edl.py EDL.json TAKE_16k.wav CHUNKS.json

For each row it finds the real word edges with a 10 ms level (threshold max(-48 dB, floor + 8)):
  src_in  = the onset that runs into the chunk start, minus 30 ms
  src_out = the decay that runs out of the chunk end, plus 30 ms
Both searches stop at the neighbouring speech in the SOURCE (previous chunk end / next chunk start), so a
cut can never reach into another sentence. Rows marked "explicit_out" keep their hand-picked src_out.
If two rows touch or overlap in the source (no silence left between them), or the first is marked
"keep_join", they are merged and the natural pause stays.
Gaps stay as designed (they are the pause the viewer hears after the word's own decay).
"""
import json, sys
import numpy as np
from scipy.io import wavfile

def main():
    edl, wav, chunks_p = sys.argv[1:4]
    spec = json.load(open(edl)); chunks = json.load(open(chunks_p))
    sr, x = wavfile.read(wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x; x /= 32768.0
    hop = int(sr * 0.01); n = len(x) // hop
    L = 10 * np.log10(np.convolve((x[:n * hop].reshape(n, hop) ** 2).mean(1), np.ones(3) / 3, mode="same") + 1e-12)
    th = max(-48.0, float(np.percentile(L, 10)) + 8)
    starts = sorted(c["start"] for c in chunks); ends = sorted(c["end"] for c in chunks)
    hot = lambda t: 0 <= int(t * 100) < n and L[int(t * 100)] > th
    near = lambda t, d: any(hot(t + k * 0.01 * d) for k in range(1, 7))     # bridges stop closures (the t in "realistic") up to 60 ms
    out = []
    for r in spec["rows"]:
        s, e = r["src_in"] + 0.06, r["src_out"] - 0.08          # back to the chunk edges
        prv = max([q for q in ends if q <= s - 0.02] + [s - 0.6]); nxt = min([q for q in starts if q >= e + 0.02] + [e + 0.6])
        a = s                                   # onsets are short; an inhale is 0.2 s+ and is dead air: cap at 0.18 s
        while a - 0.01 > max(prv + 0.04, s - 0.18) and near(a, -1): a -= 0.01
        b = e                                   # decays and final fricatives: cap at 0.20 s
        if not r.get("explicit_out"):
            while b + 0.01 < min(nxt - 0.04, e + 0.20) and near(b, 1): b += 0.01
        r = dict(r, src_in=round(max(prv + 0.02, a - 0.03), 3), src_out=round(r["src_out"] if r.get("explicit_out") else min(nxt - 0.02, b + 0.03), 3))
        out.append(r)
    # rows that touch or overlap in the source (or are marked keep_join) are JOINED, not merged: one shared cut at
    # the quietest 10 ms between their chunks, gap 0, so the sound runs straight through and each row keeps its cue
    merged = out
    for i in range(len(out) - 1):
        r, q = out[i], out[i + 1]
        e_i, s_n = r["src_out"], q["src_in"]
        if not (-0.5 < s_n - e_i < 0.6) or r.get("explicit_out"): continue
        if s_n - e_i < 0.02 or r.get("keep_join"):
            lo, hi = sorted((e_i, s_n)); lo, hi = lo - 0.25, hi + 0.25
            i0, i1 = int(lo * 100), int(hi * 100); k = i0 + int(np.argmin(L[i0:i1])); cut = round(k / 100, 3)
            r["src_out"] = cut; q["src_in"] = cut; r["gap"] = 0.0
            print("  joined at", cut, "s:", r["caption"][-35:], "|", q["caption"][:30])
    t = 0.0
    for r in merged:
        d = r["src_out"] - r["src_in"]; r["edit_in"] = round(t, 3); r["edit_out"] = round(t + d, 3); t += d + r.get("gap", 0)
    spec["rows"] = merged; spec["duration"] = round(t, 2)
    json.dump(spec, open(edl, "w"), indent=1)
    print(f"{edl}: {len(merged)} rows, {spec['duration']} s (threshold {th:.1f} dB)")

if __name__ == "__main__":
    main()
