#!/usr/bin/env python3
"""Zero dead space cuts for short form (OB's rule; the method he approved on the EkkoVision MASTER1 v4, 2026-10-27: "its amazing").
OB: "immediately after the sound goes down cut, not even 0.1 seconds left over", "rapid fire, fast pace", and after a 1.25x speed-up:
"no i didnt want a literaly speed up, i meant with cuts". 2026-10-28: "short form needs to be fast pace, not speed it up but just cut
absolutely all deadspace". Never fix pace with tempo; fix it with cuts. Long-form YouTube keeps its own join rule.

Ported unchanged from `/Volumes/OB-ARCHIVE/ekko ads/_work/scripts/ekko.py` (line_ref, tighten, pieces_of, the dead-space metric in qc)
so every short-form pipeline cuts the same way. Method and numbers: vault `90-References/ZERO-DEAD-SPACE-CUTS-2026-10-27.md`.

Levels: 30 ms RMS windows every 10 ms of 16 kHz mono, in dB. A line's reference level is the 90th percentile of its windows.
  edges     start on the first window louder than ref - 20 dB (with at most 20 ms of lead-in that stays above ref - 32 dB);
            end on the last such window + 30 ms + at most 50 ms of tail above ref - 32 dB (keeps word-final -s/-t/-f).
            The thresholds follow the line's own speech level, never the room hum: hum-relative thresholds counted breaths, lip
            smacks and shirt rustle as speech and left 0.16-0.21 s of air at every join.
  inside    every run of 70 ms+ under ref - 20 dB inside the line is cut, keeping 30 ms before it and 10 ms after.
  frames    edges round to the NEAREST frame, never outward (outward snapping put up to 66 ms of air back at every join).
  yardstick dead = a run of 60 ms+ under (the render's 90th percentile - 20 dB), first and last 0.3 s ignored. Target: inside the
            reference ads' range, dead <= ~6% of the runtime and a median dead run <= ~0.09 s (Haus/Comfort refs: 0.9-9.6%, median
            ~5%, runs 0.07-0.11 s; approved v4 MASTER1: 3.4%, 0.08 s, longest 0.10 s; the rejected v2 cuts: 9.2-17.4%, 0.16-0.21 s).

Use as a library (pipelines import it):
    import zero_dead as Z
    env = Z.level_env("take_16k.wav")                       # or a float32 mono array at 16 kHz
    pieces = Z.cut_line(env, s, e, fps=30000/1001)          # s, e: the line's word span (source seconds); -> [(a, b), ...]
    # lo/hi keep the edges inside a window: Z.cut_line(env, s, e, fps, lo=prev_line_end, hi=next_line_start)
or from the shell:
    python3 -I zero_dead.py measure FILE [FILE ...]          the yardstick on renders (exit 1 if any is outside the target)
    python3 -I zero_dead.py line AUDIO START END [--fps 29.97] [--lo S] [--hi S]   the pieces for one line, as JSON
    python3 -I zero_dead.py lookoff VIDEO PIECES.json        his eyes at both edges of every piece (Apple Vision, bin/gaze; 3 frames
                                                             per edge, 2 must agree, so a blink is not a flag): flags a piece that
                                                             opens or closes with him looking down, shut-eyed or turned away
Every cut still goes through the word check (whisper medium on the cut audio, diffed against the script: 0 missing or clipped
words) before anything renders; this method keeps word-final consonants, the check proves it.
"""
import json, os, subprocess, sys, tempfile
import numpy as np

SR, HOP, WIN = 16000, 0.01, 0.03
ACTIVE, TAIL = 20.0, 32.0            # dB under the line's p90: speech / word-final tail
LEAD_MAX, TAIL_MAX = 2, 5            # windows (20 ms lead-in, 50 ms tail)
MIN_GAP, KEEP_PRE, KEEP_POST = 0.07, 0.03, 0.01
DEAD_RUN, DEAD_PCT_MAX, DEAD_MED_MAX = 0.06, 6.0, 0.09
GAZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gaze")


