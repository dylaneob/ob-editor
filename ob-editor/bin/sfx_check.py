#!/usr/bin/env python3
"""sfx_check: the sound-effects check (2026-11-07), from the 6-step chain in Mark Pyvovarov's 11-05 reel (@markpyvo, "LINK all 3
tools": Openverse -> earshot -> Real SFX). OB's editor has had the three tools since 11-01 (@hugomxnning's reel). This adds,
as code, the two steps of that chain the editor only did by eye (ledger M17 was "manual"):

  step 3, LISTEN AND PICK: every candidate file screened before it goes in a plan: clipped, noisy, a long silent tail, a late
          start (assemble.py puts the file's FIRST sample on the cue, so silence at the head lands the sound late), over 2 s
  step 5, CHECK YOUR WORK: the plan against OB's caps (M17), and the finished file: each sound found on its cue (no sound on the
          wrong frame) and under his voice (never louder than him, never buried)

  python3 -I sfx_check.py files FILE...                    screen candidates before one goes in a plan
  python3 -I sfx_check.py plan PLAN.json --dur S [--long]   the plan alone: rate, first 0.5 s, gaps, variety, level
  python3 -I sfx_check.py mix VIDEO PLAN.json [--long]      plan + its files + where each sound really sits in VIDEO
  python3 -I sfx_check.py --selftest
qc_gate.py runs `mix` as its `sfx` check when it gets --sfx-plan, --work with story/sfx_plan.json, or a render made with
OB_SFX_PLAN set.

Plan format (assemble.py OB_SFX_PLAN): {"hits": [{"t": edit seconds of the file's first sample, "file": path, "db": the sound's
loudest 100 ms vs his speech level, "why": optional, "list": optional true for a list's ticks}]}

OB's caps (M17; 10-16, 10-29: "use them when needed dont be obxious about them"): reels about 3-4 a minute at most, long-form
up to C4367's 2.9 a minute; none in the first 0.5 s; never two within 1.5 s (a list's ticks excepted, 0.25 s apart at least);
quiet (plans sit at -17 to -27) and varied (C4352: "have different sound effects"). The reel's own rules are looser
(two moments under 0.5 s apart: keep one) and are covered by these.
"""
import json, math, os, re, subprocess, sys
import numpy as np

SR = 16000
FRAME = 1 / 29.97
REEL_CAP, REEL_FAIL = 4.0, 5.0          # a minute (fallbacks only: the numbers live in qc/formats.json since the 2026-11-10 rebuild)
LONG_CAP, LONG_FAIL = 2.9, 4.0
MIN_GAP, LIST_GAP, HEAD = 1.5, 0.25, 0.5
REPEAT_REEL, REPEAT_LONG = 2, 3
try:   # rebuild 2026-11-10: caps and repeat rules read from formats.json (one place for numbers)
    _F = json.load(open(os.path.expanduser("~/ob-editor/qc/formats.json")))
    _S = _F["defaults"]["sfx"]; MIN_GAP, LIST_GAP, HEAD = _S["min_gap_s"], _S["list_tick_gap_s"], _S["first_s_none"]
    REPEAT_REEL, REPEAT_LONG = _S["repeat_max_reel"], _S["repeat_max_long"]
    REEL_CAP, REEL_FAIL = (lambda c: (c["cap"], c["fail"]))(_F["routes"]["reel-talking"]["sfx_per_min"])
    LONG_CAP, LONG_FAIL = (lambda c: (c["cap"], c["fail"]))(_F["routes"]["long-form"]["sfx_per_min"])
except Exception:
    pass


def route_caps(route):
    """(cap, fail) a minute for a formats.json route (level-kit reels run 18/23), or None when unknown."""
    try:
        c = json.load(open(os.path.expanduser("~/ob-editor/qc/formats.json")))["routes"][route]["sfx_per_min"]
        return c["cap"], c["fail"]
    except Exception:
        return None
LOUD_WARN, LOUD_FAIL = -12.0, -6.0      # the sound's loudest 100 ms vs his speech level (assemble.py's "db")
TICKISH = re.compile(r"tick|click|bleep|beep|blip", re.I)
LONGOK = re.compile(r"riser|rise|boom|drop|swell|sub|charge|whoosh_long|impact", re.I)


