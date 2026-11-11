#!/usr/bin/env python3
"""Bad takes out, last clean take in (OB 2026-10-28: "find the bad takes and get rid of them and deadspace so it flows really well
and its fast pace"; 10-25: "you don't take out bad takes"; 10-27: keep only the LAST take of each line). Short form.

He reads each script line, and when a try goes wrong he says "cut that, Claude" (the transcript hears "cut that cloud", "got that,
Claude", "cut that clock") and goes again. So for every script line this finds every try in the raw transcript and drops:
  cue      a try that "cut that ..." follows (before he starts anything else), or one with the cue inside it
  partial  a try that stops short (under 80% of the line's words: "10 out of 10 hot.")
  restart  a try that starts over inside itself (the line's opening words twice)
and keeps the LAST clean try. A line with no clean try keeps its most complete last try and is marked REVIEW.

  python3 -I takes.py WORDS.json SCRIPT [--audio MIC.wav --fps 29.97 --edl OUT.json [--voice OUT.wav [--master] [--verify]]]

WORDS.json: [{"w": word, "s": start, "e": end}, ...] in source seconds (Apple `speech_words` / the 10/10 `*_words.json`;
whisper `-ojf` word lists convert to that). SCRIPT: a text file, one script line per line (or a JSON list of strings, or of
[id, text]). With --audio, every kept take is cut by zero_dead.cut_words (zero dead space, every word whole) into an EDL
{"lines": [{"id", "text", "take": [s, e], "pieces": [[a, b], ...]}]}; --voice writes the cut voice (48 kHz from the mic, 5 ms
fades at the joins; --master runs voice_master.py on it with every line levelled); --verify then runs whisper medium on it and
diffs it against the script (0 missing or clipped words), with the dead-space yardstick.
Validated 2026-10-28 on the 10/10 GUT raw take (C4376: 16 retake cues, 46 script lines incl. the 5 hooks): it picked the same take
as the hand-picked delivered edit for 46 of 46 lines.
"""
import difflib, json, os, re, subprocess, sys

NUM = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
       "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20", "thirty": "30"}
CUT = {"cut", "got", "cuts", "cup", "gut", "caught", "cot"}
CLAUDE = {"claude", "cloud", "clod", "clyde", "clawed", "clock", "claud", "clot", "clouds", "cloth"}
COMPLETE, MIN_TRY = 0.75, 0.34   # share of the line's letters a try must say to be complete ("Yogurt confure kimchi" = 0.79)


def toks(text):
    t = text.lower().replace("’", "'").replace("-", " ").replace("/", " ").replace("%", " percent")
    return [NUM.get(x, x) for x in re.sub(r"[^a-z0-9' ]", " ", t).split() if x.strip("'")]


def load_script(path):
    raw = open(path).read()
    try: data = json.loads(raw)
    except ValueError: data = [l.strip() for l in raw.splitlines() if l.strip()]
    return [(str(d[0]), d[1]) if isinstance(d, (list, tuple)) else (f"L{k + 1:02d}", d) for k, d in enumerate(data)]


def flatten(words):
    """One token per word piece, each pointing back at its word index."""
    tk, wi = [], []
    for i, w in enumerate(words):
        for t in toks(w["w"]): tk.append(t); wi.append(i)
    return tk, wi