def decode(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def level_env(src):
    """dB of 30 ms RMS windows every 10 ms (window i covers i*10 ms .. i*10 ms + 30 ms)."""
    x = decode(src) if isinstance(src, str) else np.asarray(src, np.float32)
    n = (len(x) - 480) // 160
    if n <= 0: return np.zeros(0)
    cs = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    i = 160 * np.arange(n)
    return 20 * np.log10(np.sqrt(np.maximum(cs[i + 480] - cs[i], 0) / 480) + 1e-9)


def line_ref(env, s, e):
    seg = env[int(s / HOP):int(e / HOP)]
    return float(np.percentile(seg, 90)) if len(seg) > 5 else -25.0


def tighten(env, s, e, lo=None, hi=None):
    """The line's edges: first speech window (minus <= 20 ms lead-in), last speech window + 30 ms + <= 50 ms of tail."""
    n = len(env); P = line_ref(env, s, e); A, T = P - ACTIVE, P - TAIL
    lo_i = 0 if lo is None else int(lo / HOP); hi_i = n - 2 if hi is None else min(n - 2, int(hi / HOP))
    i = max(lo_i, int((s - 0.15) / HOP))
    while i < hi_i and env[i] <= A: i += 1
    k = i
    while k > max(lo_i, i - LEAD_MAX) and env[k - 1] > T: k -= 1
    st = k * HOP
    j = min(hi_i, int((e + 0.15) / HOP))
    while j > i and env[j] <= A: j -= 1
    k = j
    while k < min(hi_i, j + TAIL_MAX) and env[k + 1] > T: k += 1
    en = k * HOP + WIN
    if lo is not None: st = max(st, lo)
    if hi is not None: en = min(en, hi)
    return st, en


def pieces_of(env, st, en, fps, min_gap=MIN_GAP):
    """Cut every dead run of min_gap+ inside the line (dead = 20 dB under its speech level); edges to the nearest frame."""
    rnd = lambda t: round(t * fps) / fps
    P = line_ref(env, st, en); A = P - ACTIVE
    i0 = int(round(st / HOP)); i1 = max(i0 + 1, int(round(en / HOP))); q = env[i0:i1] <= A; n = len(q); out = []; cur = st; k = 0
    while k < n:
        if q[k]:
            j = k
            while j < n and q[j]: j += 1
            if k > 0 and j < n and (j - k) * HOP >= min_gap:
                a = (i0 + k) * HOP + KEEP_PRE; b = (i0 + j) * HOP - KEEP_POST
                if b - a > 0.03 and a > cur: out.append((cur, a)); cur = b
            k = j
        else: k += 1
    out.append((cur, en)); m = []
    for a, b in [(rnd(a), rnd(b)) for a, b in out]:
        if m and a <= m[-1][1]: m[-1] = (m[-1][0], max(b, m[-1][1]))
        elif b - a >= 2 / fps: m.append((a, b))
    return m


def cut_line(env, s, e, fps, lo=None, hi=None):
    st, en = tighten(env, s, e, lo, hi)
    return pieces_of(env, st, en, fps)


# ---- word-safe version (2026-10-28). The v4 cuts above were approved on the EkkoVision UGC lines: short punchy lines, close to
# one level. On his everyday talking takes (the 10/10 GUT H5 voice) the same inner cuts deleted soft words that sit more than
# 20 dB under the line's loud syllables ("on", "of", "it", "and", "but", "they're") and broke others ("pound you weigh" heard as
# "brownie whey"): 22 word differences. A level can't tell a soft word from a breath; the word timings can. So the gaps between
# words are cut exactly as v4 cuts them, and nothing inside a word is ever cut.
STRETCH = 0.20   # a run this long without speech inside a word's ASR span is the ASR stretching the word over a pause
BURST_GAP, BURST_LEN = 12, 8   # windows: a closure dip of up to 120 ms, then a release burst of up to 80 ms (-t, -k, -ts)
LEAD_SOFT = 12                 # windows: a soft onset (f-, s-, h-, th-) can start up to 120 ms before the word's first loud window
DIP_MAX = 8                    # windows: a dip under T this short inside a word's span is the word going on ("for | you": 30 ms)
DIP_ON, LEAD_MAX, SOFT_SYL = 4, 25, 6.0   # a soft first syllable before a stop: dip up to 40 ms, lead up to 250 ms, within 6 dB of A


def word_core(env, w, A, T):
    """(on, off) seconds of a word's own sound: from its first to its last window louder than A (the line's p90 - 20 dB), then
    out over its soft parts while they stay above T (p90 - 32 dB): back up to 120 ms (a soft f-, s-, h- onset) and forward until
    the sound goes down, anywhere inside the word's ASR span + 0.1 s ("Not for you." ends on a "you" 25 dB under "Not"; a 50 ms
    cap there cut it to "no"), at most 50 ms past it. Inside the span it bridges dips under T of up to 80 ms (between "for" and
    that "you" the level dips under T for 30 ms). Plus a word-final release: a burst above T of up to 80 ms after a closure
    dip of up to 120 ms ("legi-t", "effect-s") that ends inside the span + 0.1 s. A pause (under T) always ends a word, so
    breaths after a pause are not part of it.
    ASR spans reach back over the pause before a word and run on after it, so a pause of STRETCH+ inside a span splits it:
    a short bit of speech before it is the previous word's tail, and the word ends at the first such pause after its onset.
    A word with no window above A (a very soft "of", "it") keeps its sound above T, and one with none above T its ASR span."""
    n = len(env); k0 = max(0, int(w["s"] / HOP) - 2); k1 = min(int(w["e"] / HOP) + 2, n - 2)
    if k1 <= k0: return w["s"], w["e"]
    act = env[k0:k1 + 1] > A
    if not act.any():
        snd = np.flatnonzero(env[k0:k1 + 1] > T)
        return ((k0 + snd[0]) * HOP, (k0 + snd[-1]) * HOP + WIN) if len(snd) else (w["s"], w["e"])
    L = int(round(STRETCH / HOP)); runs, i = [], 0
    while i < len(act):
        if not act[i]:
            j = i
            while j < len(act) and not act[j]: j += 1
            if j - i >= L and i > 0 and j < len(act): runs.append((i, j))
            i = j
        else: i += 1
    on = int(np.argmax(act))
    for ra, rb in runs:
        if ra >= on and act[rb:].any() and ra - on < 0.6 * len(act): on = rb + int(np.argmax(act[rb:]))
    off = on
    for k in range(on, len(act)):
        if any(ra <= k < rb for ra, rb in runs if ra > on): break
        if act[k]: off = k
    on, off = k0 + on, k0 + off
    k = on
    while k > max(0, on - LEAD_SOFT) and env[k - 1] > T: k -= 1
    # a soft first syllable before a stop closure: "Tri-p-le" (C4378 FDOE) has "Tri" under A, a 30 ms closure under T, then
    # the loud "-ple". The lead-in above stopped at the closure, the cut began on "-ple" and whisper heard "Purple whammy"
    # (2026-10-28). Inside the word's ASR span, step back over a dip under T of up to 40 ms when 30 ms+ of sound above T comes
    # before it and reaches within 6 dB of A (a breath sits lower and stays out), at most 250 ms before the first loud window.
    while True:
        d = k - 1
        while d >= k0 and env[d] <= T and k - 1 - d < DIP_ON: d -= 1
        if d < k0 or d == k - 1 or env[d] <= T or on - d > LEAD_MAX: break
        r = d
        while r - 1 >= k0 and env[r - 1] > T and on - (r - 1) <= LEAD_MAX: r -= 1
        if d - r + 1 < 3 or env[r:d + 1].max() < A - SOFT_SYL: break
        k = r
    on = k
    k = off; e_lim = int((w["e"] + 0.10) / HOP); cap = None; hard = e_lim + int(0.5 / HOP)
    while k + 1 < n - 1:
        if env[k + 1] > T:
            if k + 1 > e_lim:
                # past the ASR's end: while he is still at speaking level (over A) the word is still going, so never stop
                # there (2026-10-28: "slowly" ran 0.15 s past Apple's end and the old 50 ms cap cut it off; the QC gate's
                # edge check caught it). Only the soft tail under A is capped at 50 ms.
                if env[k + 1] > A and k + 1 <= hard: cap = None; k += 1; continue
                # a soft ending joined straight onto the word with no dip (the long "s" of "gas") is the word too: up to
                # 0.25 s past the ASR's end; a breath comes after a dip, which stops the loop below
                cap = max(e_lim + int(0.25 / HOP), k + TAIL_MAX) if cap is None else cap
                if k + 1 > cap: break
            k += 1; continue
        if k + 1 > e_lim: break
        d = k + 1
        while d < n - 1 and env[d] <= T and d - k - 1 < DIP_MAX: d += 1
        if env[d] > T and d <= e_lim: k = d; continue   # a short dip inside the word: it goes on
        break
    off = k
    j = off + 1; lim = min(n - 2, int((w["e"] + 0.10) / HOP))
    while j <= min(lim, off + BURST_GAP) and env[j] <= T: j += 1   # a closure dip after the last sound ...
    if off + 1 < j <= min(lim, off + BURST_GAP):                    # ... then a short burst = the word's final consonant
        b = j
        while b + 1 <= lim and env[b + 1] > T: b += 1
        if b - j + 1 <= BURST_LEN: off = b
    return on * HOP, off * HOP + WIN


def cut_words(env, words, i0, i1, fps, lo=None, hi=None):
    """The line words[i0..i1] (dicts with "s"/"e", source seconds) with zero dead space and every word whole.
    Edges at the first word's onset and the last word's end (word_core); every dead run of 70 ms+ between words is cut like
    pieces_of() (30 ms kept before, 10 ms after); edges to the nearest frame."""
    s, e = words[i0]["s"], words[i1]["e"]
    P = line_ref(env, s, e); A, T = P - ACTIVE, P - TAIL
    cores = [word_core(env, words[i], A, T) for i in range(i0, i1 + 1)]
    # the line's edges are its first word's onset (20 ms before) and its last word's end: the ASR stretches the first word back
    # over whatever came before, so tighten() kept a stray 0.2 s sound before "Mindfulness" (heard as "3")
    st, en = cores[0][0] - 0.02, cores[-1][1]
    if lo is not None: st = max(st, lo)
    if hi is not None: en = min(en, hi)
    i_st = int(round(st / HOP)); i_en = max(i_st + 1, int(round(en / HOP)))
    dead = env[i_st:i_en] <= A
    for a, b in cores:   # a word's own sound (and 20 ms before it) is never dead
        dead[max(0, int(a / HOP) - 2 - i_st):max(0, int(np.ceil(b / HOP)) - i_st)] = False
    rnd = lambda t: round(t * fps) / fps
    out, cur, k, n = [], st, 0, len(dead)
    while k < n:
        if dead[k]:
            j = k
            while j < n and dead[j]: j += 1
            if k > 0 and j < n and (j - k) * HOP >= MIN_GAP:
                a = (i_st + k) * HOP + KEEP_PRE; b = (i_st + j) * HOP - KEEP_POST
                if b - a > 0.03 and a > cur: out.append((cur, a)); cur = b
            k = j
        else: k += 1
    out.append((cur, en)); m = []
    for a, b in [(rnd(a), rnd(b)) for a, b in out]:
        if m and a <= m[-1][1]: m[-1] = (m[-1][0], max(b, m[-1][1]))
        elif b - a >= 2 / fps: m.append((a, b))
    return m


def _runs(q):
    runs, k = [], 0
    while k < len(q):
        if q[k]:
            j = k
            while j < len(q) and q[j]: j += 1
            if (j - k) * HOP >= DEAD_RUN - 1e-9: runs.append((j - k) * HOP)
            k = j
        else: k += 1
    return runs


def dead_space(src):
    """The yardstick on a finished file (or a mono 16 kHz array): dead %, median and longest dead run (under p90 - 20 dB, the
    approved v4 measure), plus silent % and longest silence (under p90 - 32 dB: the sound is gone). A soft-spoken word sits
    between the two, so on his everyday takes dead % can't reach the UGC ads' 3-4% without cutting words; silence can."""
    d = level_env(src)[30:-30]
    if len(d) < 10: return dict(dead_pct=0.0, median_run=0.0, longest=0.0, runs=0, silent_pct=0.0, longest_silence=0.0)
    p = np.percentile(d, 90); runs = _runs(d < p - ACTIVE); sil = _runs(d < p - TAIL)
    return dict(dead_pct=round(sum(runs) / (len(d) * HOP) * 100, 1), median_run=round(float(np.median(runs)), 3) if runs else 0.0,
                longest=round(max(runs), 2) if runs else 0.0, runs=len(runs),
                silent_pct=round(sum(sil) / (len(d) * HOP) * 100, 1), longest_silence=round(max(sil), 2) if sil else 0.0)


def lookoff(video, pieces, th=0.45, shut=0.13, yaw_off=0.45):
    """Eyes at both edges of each piece: 3 frames per edge (the first or last 0.2 s), flagged when 2 or more show him looking
    down (pupil_y >= th), eyes shut (open < shut), turned away (|yaw| > yaw_off rad) or no face. One frame is only a blink.
    (GUT 10/10 test: the 149.7-150.0 s edges were him reading off his notes, head down; two single-frame flags were blinks.)"""
    rows = []
    with tempfile.TemporaryDirectory() as td:
        jobs = []
        for k, (a, b) in enumerate(pieces):
            for side, ts in (("start", (a + 0.02, a + 0.10, a + 0.20)), ("end", (b - 0.04, b - 0.12, b - 0.20))):
                for q, t in enumerate(ts):
                    t = min(max(t, a), b); p = os.path.join(td, f"{k:04d}_{side}_{q}.jpg")
                    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=-2:1080",
                                    "-q:v", "3", "-y", p], capture_output=True)
                    jobs.append((k, side, t, p))
        got = {}
        for line in subprocess.run([GAZE] + [p for *_, p in jobs], capture_output=True, text=True).stdout.splitlines():
            parts = line.split()
            if parts: got[parts[0]] = parts[1:]
        edges = {}
        for k, side, t, p in jobs:
            v = got.get(p, ["-"])
            if v == ["-"] or len(v) < 5: why = "no face"; py = yaw = None
            else:
                pitch, yaw, py, px, op = (float(x) for x in v[:5])
                why = "down" if py >= th else ("shut" if op < shut else ("turned" if abs(yaw) > yaw_off else ""))
            edges.setdefault((k, side), []).append((t, py, yaw, why))
        for (k, side), fr in edges.items():
            bad = [f for f in fr if f[3]]
            rows.append((k, side, fr[0][0], bad[0][1] if bad else fr[0][1], bad[0][2] if bad else fr[0][2], bad[0][3] if len(bad) >= 2 else ""))
    return rows


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("measure", "line", "lookoff"): print(__doc__); sys.exit(2)
    if a[0] == "measure":
        bad = 0
        print(f"{'file':52s} {'dead %':>7s} {'median':>7s} {'longest':>8s}  verdict (target <= {DEAD_PCT_MAX:g}% and <= {DEAD_MED_MAX:g} s)")
        for p in a[1:]:
            m = dead_space(p); ok = m["dead_pct"] <= DEAD_PCT_MAX and m["median_run"] <= DEAD_MED_MAX; bad += not ok
            print(f"{os.path.basename(p)[:52]:52s} {m['dead_pct']:7.1f} {m['median_run']:7.3f} {m['longest']:8.2f}  {'OK' if ok else 'TOO MUCH AIR'}")
        sys.exit(1 if bad else 0)
    if a[0] == "line":
        opt = {k: float(a[a.index(k) + 1]) for k in ("--fps", "--lo", "--hi") if k in a}
        env = level_env(a[1]); fps = opt.get("--fps", 30000 / 1001)
        print(json.dumps(cut_line(env, float(a[2]), float(a[3]), fps, opt.get("--lo"), opt.get("--hi"))))
        return
    rows = lookoff(a[1], json.load(open(a[2]))); bad = [r for r in rows if r[5]]
    for k, side, t, py, yaw, flag in rows:
        if flag: print(f"piece {k:3d} {side:5s} {t:8.2f}s  {flag:7s} pupil_y {py if py is None else round(py, 2)}  yaw {yaw if yaw is None else round(yaw, 2)}")
    print(f"{len(bad)} of {len(rows)} edges flagged")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