def decode(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def env_db(x, sr=SR, win=0.01):
    fr = max(1, int(win * sr)); n = len(x) // fr
    if n < 1: return np.array([-120.0])
    return 10 * np.log10((x[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)


def peak100(x, sr=SR):
    """assemble.py's level for a sound: its loudest 100 ms (RMS dB)."""
    fr = int(0.1 * sr); k = max(1, len(x) // fr)
    if len(x) < fr: return 10 * np.log10((x ** 2).mean() + 1e-12)
    return 10 * np.log10(((x[: k * fr].reshape(k, fr) ** 2).mean(1)).max() + 1e-12)


def speech_db(v, sr=SR):
    """score._speech_db: the 70th percentile of 100 ms RMS over the frames within 30 dB of the loudest."""
    fr = int(0.1 * sr); n = len(v) // fr
    if n < 3: return -24.0
    r = 10 * np.log10((v[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)
    return float(np.percentile(r[r > r.max() - 30], 70))


def onset_of(x, sr=SR):
    """Seconds of near-silence before the sound starts (10 ms envelope 30 dB under its peak)."""
    e = env_db(x, sr); i = int(np.argmax(e > e.max() - 30))
    return i * 0.01


# ---------- step 3: screen a candidate file ----------
def screen_file(path):
    """Returns (status, list of notes, facts). WARN only: a sound with a flag can still go in once it's trimmed or checked by ear."""
    x48 = decode(path, 48000); notes = []
    if len(x48) == 0: return "FAIL", ["no audio"], {}
    dur = len(x48) / 48000; pk = float(np.abs(x48).max())
    e = env_db(x48, 48000); top = e.max()
    lead = float(np.argmax(e > top - 30)) * 0.01
    last = len(e) - 1 - int(np.argmax(e[::-1] > top - 40)); tail = max(0.0, dur - (last + 1) * 0.01)
    quiet = np.concatenate([e[: max(0, int(lead / 0.01) - 1)], e[last + 2:]])
    noise = float(np.median(quiet)) if len(quiet) >= 5 else None
    flat = 0
    if pk >= 0.999:
        hot = np.abs(x48) >= 0.999 * pk; flat = int(np.sum(hot[1:] & hot[:-1]))
    facts = {"dur": round(dur, 2), "peak_dbfs": round(20 * math.log10(pk + 1e-12), 1), "lead_ms": round(lead * 1000), "tail_s": round(tail, 2),
             "noise_db": None if noise is None else round(noise, 1)}
    if flat >= 2: notes.append(f"clipped ({flat} flat-topped samples)")
    if lead > FRAME + 0.002: notes.append(f"starts {lead * 1000:.0f} ms in: placed by its first sample it lands late, trim the head")
    if tail > 0.3: notes.append(f"{tail:.1f} s silent tail")
    if noise is not None and noise > -55: notes.append(f"hiss: floor {noise:.0f} dBFS in its quiet parts")
    if dur > 2.0 and not LONGOK.search(os.path.basename(path)): notes.append(f"{dur:.1f} s long (under 2 s unless the moment needs a riser or a boom)")
    return ("WARN" if notes else "PASS"), notes, facts


# ---------- step 5a: the plan against OB's caps ----------
def _recording_id(path):
    """recording id from the bank index (by hash); falls back to the real path when the file is not indexed."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bank_index as BI
        k, sha, e = BI.lookup_path(path)
        return e["recording_id"] if e else "file:" + os.path.realpath(path)
    except BaseException:
        return "file:" + os.path.realpath(path)


def plan_issues(hits, dur, long=False, route=None):
    """hits: [{"t", "file", "db", ...}] in edit seconds. Returns (fails, warns, facts)."""
    hs = sorted([h for h in hits if -0.05 <= float(h["t"]) < dur], key=lambda h: float(h["t"]))
    F, W = [], []
    n = len(hs); mins = max(dur, 1.0) / 60
    cap, hard = (route_caps(route) if route else None) or ((LONG_CAP, LONG_FAIL) if long else (REEL_CAP, REEL_FAIL))
    allow, allow_hard = math.ceil(cap * mins - 1e-9), math.ceil(hard * mins - 1e-9)
    rate = n / mins
    if n > allow_hard: F.append(f"{n} sounds in {dur:.0f} s ({rate:.1f} a minute; the cap is about {cap:g})")
    elif n > allow: W.append(f"{n} sounds in {dur:.0f} s ({rate:.1f} a minute; the cap is about {cap:g})")
    for h in hs:
        if float(h["t"]) < HEAD: F.append(f"a sound at {float(h['t']):.2f} s (none in the first {HEAD} s)")
    for a, b in zip(hs, hs[1:]):
        gap = float(b["t"]) - float(a["t"]); ticks = (a.get("list") and b.get("list")) or (TICKISH.search(os.path.basename(a["file"])) and TICKISH.search(os.path.basename(b["file"])))
        if ticks and gap >= LIST_GAP: continue
        if gap < MIN_GAP: F.append(f"two sounds {gap:.2f} s apart at {float(a['t']):.2f} s (never within {MIN_GAP} s{'; list ticks 0.25 s' if ticks else ''})")
    same = [float(b["t"]) for a, b in zip(hs, hs[1:]) if os.path.realpath(a["file"]) == os.path.realpath(b["file"])]
    if same: W.append(f"the same file twice in a row at {', '.join(f'{t:.1f}' for t in same[:4])} s (vary them)")
    recs = [h.get("recording_id") or _recording_id(h["file"]) for h in hs]   # rebuild: repeats are counted by RECORDING, so pitch variants of one sound count together
    for i in range(1, len(recs)):
        if recs[i] == recs[i - 1] and not same: F.append(f"the same recording twice in a row at {float(hs[i - 1]['t']):.1f} and {float(hs[i]['t']):.1f} s (pitch variants of one sound are the same sound)")
    mx = REPEAT_LONG if long else REPEAT_REEL
    for r in sorted({r for r in recs if recs.count(r) > mx}): F.append(f"one recording used {recs.count(r)} times (max {mx} per {'video' if long else 'reel'}): {r}")
    for h in hs:
        db = float(h.get("db", -14.0))
        if db > LOUD_FAIL: F.append(f"{os.path.basename(h['file'])} at {float(h['t']):.2f} s planned at {db:+.0f} dB vs his voice (keep it under him)")
        elif db > LOUD_WARN: W.append(f"{os.path.basename(h['file'])} at {float(h['t']):.2f} s planned at {db:+.0f} dB vs his voice (plans sit at -17 to -27)")
    missing = sorted({h["file"] for h in hs if not os.path.exists(h["file"])})
    if missing: F.append(f"{len(missing)} planned file(s) missing: {', '.join(os.path.basename(m) for m in missing[:3])}")
    return F, W, {"n": n, "per_min": round(rate, 2), "dur": round(dur, 1)}


# ---------- step 5b: where each sound really sits in the finished file ----------
def locate(mix, tmpl, expect, sr=SR, search=0.30):
    """Normalized cross-correlation of the sound's first 0.25 s against the mix around where it should start.
    Returns (offset s, ncc, gain)."""
    L = len(tmpl); i0 = int(round((expect - search) * sr)); i1 = int(round((expect + search) * sr)) + L
    lo = max(0, i0); seg = mix[lo:max(lo, min(len(mix), i1))]
    if len(seg) < L + 1 or not np.any(tmpl): return None, 0.0, 0.0
    t = tmpl - tmpl.mean(); tn = np.sqrt((t ** 2).sum()) + 1e-12
    nfft = 1 << int(np.ceil(np.log2(len(seg) + L)))
    corr = np.fft.irfft(np.fft.rfft(seg, nfft) * np.conj(np.fft.rfft(t, nfft)), nfft)[: len(seg) - L + 1]
    c1 = np.concatenate([[0.0], np.cumsum(seg)]); c2 = np.concatenate([[0.0], np.cumsum(seg ** 2)])
    s1 = c1[L:] - c1[:-L]; s2 = c2[L:] - c2[:-L]; var = np.maximum(s2 - s1 ** 2 / L, 1e-12)
    ncc = corr / (tn * np.sqrt(var)); k = int(np.argmax(ncc))
    win = seg[k:k + L]; g = float((win * tmpl).sum() / ((tmpl ** 2).sum() + 1e-12))
    return (lo + k) / sr - expect, float(ncc[k]), g


def mix_check(video, hits, dur=None, mix=None):
    """Each planned sound found in VIDEO's audio: its start within one frame of the cue, its level under his voice."""
    mix = decode(video) if mix is None else mix
    dur = dur or len(mix) / SR; sp = speech_db(mix)
    F, W, rows, cache = [], [], [], {}
    for h in sorted(hits, key=lambda h: float(h["t"])):
        t = float(h["t"]); f = h["file"]
        if not (0 <= t < dur) or not os.path.exists(f): continue
        if f not in cache:
            x = decode(f); lead = onset_of(x); cache[f] = (x, lead, peak100(x))
        x, lead, pk = cache[f]
        i = int(lead * SR); tmpl = x[i:i + int(0.25 * SR)]
        off, ncc, g = locate(mix, tmpl, t + lead)
        if off is None: continue
        if ncc < 0.3:   # not on its cue: look 2 s either side; a clear match there means it was placed on the wrong frame
            o2, n2, g2 = locate(mix, tmpl, t + lead, search=2.0)
            if o2 is not None and n2 >= 0.7: off, ncc, g = o2, n2, g2
        lvl = 20 * math.log10(abs(g) + 1e-9) + pk - sp if g > 0 else -99.0
        row = {"t": round(t, 3), "file": os.path.basename(f), "lands_ms": round((t + lead) * 1000 - t * 1000), "offset_ms": round(off * 1000),
               "match": round(ncc, 2), "db_vs_voice": round(lvl, 1)}
        rows.append(row)
        where = f"{os.path.basename(f)} at {t:.2f} s"
        if ncc < 0.3: F.append(f"{where}: not heard clearly in the mix (match {ncc:.2f}: buried under him or the music, or missing; raise it or remove it)"); continue   # rebuild 2026-11-10: a buried sound is a FAIL
        if abs(off) > FRAME + 0.004: F.append(f"{where}: sits {off * 1000:+.0f} ms off its cue (the wrong frame)")
        if lead > FRAME + 0.002: W.append(f"{where}: the file starts {lead * 1000:.0f} ms in, so it lands {lead * 1000:.0f} ms after the cue (trim the head)")
        if lvl > LOUD_FAIL: F.append(f"{where}: {lvl:+.0f} dB vs his voice in the mix (louder than him)")
        elif lvl > LOUD_WARN: W.append(f"{where}: {lvl:+.0f} dB vs his voice in the mix")
    return F, W, rows


def check(video, plan_path, long=False, dur=None):
    """The gate's `sfx` check. Returns (status, detail, rows)."""
    hits = json.load(open(plan_path))["hits"]
    mix = decode(video); dur = dur or len(mix) / SR
    F, W, facts = plan_issues(hits, dur, long)
    used = sorted({h["file"] for h in hits if os.path.exists(h["file"]) and 0 <= float(h["t"]) < dur})
    for f in used:
        st, notes, _ = screen_file(f)
        for n_ in notes:
            if "starts" in n_: continue   # reported per hit by mix_check, with where it lands
            W.append(f"{os.path.basename(f)}: {n_}")
    F2, W2, rows = mix_check(video, hits, dur, mix)
    F += F2; W += W2
    head = f"{facts['n']} sounds, {facts['per_min']} a minute"
    if F: return "FAIL", head + "; " + " | ".join(F[:4]) + (f" (+{len(F) - 4} more)" if len(F) > 4 else ""), rows
    if W: return "WARN", head + "; " + " | ".join(W[:4]) + (f" (+{len(W) - 4} more)" if len(W) > 4 else ""), rows
    return "PASS", head + ", each on its cue and under his voice", rows


def selftest():
    ok = True
    def t(good, what):
        nonlocal ok; ok &= bool(good); print(f"  {'ok ' if good else 'BAD'} sfx: {what}")
    kit = os.path.expanduser("~/ob-editor/assets/sfx")
    pop, wh, tk = f"{kit}/pop_1.wav", f"{kit}/whoosh_1.wav", f"{kit}/tick_1.wav"
    F, W, _ = plan_issues([{"t": 0.2, "file": pop, "db": -20}], 30)
    t(F and "first" in F[0], "a sound in the first 0.5 s FAILs")
    F, W, _ = plan_issues([{"t": 5.0, "file": pop, "db": -20}, {"t": 5.6, "file": wh, "db": -18}], 30)
    t(F and "apart" in F[0], "two sounds 0.6 s apart FAIL (the reel's own rule: keep the stronger one)")
    F, W, _ = plan_issues([{"t": 5.0, "file": tk, "db": -22}, {"t": 5.4, "file": f"{kit}/tick_2.wav", "db": -22}], 30)
    t(not F, "a list's ticks 0.4 s apart pass")
    F, W, _ = plan_issues([{"t": 3.0 + 3 * k, "file": [pop, wh][k % 2], "db": -20} for k in range(9)], 30)
    t(F and "a minute" in F[0], "9 sounds in a 30 s reel FAIL the 3-4 a minute cap")
    F, W, _ = plan_issues([{"t": 10.0 + 21 * k, "file": [pop, wh][k % 2], "db": -20} for k in range(20)], 600, long=True)
    t(not [f for f in F if "a minute" in f] and not W, "20 sounds in a 10-minute video pass the rate cap (2 a minute)")
    t(any("one recording used" in f for f in F), "...but two files cycled 10 times each FAIL the repeat cap (rebuild: by recording id)")
    F, W, _ = plan_issues([{"t": 3.0 + 9 * k, "file": pop, "db": -20, "recording_id": f"r{k % 2}"} for k in range(4)], 60, route="reel-graphics")
    t(not [f for f in F if "a minute" in f], "the level-kit route's 18 a minute cap is read from formats.json")
    F, W, _ = plan_issues([{"t": 5.0, "file": pop, "db": -3}], 30)
    t(F and "under him" in F[0], "a sound planned louder than his voice FAILs")
    F, W, _ = plan_issues([{"t": 5.0, "file": pop, "db": -20}, {"t": 8.0, "file": pop, "db": -20}], 30)
    t(not F and W and "twice in a row" in W[0], "the same pop twice in a row WARNs (vary them)")
    # the matched filter: a sound planted in speech-like noise is found on its frame, and an 80 ms slip FAILs
    rng = np.random.default_rng(7); x = decode(pop); lead = onset_of(x); tm = x[int(lead * SR):int(lead * SR) + int(0.25 * SR)]
    base = rng.normal(0, 0.05, SR * 10) * (1 + np.sin(np.arange(SR * 10) / 900.0))
    for slip, want in ((0.0, True), (0.08, False)):
        m = base.copy(); k = int((4.0 + slip) * SR); m[k:k + len(x)] += 0.5 * x[: len(m) - k] / (np.abs(x).max() + 1e-9)
        off, ncc, g = locate(m, tm, 4.0 + lead)
        t((abs(off) <= FRAME) == want and ncc > 0.3, f"a sound placed {slip * 1000:.0f} ms late is {'on its frame' if want else 'caught off its cue'} (found {off * 1000:+.0f} ms, match {ncc:.2f})")
    return ok


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit(2)
    if a[0] == "--selftest": sys.exit(0 if selftest() else 1)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    long = "--long" in a
    if a[0] == "files":
        for f in [x for x in a[1:] if not x.startswith("--")]:
            st, notes, facts = screen_file(f)
            print(f"{st:4s} {os.path.basename(f)}  {facts}  " + ("; ".join(notes) if notes else "clean"))
        return
    if a[0] == "plan":
        hits = json.load(open(a[1]))["hits"]; dur = float(opt("--dur") or 0) or max(float(h["t"]) for h in hits) + 5
        F, W, facts = plan_issues(hits, dur, long)
        print(f"{'FAIL' if F else ('WARN' if W else 'PASS')} {facts}")
        for x in F: print("  FAIL", x)
        for x in W: print("  WARN", x)
        sys.exit(1 if F else 0)
    if a[0] == "mix":
        st, detail, rows = check(a[1], a[2], long)
        for r in rows: print(f"  {r['t']:8.2f}s {r['file']:22s} lands +{r['lands_ms']} ms  found {r['offset_ms']:+d} ms  match {r['match']:.2f}  {r['db_vs_voice']:+.1f} dB vs voice")
        print(f"{st} {detail}")
        sys.exit(1 if st == "FAIL" else 0)
    print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