def cues(tk):
    """Token indices where a "cut that (Claude)" starts, and where it ends."""
    out = []
    for i in range(len(tk) - 1):
        if tk[i] in CUT and tk[i + 1] == "that":
            j = i + 2 + (1 if i + 2 < len(tk) and tk[i + 2] in CLAUDE else 0)
            out.append((i, j))
        elif tk[i] in CLAUDE and i > 0 and tk[i - 1] == "that" and not any(a <= i < b for a, b in out):
            out.append((i - 1, i + 1))
    return out


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def tries(tk, line, cue_at=(), t0=None, t1=None):
    """Every try of the script line: (first token, last token, how much of the line it says). Matched on letters, not exact
    words, because the transcript misspells and merges ("Seven, 30" -> "730", "That's where" -> "Those were", "comment" ->
    "Come at"). A try starts on a token like the line's first or second word, and stops before a retake cue or before the line's
    opening comes round again (the next try)."""
    m = len(line); ls = " ".join(line); found = []
    for i in range(len(tk)):
        if not (sim(tk[i], line[0]) >= 0.6 or (m > 1 and sim(tk[i], line[1]) >= 0.6)): continue
        stop = min([c for c in cue_at if c > i] + [i + m + 6, len(tk)])
        for k in range(i + 2, stop - 1):   # the opening again = a new try
            if sim(tk[k], line[0]) >= 0.75 and m > 1 and sim(tk[k + 1], line[1]) >= 0.75: stop = k; break
        bi = i
        if m > 1 and sim(tk[i], line[0]) < 0.6 and i > 0 and t0 is not None and t0[i] - t1[i - 1] < 0.3 and sim(tk[i - 1], line[0]) >= 0.4 \
                and not any(c <= i - 1 < c + 3 for c in cue_at):
            bi = i - 1   # matched on the second word: the first was misheard ("That's where" heard as "Those were")
        # start on the line's real first word: drop a leading token that ends a sentence before a pause ("gut." ~ "but")
        while bi + 1 < stop and t0 is not None and t0[bi + 1] - t1[bi] >= 0.3 and sim(tk[bi + 1], line[0]) >= sim(tk[bi], line[0]): bi += 1
        best, bj = 0.0, bi
        for j in range(bi, stop):
            r = sim(ls, " ".join(tk[bi:j + 1]))
            if r > best + 1e-9: best, bj = r, j
        # the line's last words unmatched (misheard: "pound you weigh" heard as "brownie way"): the try runs on over as many
        # following words as are missing, while he keeps talking (gaps under 0.3 s) and before a cue or the next try
        bl = [x for x in difflib.SequenceMatcher(None, line, tk[bi:bj + 1], autojunk=False).get_matching_blocks() if x.size]
        if bl and t0 is not None:
            u = m - (bl[-1].a + bl[-1].size); j = last = bi + bl[-1].b + bl[-1].size - 1
            while u > 0 and j + 1 < stop and j + 1 - last <= u and t0[j + 1] - t1[j] < 0.3: j += 1
            bj = max(bj, j)
        cov = sum(bl.size for bl in difflib.SequenceMatcher(None, ls, " ".join(tk[bi:bj + 1]), autojunk=False).get_matching_blocks()) / len(ls)
        if cov >= MIN_TRY: found.append([bi, bj, cov])
    found.sort(key=lambda x: (x[0], -x[2])); keep = []
    for f in found:   # tries that overlap are one try: keep the fuller reading
        if keep and f[0] <= keep[-1][1]:
            if f[2] > keep[-1][2]: keep[-1] = f
        else: keep.append(f)
    return keep


