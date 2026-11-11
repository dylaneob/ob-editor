#!/usr/bin/env python3
"""Prove no cut in a lecture EDL clips a word, and fix the edges that do.

  python3 lecture_qc.py EDL.json TAKE_16k.wav CHUNKS.json [--fix] [--min-gap 0.10]

Chunks were cut at -42 dB (20 ms frames), so soft word endings ("sides", "eating it") and soft onsets
("Do it") can sit just outside a piece. This scans each edge with a 100 ms-smoothed level against
max(-48 dB, noise floor + 8 dB), judging by energy, not Whisper word times:
  - tail: speech-level audio running on from src_out = the last word's decay -> clipped
  - head: speech-level audio running into src_in = the first word's onset -> clipped
  - gap:  the render fills each row's gap with the source that follows src_out, so that stretch must
          hold no speech (else the next sentence's first sound leaks in). A row with "fill": "room"
          gets room tone instead (use it to keep a beat where the source runs straight on).
--fix moves src_out past the decay and src_in before the onset, takes the added time out of the
neighbouring pause (min 0.10 s) so the reel length holds, clamps each gap before the next speech in
the source, rewrites rows' edit times, and re-checks. Ship only at 0 problems.
"""
import json, sys
import numpy as np
from scipy.io import wavfile

PAD_T, PAD_H, MIN_GAP = 0.05, 0.04, 0.10


def level_db(x, sr):
    hop = int(sr * 0.01); n = len(x) // hop
    e = (x[:n * hop].reshape(n, hop) ** 2).mean(1)
    return 10 * np.log10(np.convolve(e, np.ones(10) / 10, mode="same") + 1e-12)


class Audio:
    def __init__(self, wav):
        sr, x = wavfile.read(wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x
        self.L = level_db(x / 32768.0, sr); self.floor = float(np.percentile(self.L, 10))
        self.th = max(-48.0, self.floor + 8); self.n = len(self.L)

    def hot(self, t): i = int(round(t * 100)); return 0 <= i < self.n and self.L[i] > self.th

    def run_fwd(self, t, limit):           # end of the speech-level run that touches t (or t if none)
        if not (self.hot(t) or self.hot(t + 0.01) or self.hot(t + 0.02)): return t
        u = t
        while u < limit and (self.hot(u) or self.hot(u + 0.01)): u += 0.01
        return u

    def run_back(self, t, limit):          # start of the speech-level run that touches t (or t if none)
        if not (self.hot(t - 0.01) or self.hot(t - 0.02) or self.hot(t - 0.03)): return t
        u = t
        while u > limit and (self.hot(u - 0.01) or self.hot(u - 0.02)): u -= 0.01
        return u

    def first_hot(self, a, b):             # first speech-level 80 ms run inside [a, b]
        t = a
        while t < b:
            if all(self.hot(t + k * 0.01) for k in range(8)): return t
            t += 0.01
        return None


def check(spec, A, starts, ends, fix):
    rows = spec["rows"]; problems = []
    for i, r in enumerate(rows):
        a, b = r["src_in"], r["src_out"]
        nxt = min([s for s in starts if s > b - 0.02] + [b + 3.0])
        prv = max([e for e in ends if e < a + 0.02] + [a - 3.0])
        tail_end = A.run_fwd(b, nxt)
        head_start = A.run_back(a, prv)
        if tail_end > b + 0.015:
            problems.append(f"shot {i + 1} tail: word decay runs {tail_end - b:.2f} s past the cut | {r['caption'][-40:]!r}")
            if fix:
                ext = round(tail_end + PAD_T - b, 3); r["src_out"] = round(b + ext, 3); r["gap"] = round(max(MIN_GAP, r.get("gap", 0) - ext), 3)
        if head_start < a - 0.015:
            problems.append(f"shot {i + 1} head: word onset starts {a - head_start:.2f} s before the cut | {r['caption'][:40]!r}")
            if fix:
                ext = round(a - (head_start - PAD_H), 3); r["src_in"] = round(a - ext, 3)
                if i > 0: rows[i - 1]["gap"] = round(max(MIN_GAP, rows[i - 1].get("gap", 0) - ext), 3)
        # the gap is filled with the source after src_out: it must not reach the next speech
        b2, g = r["src_out"], r.get("gap", 0)
        if r.get("fill") == "room": continue                  # gap rendered as room tone, not source
        leak = A.first_hot(b2 + 0.02, b2 + g)
        if leak is not None:
            problems.append(f"shot {i + 1} gap: next speech in the source starts {leak - b2:.2f} s after the cut, inside the {g:.2f} s pause")
            if fix: r["gap"] = round(max(0.0, leak - 0.04 - b2), 3)
    return problems


def main():
    global MIN_GAP
    edl, wav, chunks_p = sys.argv[1:4]; fix = "--fix" in sys.argv
    if "--min-gap" in sys.argv: MIN_GAP = float(sys.argv[sys.argv.index("--min-gap") + 1])   # tight pacing: 0.03
    spec = json.load(open(edl)); chunks = json.load(open(chunks_p)); A = Audio(wav)
    starts = sorted(c["start"] for c in chunks); ends = sorted(c["end"] for c in chunks)
    print(f"{edl}: noise floor {A.floor:.1f} dB, threshold {A.th:.1f} dB, {spec['duration']} s")
    probs = check(spec, A, starts, ends, fix)
    for p in probs: print("  " + p)
    if fix and probs:
        t = 0.0
        for r in spec["rows"]:
            d = r["src_out"] - r["src_in"]; r["edit_in"] = round(t, 3); r["edit_out"] = round(t + d, 3); t += d + r.get("gap", 0)
        spec["duration"] = round(t, 2); json.dump(spec, open(edl, "w"), indent=1)
        again = check(json.load(open(edl)), A, starts, ends, False)
        print(f"  fixed {len(probs)}; re-check: {len(again)} problems; duration now {spec['duration']} s")
        for p in again: print("    still: " + p)
    else:
        print(f"  {len(probs)} problems")


if __name__ == "__main__":
    main()
