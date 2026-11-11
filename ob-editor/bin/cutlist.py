#!/usr/bin/env python3
"""Energy-based cut list for a talking-head take.

Speech is detected from the synced audio's loudness (20 ms frames), never from
Whisper word times (those smear near window starts). Pauses >= MIN_PAUSE are
trimmed to ~KEEP_AFTER + KEEP_BEFORE. Manual removals are applied on top.
Each kept segment alternates framing (wide / punch) so jump cuts read as edits.

  python3 cutlist.py AUDIO.wav OUT.json [--remove 1379.35-1382.58 ...] [--start S] [--end E]
"""
import argparse, json
import numpy as np
from scipy.io import wavfile

HOP = 0.02
THRESH_DB = -45.0     # speech sits around -20..-35 dB; room noise -60..-86 dB
MIN_PAUSE = 0.8       # only pauses at least this long get trimmed
KEEP_AFTER = 0.15     # keep this much after speech ends (soft word tails)
KEEP_BEFORE = 0.20    # keep this much before speech starts (breath / onset)
MIN_SPEECH = 0.12     # ignore blips shorter than this (clicks, mic bumps)


def main():
    global KEEP_AFTER, KEEP_BEFORE, MIN_PAUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--remove", nargs="*", default=[], help="source ranges to drop, e.g. 1379.35-1382.58")
    ap.add_argument("--start", type=float, default=None); ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--keep-after", type=float, default=None, help="word-tail pad (default %.2f s)" % KEEP_AFTER)
    ap.add_argument("--keep-before", type=float, default=None, help="onset pad (default %.2f s)" % KEEP_BEFORE)
    ap.add_argument("--min-pause", type=float, default=None, help="trim pauses at least this long (default %.2f s)" % MIN_PAUSE)
    ap.add_argument("--soft-db", type=float, default=None,
                    help="follow a word's quiet edge (10 ms frames) down to this level before padding, e.g. -50 (off by default)")
    a = ap.parse_args()
    if a.keep_after is not None: KEEP_AFTER = a.keep_after
    if a.keep_before is not None: KEEP_BEFORE = a.keep_before
    if a.min_pause is not None: MIN_PAUSE = a.min_pause

    sr, x = wavfile.read(a.audio)
    # scale by the file's own sample format: a 24-bit WAV reads as int32, and dividing it by 32768 put
    # silence 48 dB too loud, so no pause was ever found (C4365, 2026-10-18). 16-bit files are unchanged.
    scale = {np.dtype("int16"): 32768.0, np.dtype("int32"): 2147483648.0}.get(x.dtype, 1.0)
    x = x.astype(np.float64)
    if x.ndim > 1: x = x.mean(1)
    x /= scale
    hop = int(sr * HOP); n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    voiced = db > THRESH_DB

    # speech runs, dropping blips
    careful = a.soft_db is not None
    runs, i = [], 0
    while i < n:
        if voiced[i]:
            j = i
            while j < n and voiced[j]: j += 1
            if careful or (j - i) * HOP >= MIN_SPEECH: runs.append([i * HOP, j * HOP])
            i = j
        else:
            i += 1
    if careful:
        # With --soft-db a short run is a word fragment when it sits within FRAG_GAP of speech ("by", the "-es" of
        # "minutes" after its "t" closure): it joins that speech. Dropping it, as before, cut straight through the word
        # (C4365). A short run further out (a breath or click in a pause) is still a blip, so long pauses still get trimmed.
        FRAG_GAP = 0.15
        speech = [r[:] for r in runs if r[1] - r[0] >= MIN_SPEECH]
        frags = [r for r in runs if r[1] - r[0] < MIN_SPEECH]
        grew = True
        while grew and frags:
            grew = False
            for f in frags[:]:
                for r in speech:
                    if -FRAG_GAP <= f[0] - r[1] <= FRAG_GAP or -FRAG_GAP <= r[0] - f[1] <= FRAG_GAP:
                        r[0], r[1] = min(r[0], f[0]), max(r[1], f[1]); frags.remove(f); grew = True; break
        runs = sorted(speech)
    # merge runs separated by short gaps (normal word gaps)
    merged = [runs[0]]
    for s, e in runs[1:]:
        if s - merged[-1][1] < MIN_PAUSE: merged[-1][1] = max(merged[-1][1], e)
        else: merged.append([s, e])

    start = a.start if a.start is not None else max(0.0, merged[0][0] - 0.3)
    end = a.end if a.end is not None else merged[-1][1] + 0.6
    if a.soft_db is not None:
        # soft edges (C4365, 2026-10-18): a word's quiet tail ("-tes" of "minutes", the "s" of "trials") can sit under
        # THRESH_DB on 20 ms frames past KEEP_AFTER, so the pad alone clipped it. Follow the edge on 10 ms frames while it
        # stays above soft_db (dips up to 100 ms allowed: the silent closure before a "t" release), up to 0.35 s after a run
        # and 0.15 s before one, then pad as usual.
        h10 = int(sr * 0.01); n10 = len(x) // h10
        d10 = 20 * np.log10(np.sqrt((x[:n10 * h10].reshape(n10, h10) ** 2).mean(1)) + 1e-9)
        def edge(t, direction, limit):
            k0, last, quiet = int(round(t / 0.01)), None, 0
            for j in range(1, int(limit / 0.01) + 1):
                k = k0 + direction * j
                if not 0 <= k < n10: break
                if d10[k] > a.soft_db: last, quiet = k, 0
                else:
                    quiet += 1
                    if quiet >= 10: break
            return t if last is None else (last + (1 if direction > 0 else 0)) * 0.01
        merged = [[min(s, edge(s, -1, 0.15)), max(e, edge(e, 1, 0.35))] for s, e in merged]
    keep = [[max(start, s - KEEP_BEFORE), min(end, e + KEEP_AFTER)] for s, e in merged
            if e > start and s < end]
    for k in range(len(keep) - 1, 0, -1):   # padded neighbours that now touch become one shot
        if keep[k][0] <= keep[k - 1][1]:
            keep[k - 1][1] = keep[k][1]; del keep[k]

    for r in a.remove:  # manual removals
        lo, hi = map(float, r.split("-")); out = []
        for s, e in keep:
            if e <= lo or s >= hi: out.append([s, e]); continue
            if s < lo: out.append([s, lo])
            if e > hi: out.append([hi, e])
        keep = out

    segs, t = [], 0.0
    for k, (s, e) in enumerate(keep):
        d = e - s
        segs.append({"i": k, "src_in": round(s, 3), "src_out": round(e, 3), "dur": round(d, 3),
                     "edit_in": round(t, 3), "edit_out": round(t + d, 3),
                     "framing": "wide" if k % 2 == 0 else "punch"})
        t += d
    json.dump({"segments": segs, "removed_manual": a.remove, "src_start": start, "src_end": end,
               "params": {"thresh_db": THRESH_DB, "min_pause": MIN_PAUSE, "keep_after": KEEP_AFTER, "keep_before": KEEP_BEFORE,
                          "soft_db": a.soft_db}}, open(a.out, "w"), indent=1)
    raw = end - start
    print(f"source {start:.2f}-{end:.2f} ({raw/60:.2f} min) -> edit {t/60:.2f} min, "
          f"{len(segs)} segments, removed {raw - t:.1f} s")


if __name__ == "__main__":
    main()