def pick(words, script):
    tk, wi = flatten(words); cs = cues(tk); lines = [(lid, txt, toks(txt)) for lid, txt in script]
    t0 = [words[k]["s"] for k in wi]; t1 = [words[k]["e"] for k in wi]
    every = {lid: tries(tk, lt, [c0 for c0, c1 in cs], t0, t1) for lid, txt, lt in lines if len(lt) >= 1}
    # a stretch of the take is a try of ONE line: the line it reads most like ("10 out of 10 habits to improve your gut health"
    # is not a try of "... to increase your gut health"; "for your gut health" is not "DEI for your gut")
    text = {lid: " ".join(lt) for lid, txt, lt in lines}
    score = {(lid, a): sim(text[lid], " ".join(tk[a:b + 1])) for lid, v in every.items() for a, b, c in v}
    for lid in list(every):
        mine = []
        for a, b, c in every[lid]:
            beaten = any(o != lid and min(b, ob) - max(a, oa) + 1 > 0.5 * (b - a + 1) and score[(o, oa)] > score[(lid, a)] + 0.02
                         for o, v in every.items() for oa, ob, oc in v)
            if not beaten: mine.append([a, b, c])
        every[lid] = mine
    starts = sorted(a for v in every.values() for a, b, c in v)
    out = []
    for lid, txt, lt in lines:
        rows = []
        for a, b, cov in every.get(lid, []):
            nxt = next((s for s in starts if s > b), len(tk))
            flags = []
            if cov < COMPLETE: flags.append("partial")
            # a cue belongs to what he said right before it: this try only if at most one word comes between them
            # ("...even after dinner. 10 times, cut that clock." cuts the "10 times" flub, not the good take before it)
            if any(a <= c0 <= b for c0, c1 in cs) or any(b < c0 < nxt and c0 - b - 1 <= 1 and words[wi[c0]]["s"] - words[wi[b]]["e"] < 6 for c0, c1 in cs):
                flags.append("cue")
            head = lt[:3]
            if len(lt) >= 4 and any(tk[k:k + 3] == head for k in range(a + 2, b - 1)) and tk[a:b + 1].count(head[0]) > lt.count(head[0]):
                flags.append("restart")
            rows.append(dict(s=round(words[wi[a]]["s"], 2), e=round(words[wi[b]]["e"], 2), i0=wi[a], i1=wi[b], cov=round(cov, 2),
                             flags=flags, said=" ".join(w["w"] for w in words[wi[a]:wi[b] + 1])))
        clean = [r for r in rows if not r["flags"]]
        if clean: ch, status = clean[-1], "ok"
        elif rows:
            best = max(r["cov"] for r in rows); ch = [r for r in rows if r["cov"] == best][-1]; status = "REVIEW"
        else: ch, status = None, "MISSING"
        out.append(dict(id=lid, text=txt, status=status, take=ch, tries=rows))
    # lines are read in order: a line's take that starts after the next line's take is the wrong stretch when the line has a
    # clean try before the next line (2026-10-28, C4364: "It's no calories." took "...is crazy. 130 calories," 45 s later,
    # the last fuzzy match, and the real try at 101.6 s was dropped as an earlier take)
    for i in range(len(out) - 2, -1, -1):
        r, nx = out[i], out[i + 1]
        if r["status"] == "ok" and nx["take"] and r["take"]["s"] > nx["take"]["s"]:
            before = [t for t in r["tries"] if not t["flags"] and t["e"] <= nx["take"]["s"] + 0.05]
            if before: r["take"] = before[-1]
    return out, [(round(words[wi[a]]["s"], 2), " ".join(tk[a:b])) for a, b in cs]


def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(2)
    words = json.load(open(a[0])); script = load_script(a[1])
    opt = {k: a[a.index(k) + 1] for k in ("--audio", "--fps", "--edl", "--voice") if k in a}
    res, cue_list = pick(words, script)
    print(f"{len(cue_list)} retake cues heard; {sum(len(r['tries']) for r in res)} tries of {len(res)} lines")
    for r in res:
        t = r["take"]
        print(f"{r['id']:>6s} {r['status']:7s} keep {t['s'] if t else '-':>8} \"{r['text'][:60]}\"")
        for x in r["tries"]:
            if x is not t: print(f"{'':16s}drop {x['s']:8.2f} [{','.join(x['flags']) or 'earlier take'}] \"{x['said'][:70]}\"")
    bad = [r for r in res if r["status"] != "ok"]
    if "--audio" not in opt:
        sys.exit(1 if bad else 0)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import numpy as np
    import zero_dead as Z
    fps = float(opt.get("--fps", 30000 / 1001)); env = Z.level_env(opt["--audio"]); edl = []

    def boundary(w0, w1, A, T):
        """How far a line may reach toward its neighbour word. With a real pause between them (MIN_GAP+ under T): no bound,
        the word's own sound decides. Said in one breath: the quietest 10 ms between the two words, so lines meet there with
        nothing repeated or clipped. Never the ASR's word end: it stretches over pauses and over the next word's onset
        (2026-10-28, C4361: a phantom "So" ran to 72.30 and the old end+30 ms bound clipped the "H" of "How" at 72.27).
        The pause is looked for up to the next word's real onset: on C4362 Apple ended "sustainable," at 58.68 and began
        "Because" there too, while the "-ble" ran to 58.82 and the pause after it to 59.9; looking only 0.1 s past the ASR
        times found no pause, took the dip inside the word (58.62) and cut the "-ble"."""
        on1 = Z.word_core(env, w1, A, T)[0]
        i_a = int(max(0.0, w0["e"] - 0.10) / Z.HOP); i_b = max(i_a + 1, int((max(w1["s"] + 0.10, on1 + 0.02)) / Z.HOP)); run = best = 0
        for v in env[i_a:i_b] <= T: run = run + 1 if v else 0; best = max(best, run)
        return None if best * Z.HOP >= Z.MIN_GAP else (i_a + int(np.argmin(env[i_a:i_b]))) * Z.HOP
    prev_e = None
    for r in res:
        t = r["take"]
        if not t: continue
        i0, i1 = t["i0"], t["i1"]
        # a take that starts inside the line before it (and runs on past it) starts after it: on C4362 "And that's why ..."
        # was matched from L07's last word "habits.", and "The body will come ..." from L09's "...has the body," 3 s earlier
        if prev_e is not None and words[i0]["s"] < prev_e - 0.02 < words[i1]["e"]:
            while i0 < i1 and words[i0]["s"] < prev_e - 0.02: i0 += 1
            t["i0"], t["s"] = i0, words[i0]["s"]
        prev_e = max(prev_e or 0.0, words[i1]["e"])
        P = Z.line_ref(env, words[i0]["s"], words[i1]["e"]); A, T = P - Z.ACTIVE, P - Z.TAIL
        lo = boundary(words[i0 - 1], words[i0], A, T) if i0 > 0 else None
        hi = boundary(words[i1], words[i1 + 1], A, T) if i1 + 1 < len(words) else None
        edl.append(dict(id=r["id"], text=r["text"], status=r["status"], take=[t["s"], t["e"]],
                        pieces=[[round(x, 4), round(y, 4)] for x, y in Z.cut_words(env, words, i0, i1, fps, lo, hi)]))
    if "--edl" in opt: json.dump({"fps": fps, "audio": opt["--audio"], "lines": edl}, open(opt["--edl"], "w"), indent=1)
    if "--voice" in opt:   # the cut voice at the mic's own 48 kHz (never the 16 kHz analysis copy), 5 ms fades at every join
        sr = 48000
        x = np.frombuffer(subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", opt["--audio"], "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                                         capture_output=True).stdout, np.float32).astype(np.float64)
        f5 = int(0.005 * sr); segs, spans, cur = [], [], 0
        for l in edl:
            n0 = cur
            for p, q in l["pieces"]:
                g = x[int(round(p * sr)):int(round(q * sr))].copy()
                if len(g) > 2 * f5: g[:f5] *= np.linspace(0, 1, f5); g[-f5:] *= np.linspace(1, 0, f5)
                segs.append(g); cur += len(g)
            spans.append((n0, cur))
        y = np.concatenate(segs)
        import voice_master as VM
        from scipy.io import wavfile
        import tempfile
        if "--master" in a:
            y, rep = VM.master(y, sr, -14.0, spans); print("master:", json.dumps(rep))
        with tempfile.TemporaryDirectory() as td:
            t = os.path.join(td, "v.wav"); wavfile.write(t, sr, np.asarray(y, np.float32))
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", t, "-c:a", "pcm_s24le", opt["--voice"]], check=True)
        d = Z.dead_space(opt["--voice"])
        print(f"voice {len(y) / sr:.1f} s: dead {d['dead_pct']}% (median {d['median_run']} s), silent {d['silent_pct']}% (longest {d['longest_silence']} s)")
        if "--verify" in a:
            with tempfile.TemporaryDirectory() as td:
                w16 = os.path.join(td, "v16.wav")
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", opt["--voice"], "-ac", "1", "-ar", "16000", w16], check=True)
                o = subprocess.run(["whisper-cli", "-m", os.path.expanduser("~/.whisper-models/ggml-medium.en.bin"), "-f", w16, "-np", "-nt"],
                                   capture_output=True, text=True).stdout
            exp = [t for l in edl for t in toks(l["text"])]; got = toks(o)
            sm = difflib.SequenceMatcher(None, exp, got, autojunk=False); n = 0
            for op, i1_, i2_, j1, j2 in sm.get_opcodes():
                if op != "equal": n += 1; print(f"   WORDS {op:7s} [{' '.join(exp[i1_:i2_])}] -> [{' '.join(got[j1:j2])}]")
            print(f"   {n} word differences (match {sm.ratio():.3f}); cue words heard: {re.findall(r'(?i)cut that|claude', o)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
