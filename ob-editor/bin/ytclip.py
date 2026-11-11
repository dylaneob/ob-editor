#!/usr/bin/env python3
"""YouTube long-form -> Instagram reels, from the ORIGINAL source (OB 2026-10-26/28: "clip up my YouTube video to repurpose for
Instagram to promote my YT ... way better than ob moment skill ... make it an automatic flow"; "you edit those up though, just as
you would for short form and can get inspo on how you edited the long form so you dont need to build new assets").

The rule (rico.incarnati's "appetizer rule", the reference OB sent): every clip stands on its own (one whole takeaway) AND leaves
them hungry for the full video. The plan OB approved 10-28 (1A 2B 3A 4A 5A 6A): https://claude.ai/artifact/76vTgm79aGJZWV2XVdHyBg
Study, numbers and why: T7 OB-EDITS/2026-10-28-yt-clipper/STUDY.md. Preset: ~/ob-editor/presets/yt-clips/PRESET.md.

It edits from the long-form edit's own decisions, never from the YouTube export:
  camera     the 4K concat the long-form cut from (cutlist "source"), graded with the long-form's LUT
  voice      the long-form's 48 kHz MOTIV master (voice_polish'd), on the same timeline
  takes      only what the long-form kept (cutlist segments): its outtakes and "cut that, Claude" tries are already gone
  receipts   the long-form's events (events_resolved.json, source-timed): its B-roll, document pages, photos and sourced data,
             shown in Dylan Page's split while he talks (ytclip_look.py, 11-04: OB's rules since the 10-30 rejection of R1, "im not
             on the screen at all": he is on screen every frame he talks, no text-only cards, no black, one file per reel)
  words      Apple speech_words on the mic per reel (cut timing), checked word by word by whisper large-v3-turbo on the cut voice

WORK/clipper.json names the files; WORK/picks.json holds the reels (lines by first/last words near a source time, in the order
they play, the label, the names, the post caption). Stages, each re-runnable:
  python3 -I ytclip.py words WORK A B         Apple's words for source seconds A-B, the long-form's outtakes in [brackets]
  python3 -I ytclip.py cut WORK [R1 ...]      words -> zero-dead pieces -> mastered voice -> word diff + dead-space yardstick
  python3 -I ytclip.py mock WORK [R1 ...]     the plan (receipts, spans, moves) + the stills for OB's shot-by-shot OK
  python3 -I ytclip.py lookoff WORK [R1 ...]  his eyes at every cut edge; one in a full-frame line switches to the split (M37)
  python3 -I ytclip.py page WORK OUT.html     the shot-by-shot page (publish it; nothing renders before he OKs it)
  python3 -I ytclip.py render WORK [R1 ...] [--test] [--yield]   one file per reel, the picture in parallel chunks, voice muxed,
                                              the QC gate with every piece and the camera map (--yield: behind every other render)
  python3 -I ytclip.py qa WORK [R1 ...]       words, silence, loudness, motion score, no blast at 0 s, no text on his face: ship on PASS
  python3 -I ytclip.py deliver WORK [R1 ...]  one file per reel into the AirDrop folder (M45), POST-NOTES, manifest, _PREDICTIONS rows
  python3 -I ytclip.py review WORK            Mondays: posted clips vs their month and prediction, YouTube views from Instagram
"""
import difflib, json, os, re, subprocess, sys, tempfile
import numpy as np

BIN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BIN)
import zero_dead as Z      # noqa: E402  zero dead space cuts (OB 10-28 HARD RULE)
import voice_master as VM  # noqa: E402  the short-form voice chain (never a hard clip)
import takes as TK         # noqa: E402  toks(): the word diff's tokenizer

SPEECH = os.path.join(BIN, "speech_words")
WHISPER = os.path.expanduser("~/.whisper-models/ggml-large-v3-turbo.bin")   # the Mac mini default (11-03): Metal, ~3 s a reel
SR = 48000
KEEP_TOL = 0.06   # s: a word whose middle sits this close to a kept segment counts as kept (Apple's edges vs the cut list's)
MAX_S = 90.0      # s: a reel is always under 1:30 (OB 10-29, M33: "make the reel clip from youtube alwasy under 1:30 mins ... dont force it")


def cfg(work):
    work = os.path.abspath(work); c = json.load(open(os.path.join(work, "clipper.json"))); c["work"] = work
    c["lut"] = os.path.expanduser(c["lut"]); return c


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode: raise RuntimeError(" ".join(str(c) for c in cmd[:6]) + " ...\n" + p.stderr[-2000:])
    return p.stdout


def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())


# ---------------------------------------------------------------------------------------------------- the long-form's decisions
_KEPT = {}
def kept_segments(c):
    """The long-form's kept source spans [(src_in, src_out)], sorted (its outtakes and retakes are the gaps between them)."""
    if c["longform"] not in _KEPT:
        segs = json.load(open(os.path.join(c["longform"], "cutlist.json")))["segments"]
        _KEPT[c["longform"]] = sorted((s["src_in"], s["src_out"]) for s in segs if not s.get("hold"))
    return _KEPT[c["longform"]]


def is_kept(c, t):
    return any(a - KEEP_TOL <= t <= b + KEEP_TOL for a, b in kept_segments(c))


def kept_mask(c, words, i0, i1):
    """Per word: did the long-form keep it? Judged on the word's own sound on the mic (zero_dead.word_core), half of it inside a
    kept segment. Apple stretches a word's start back over the pause before it, so its midpoint can sit before the cut list's
    edge ("If", "Fat", "So" opening a kept line read as dropped on 10-28 when judged by the ASR span)."""
    env = env_of(c); P = Z.line_ref(env, words[i0]["s"], words[i1]["e"]); A, T = P - Z.ACTIVE, P - Z.TAIL
    out = []
    for i in range(i0, i1 + 1):
        on, off = Z.word_core(env, words[i], A, T); L = max(off - on, 0.01)
        inside = sum(max(0.0, min(off, b + KEEP_TOL) - max(on, a - KEEP_TOL)) for a, b in kept_segments(c))
        out.append(inside / L >= 0.5)
    return out


def inside_kept(c, p, q, fps, pad=0.12):
    """(p, q) clipped to the long-form's kept segments, each widened by `pad` for word tails (zero_dead keeps up to 50 ms past
    a word, the cut list's edges sit 0-60 ms inside them); pieces under 2 frames are dropped. An edge made here (a long-form
    cut inside the piece) is pulled in to the speech with zero_dead.tighten: the long-form keeps about 0.22 s of air at its own
    cuts, and on 10-28 that air came through as 0.1-0.2 s silences at those joins."""
    out, env = [], env_of(c)
    for a, b in kept_segments(c):
        x, y = max(p, a - pad), min(q, b + pad)
        if y - x < 2 / fps: continue
        if x > p or y < q:
            tx, ty = Z.tighten(env, x, y, lo=x, hi=y)
            x, y = (tx if x > p else x), (ty if y < q else y)
        x, y = round(x * fps) / fps, round(y * fps) / fps
        if y - x >= 2 / fps: out.append((x, y))
    return out


# ---------------------------------------------------------------------------------------------------- words
def words_at(c, a, b):
    """Apple's word times for the mic between source seconds a and b, cached (about 1 s per 20 s of audio)."""
    os.makedirs(os.path.join(c["work"], "cache"), exist_ok=True)
    p = os.path.join(c["work"], "cache", f"words_{a:.2f}_{b:.2f}.json")
    if not os.path.exists(p):
        with tempfile.TemporaryDirectory() as td:
            w = os.path.join(td, "m.wav")
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", c["mic16"], "-ac", "1", "-ar", "16000", w])
            ws = json.loads(run([SPEECH, "words", w]))
        json.dump([dict(w=x["w"], s=round(x["s"] + a, 3), e=round(x["e"] + a, 3)) for x in ws], open(p, "w"))
    return json.load(open(p))


def find_line(words, text, near):
    """(i0, i1, score): the words of `text` (what he said) in Apple's transcript, starting within 2.5 s of `near`. Aligned on
    tokens (takes.toks: numbers as digits) rather than exact first/last words, because Apple hears a line a little differently
    from one transcript window to the next ("Fat is 9 calories per grand" in one, "That is 9 calories per gram" in another)."""
    tt = TK.toks(text); wt, wi = [], []
    for k, x in enumerate(words):
        for t in TK.toks(x["w"]): wt.append(t); wi.append(k)
    best = None
    for j in range(len(wt)):
        k = wi[j]
        if (j and wi[j - 1] == k) or abs(words[k]["s"] - near) > 2.5: continue
        sm = difflib.SequenceMatcher(None, tt, wt[j:j + len(tt) + 8], autojunk=False)
        bl = [b for b in sm.get_matching_blocks() if b.size]
        if not bl: continue
        score = sum(b.size for b in bl) / len(tt) - 0.03 * abs(words[k]["s"] - near) - 0.05 * bl[0].b
        if best is None or score > best[0]: best = (score, j, bl)
    if best is None: raise ValueError(f"'{text[:40]}' not found near {near}")
    score, j, bl = best
    a = max(0, j + bl[0].b - bl[0].a)                                         # unmatched leading tokens: take the words before
    last = bl[-1]; b = j + last.b + last.size - 1
    for _ in range(len(tt) - last.a - last.size):   # unmatched trailing tokens: the words after, never past the sentence's end
        if b + 1 >= len(wt) or words[wi[b]]["w"].endswith((".", "?", "!")): break
        b += 1
    return wi[a], wi[b], round(score, 2)


def find_span(words, first, last, near):
    """(i0, i1): the first run of `first` within 6 s of `near` (source s), ending on the next `last` (at most 120 words on)."""
    fa = [norm(x) for x in first.split() if norm(x)]; la = [norm(x) for x in last.split() if norm(x)]
    ws = [norm(x["w"]) for x in words]
    cands = [i for i in range(len(words)) if ws[i:i + len(fa)] == fa]
    if not cands: raise ValueError(f"'{first}' not found near {near}")
    i = min(cands, key=lambda k: abs(words[k]["s"] - near))
    if abs(words[i]["s"] - near) > 6: raise ValueError(f"'{first}' is {words[i]['s'] - near:+.1f} s from {near}")
    for j in range(i + len(fa) - len(la), min(len(words), i + 120)):
        if j >= i and ws[j:j + len(la)] == la: return i, j + len(la) - 1
    raise ValueError(f"end '{last}' not found after '{first}' @ {words[i]['s']:.1f}")


# ---------------------------------------------------------------------------------------------------- cut
_ENV = {}
def env_of(c):
    """zero_dead's level envelope of the whole mic track (10 ms hop), cached as .npy: decoding 2 hours of audio takes a while."""
    if c["mic16"] not in _ENV:
        p = os.path.join(c["work"], "cache", "env_mic16.npy")
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True); np.save(p, np.asarray(Z.level_env(c["mic16"]), np.float32))
        _ENV[c["mic16"]] = np.load(p).astype(np.float64)
    return _ENV[c["mic16"]]


def clip_line(c, ln):
    """A long-form clip that plays with its own sound (the source in his reel: OB 10-20 wants the source's own words, not his
    retelling). The long-form already trimmed each clip file to the part it used; its edges are tightened again on its own level
    (zero dead space) and its words come from whisper (they're the clip's, not his)."""
    wav = os.path.join(c["longform"], "clips", "audio", ln["clip"] + ".wav")
    env = Z.level_env(np.frombuffer(run_bytes(["ffmpeg", "-nostdin", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]),
                                    np.float32))
    dur = len(env) * Z.HOP; st, en = Z.tighten(env, 0.0, dur)
    fps = c["fps"]; pcs = Z.pieces_of(env, st, en, fps); st, en = pcs[0][0], pcs[-1][1]
    os.makedirs(os.path.join(c["work"], "cache"), exist_ok=True)
    cw = os.path.join(c["work"], "cache", f"clip_{ln['clip']}_words.json")
    if not os.path.exists(cw):
        with tempfile.TemporaryDirectory() as td:
            t = os.path.join(td, "c.wav")
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{st:.3f}", "-to", f"{en:.3f}", "-i", wav, t])
            json.dump([dict(w=w, s=round(a + st, 3), e=round(b + st, 3)) for a, b, w in whisper_words(t)], open(cw, "w"))
    return dict(id=ln["id"], role="clip", clip=ln["clip"], pieces=[[round(x, 4), round(y, 4)] for x, y in pcs],
                words=json.load(open(cw)), dropped=[])


def reel_words(c, lines):
    """Apple's words for every stretch of source a reel uses: lines within 45 s of each other share one transcript window, so
    each line is found in the same transcript it was written from (a window starting mid-sentence hears its edges differently)."""
    ts = sorted(ln["near"] for ln in lines if not ln.get("clip")); blocks = []
    for t in ts:
        if blocks and t - blocks[-1][1] <= 45: blocks[-1][1] = t
        else: blocks.append([t, t])
    return {tuple(b): words_at(c, round(b[0] - 8, 2), round(b[1] + 30, 2)) for b in blocks}


def refine_edges(env, pieces, lo, hi, fps, A, T):
    """Every piece edge checked once more against the room around it. zero_dead judges by the line's own level and stops a
    word's onset at the first window under T, so a 10 ms dip before a "t" cut off the "s" of "steroids" (the reel said
    "teroids"; OB 10-25: never cut a word). Floor = the 10th percentile of the 1.2 s around the edge; S = max(floor + 10, T).
      start  past lead-in that is only the room (under floor + 6), then back over a soft onset above max(floor + 12, T - 10),
             riding through dips of 20 ms or less, at most 150 ms and never into the word before, keeping 10 ms ("And" opens at
             -67 to -55 dB, under T: cut there, whisper heard "in")
      end    never extended (zero_dead's word-end rule keeps word-final consonants); only trailing noise under S is trimmed,
             never closer than 30 ms after the last window above A (the C4373 room sits near -60 dB and its noise read as
             0.1-0.2 s silences at the joins)"""
    H = Z.HOP; out = []
    for k, (p, q) in enumerate(pieces):
        a0, b0 = int(round(p / H)), int(round(q / H))
        def S(i):
            w = env[max(0, i - 60):i + 60]; return max(float(np.percentile(w, 10)) + 10, T)
        lim = max(a0 - 15, int(round(lo / H)) if (k == 0 and lo) else 0)
        if k: lim = max(lim, int(round(out[-1][1] / H)) + 2)
        w = env[max(0, a0 - 60):a0 + 60]; floor = float(np.percentile(w, 10))
        i = a0
        while i < b0 - 3 and env[i] <= floor + 6: i += 1                   # lead-in that is just the room: out
        for thr, most in ((T, 15), (max(floor + 12, T - 10), 5)):           # a fricative above T (150 ms), then a soft vowel onset
            stop = max(lim, i - most)                                          # under it but clearly above the room (50 ms: no breaths)
            while i - 1 > stop:
                if env[i - 1] > thr: i -= 1
                elif i - 3 > stop and (env[i - 3] > thr or env[i - 2] > thr): i -= 2   # a dip of 20 ms or less inside the onset
                else: break
        st = max(lim * H, i * H - 0.01)
        e_ = S(b0) + 3; j = b0   # 3 dB over the line's T: after levelling, a tail just above T read as silence in the mix
        last_a = max([x for x in range(i, b0) if env[x] > A] or [b0 - 3])
        while j > last_a + 3 and env[j - 1] <= e_: j -= 1
        en = j * H + (0.02 if j < b0 else 0.0)
        st, en = round(st * fps) / fps, round(min(en, q) * fps) / fps
        if en - st >= 2 / fps: out.append((st, en))
    return out


_ENVS = {}
def breathe(src, pieces, most=0.2):
    """Every splice edge with his sound right outside it moves out to the nearest real pause, by the gate's own test (the 0.1 s
    past the edge 25 dB under his speech, or near the floor), at most `most` s and never onto a neighbouring piece of the same
    source. Re-cut 10-28 under M26: R2's "did." lost its released d 30 ms after the cut, R5's "Is this" its breathy onset 0.13
    s before it. An edge with no pause within reach stays (he ran straight on: that needs a different line edge)."""
    if src not in _ENVS: _ENVS[src] = Z.level_env(src)
    e, H = _ENVS[src], Z.HOP
    def quiet(t, side):   # the gate's 0.1 s test, and the 30 ms right at the edge too: R2's "did." released its d 20 dB under
        i = int(round(t / H)); Pl = float(np.percentile(e[max(0, i - 100):i + 100], 90))   # him, and the 0.1 s mean hid it
        lim = max(float(np.percentile(e[max(0, i - 300):i + 300], 10)) + 6, Pl - 25)
        db = lambda o: float(20 * np.log10(np.mean(10 ** (o / 20)) + 1e-9)) if len(o) else -120.0
        if side == "start": return db(e[max(0, i - 10):i]) <= lim and db(e[max(0, i - 3):i]) <= lim
        return db(e[i:i + 10]) <= lim and db(e[i:i + 3]) <= lim
    moved = []
    for k, pq in enumerate(pieces):
        for side, j, d_ in (("start", 0, -0.005), ("end", 1, 0.005)):
            t = pq[j]
            if quiet(t, side): continue
            nb = [q for q in pieces if q is not pq and (q[1] <= t + 1e-3 if side == "start" else q[0] >= t - 1e-3)]
            wall = (max(q[1] for q in nb) + 0.02) if side == "start" and nb else (min(q[0] for q in nb) - 0.02) if nb else None
            x = t
            while abs(x - t) < most:
                x += d_
                if wall is not None and ((side == "start" and x < wall) or (side == "end" and x > wall)): break
                if quiet(x, side): moved.append((round(t, 3), round(x, 3))); pq[j] = round(x, 4); break
    return moved


def tighten_joins(src, pieces, fps, most=0.15):
    """M44 (OB 11-03: "make the cuts sharper, still feels like there is dead space after im done talking"): at a splice the
    quiet after his last word plus the quiet before his next is at most 0.15 s. Only quiet is trimmed (the gate's pause test),
    leaving 40 ms after a word and 20 ms before one, so no word is touched. pieces: [[p, q], ...] in play order, one source."""
    if src not in _ENVS: _ENVS[src] = Z.level_env(src)
    e, H = _ENVS[src], Z.HOP
    def loud(i):
        Pl = float(np.percentile(e[max(0, i - 100):i + 100], 90)); return e[i] > max(float(np.percentile(e[max(0, i - 300):i + 300], 10)) + 6, Pl - 25)
    done = []
    for A, B in zip(pieces, pieces[1:]):
        if abs(B[0] - A[1]) < 0.002: continue   # lines that meet in the source: not a splice
        ia, ib = int(round(A[1] / H)), int(round(B[0] / H))
        la = ia
        while la > int(A[0] / H) + 2 and not loud(la - 1): la -= 1
        lb = ib
        while lb < int(B[1] / H) - 2 and not loud(lb): lb += 1
        tail, lead = (ia - la) * H, (lb - ib) * H
        if tail + lead <= most: continue
        nt = max(0.04, min(tail, most - min(lead, most / 2))); nl = max(0.02, min(lead, most - nt))
        A[1] = round(la * H + nt, 4); B[0] = round(lb * H - nl, 4); done.append((round(tail + lead, 3), round(nt + nl, 3)))
    return done


def cut_line(c, ln, tx):
    """One reel line -> its pieces: the words the long-form kept, in runs, each cut with zero dead space (every word whole)."""
    if ln.get("clip"): return clip_line(c, ln)
    near = ln["near"]; words = next(w for (a, b), w in tx.items() if a <= near <= b)
    i0, i1, score = find_line(words, ln["text"], near)
    if score < 0.5: raise ValueError(f"{ln['id']}: weak match ({score}) for '{ln['text'][:50]}' near {near}")
    env = env_of(c); fps = c["fps"]
    keep = kept_mask(c, words, i0, i1)
    for k in ln.get("force_keep", []):          # a word the cut list's edge clips by a few ms (checked by ear and by the diff)
        keep[k] = True
    runs, k = [], 0
    while k < len(keep):
        if keep[k]:
            j = k
            while j < len(keep) and keep[j]: j += 1
            runs.append((i0 + k, i0 + j - 1)); k = j
        else: k += 1
    pieces, said, dropped = [], [], [words[i0 + k]["w"] for k in range(len(keep)) if not keep[k]]
    for a, b in runs:
        P = Z.line_ref(env, words[a]["s"], words[b]["e"]); A, T = P - Z.ACTIVE, P - Z.TAIL
        lo = min(Z.word_core(env, words[a - 1], A, T)[1], words[a - 1]["e"]) + 0.03 if a > 0 else None
        hi = max(Z.word_core(env, words[b + 1], A, T)[0], words[b + 1]["s"]) - 0.03 if b + 1 < len(words) else None
        run_p = [xy for p, q in Z.cut_words(env, words, a, b, fps, lo, hi) for xy in inside_kept(c, p, q, fps)]  # never a dropped frame
        for x, y in refine_edges(env, run_p, lo, hi, fps, A, T):
            pieces.append([round(x, 4), round(y, 4)])
        said += [dict(w=words[i]["w"], s=words[i]["s"], e=words[i]["e"]) for i in range(a, b + 1)]
    return dict(id=ln["id"], role=ln.get("role", "body"), text=ln["text"], pieces=pieces, words=said, dropped=dropped,
                heard=" ".join(words[i]["w"] for i in range(i0, i1 + 1)), match=score)


def voice(c, lines, out):
    """The cut voice from the long-form's 48 kHz master, 5 ms fades at every join, mastered by voice_master (each line levelled)."""
    segs, spans, cur = [], [], 0; f5 = int(0.005 * SR)
    def grab(src, a, b):   # only the piece itself (the master is 2 hours long)
        return np.frombuffer(run_bytes(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", src,
                                        "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]), np.float32).astype(np.float64)
    allp = [(os.path.join(c["longform"], "clips", "audio", l["clip"] + ".wav") if l.get("clip") else c["voice48"], p, q) for l in lines for p, q in l["pieces"]]
    meets = [k > 0 and allp[k][0] == allp[k - 1][0] and abs(allp[k][1] - allp[k - 1][2]) < 0.002 for k in range(len(allp))]   # no cut: no fade
    k = 0
    for l in lines:
        n0 = cur
        for _ in l["pieces"]:
            src, p, q = allp[k]; g = grab(src, p, q)
            n = int(round((q - p) * SR)); g = np.pad(g, (0, max(0, n - len(g))))[:n]
            if len(g) > 2 * f5:
                if not meets[k]: g[:f5] *= np.linspace(0, 1, f5)
                if not (k + 1 < len(allp) and meets[k + 1]): g[-f5:] *= np.linspace(1, 0, f5)
            segs.append(g); cur += len(g); k += 1
        spans.append((n0, cur))
    y, rep = VM.master(np.concatenate(segs), SR, -14.0, spans)
    import ytclip_pic as P
    y = np.concatenate([np.zeros((int(round(P.LEAD * SR)),) + y.shape[1:]), y])   # the silent prop beat before his first word
    from scipy.io import wavfile
    with tempfile.TemporaryDirectory() as td:
        t = os.path.join(td, "v.wav"); wavfile.write(t, SR, np.asarray(y, np.float32))
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", t, "-c:a", "pcm_s24le", out])
    return rep


def run_bytes(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode: raise RuntimeError(" ".join(cmd[:6]) + "\n" + p.stderr.decode()[-2000:])
    return p.stdout


def whisper_words(wav):
    """Whisper large-v3-turbo, word level (-ml 1 -sow: plain mode drops short words in fast speech), on any audio file."""
    with tempfile.TemporaryDirectory() as td:
        w16 = os.path.join(td, "v16.wav")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", w16])
        o = run(["whisper-cli", "-m", WHISPER, "-l", "en", "-f", w16, "-ml", "1", "-sow", "-np"])
    ws = []
    for l in o.splitlines():
        m = re.match(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)", l)
        if m and m[7].strip() and not m[7].strip().startswith(("(", "[", "♪")):
            ws.append((int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6]), m[7].strip()))
    return ws


def inside_piece(lines, w, margin=0.06):
    """True when word w's middle sits inside one of its line's pieces, `margin` clear of both edges: the cut can't have touched
    it, so a whisper miss there is the recogniser (it runs fast joined words together), not a clipped word."""
    m = (w["s"] + w["e"]) / 2
    return any(p + margin <= m <= q - margin for l in lines for p, q in l["pieces"] if any(x is w for x in l["words"]))


def heard_in_source(c, w, tok):
    """Is `tok` heard in the raw recording around word w (its own source seconds)? The cut only removes sound, so a word that
    the raw take reads the same way ("that" for "fat", "in" for "And") is how he said it, not a clip."""
    if not c or not w or w.get("s") is None: return False
    with tempfile.TemporaryDirectory() as td:
        t = os.path.join(td, "s.wav")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0, w['s'] - 1.4):.2f}", "-t", "3.2", "-i", c["voice48"], "-ac", "1", "-ar", "16000", t])
        got = TK.toks(run(["whisper-cli", "-m", WHISPER, "-l", "en", "-f", t, "-np", "-nt"]))
    return any(difflib.SequenceMatcher(None, tok, x).ratio() >= 0.75 for x in got)


def edge_quiet(c, lines, w):
    """The cut nearest word w lands in quiet: the mic at that piece edge is 30 dB+ under the line's speech (its p90), so the
    whole word is inside the piece. A cut inside a word lands on loud sound ("teroids" started at -48 dB on a -24 dB line)."""
    if not w or w.get("s") is None: return False
    env = env_of(c); l = next((l for l in lines if any(x is w for x in l["words"])), None)
    if l is None or l.get("clip"): return False
    P = Z.line_ref(env, l["words"][0]["s"], l["words"][-1]["e"])
    edges = [(p, "start") for p, q in l["pieces"]] + [(q, "end") for p, q in l["pieces"]]
    t, side = min(edges, key=lambda e: min(abs(e[0] - w["s"]), abs(e[0] - w["e"])))
    k = int(round(t / Z.HOP)); lev = env[k] if side == "start" else env[max(0, k - 1)]
    return bool(lev < P - 30)


def verify(lines, wav, c=None):
    """Whisper on the cut voice against what he said (each line's text; a clip's own words): missing / extra words, cue words and
    the yardstick. Apple's spellings ("1000s", "FDI") never count: the expected words are the line texts. A missing or changed word
    is ASR when it sits inside an untouched piece, CUT-RISK when it sits at a piece edge; every CUT-RISK gets a second listen on
    its own (the 3.4 s around it) and stays flagged only if it's still not there (over a whole reel whisper runs fast joined words
    together: on 10-28 "like", "instead" and "your" were all there when heard alone)."""
    heard = whisper_words(wav)
    got = [t for a, b, w in heard for t in TK.toks(w)]; got_t = [a for a, b, w in heard for t in TK.toks(w)]
    exp, exp_w = [], []
    for l in lines:   # each text token mapped to the Apple word it was heard as (for its source time)
        tt = TK.toks(l.get("text") or " ".join(w["w"] for w in l["words"]))
        wt, wi = [], []
        for k, w in enumerate(l["words"]):
            for t in TK.toks(w["w"]): wt.append(t); wi.append(k)
        m = {}
        for blk in difflib.SequenceMatcher(None, tt, wt, autojunk=False).get_matching_blocks():
            for x in range(blk.size): m[blk.a + x] = wi[blk.b + x]
        for k, t in enumerate(tt):
            near = m.get(k, m.get(max([x for x in m if x < k], default=-1), 0))
            exp.append(t); exp_w.append(l["words"][near] if l["words"] else None)
    sm = difflib.SequenceMatcher(None, exp, got, autojunk=False); diffs = []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal": continue
        at = got_t[b1] if b1 < len(got_t) else (got_t[-1] if got_t else 0)
        if op == "replace" and a2 - a1 == b2 - b1 and all(difflib.SequenceMatcher(None, exp[a1 + k], got[b1 + k]).ratio() >= 0.6 for k in range(a2 - a1)):
            kind = "spelling"
        elif op == "insert": kind = "extra"
        else:
            kind = "ASR" if all(exp_w[k] is not None and inside_piece(lines, exp_w[k]) for k in range(a1, a2)) else "CUT-RISK"
        if kind == "CUT-RISK":
            with tempfile.TemporaryDirectory() as td:
                w16 = os.path.join(td, "w.wav")
                run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0, at - 1.6):.2f}", "-t", "3.4", "-i", wav, "-ac", "1", "-ar", "16000", w16])
                alone = TK.toks(run(["whisper-cli", "-m", WHISPER, "-l", "en", "-f", w16, "-np", "-nt"]))
            ok = all(any(difflib.SequenceMatcher(None, e, x).ratio() >= 0.75 for x in alone) for e in exp[a1:a2])
            kind = "heard-alone" if ok else "CUT-RISK"
            if kind == "CUT-RISK" and c is not None and not any(heard_in_source(c, exp_w[k], exp[k]) for k in range(a1, a2)):
                kind = "said-that-way"   # the raw take reads the same: not the cut
            if kind == "CUT-RISK" and c is not None and all(edge_quiet(c, lines, exp_w[k]) for k in range(a1, a2)):
                kind = "edge-in-quiet"   # the cut at this word lands where the mic is 30 dB+ under his speech: the word is whole
        diffs.append(f"{at:6.2f}s {op} {kind} [{' '.join(exp[a1:a2])}] -> [{' '.join(got[b1:b2])}]   ...{' '.join(exp[max(0, a1 - 4):a1])} | {' '.join(exp[a2:a2 + 4])}...")
    cues = [w for a, b, w in heard if re.search(r"(?i)\b(cut that|claude|cloud|clod|clyde)\b", w)]
    d = Z.dead_space(wav)
    return dict(match=round(sm.ratio(), 3), diffs=diffs, cut_risk=sum(" CUT-RISK " in x for x in diffs), cues=cues, dead=d)


def cmd_words(work, a, b):
    """Apple's words between source seconds a and b, long-form outtakes in [brackets]: for writing a reel's lines."""
    c = cfg(work); a, b = float(a), float(b); out, line = [], []
    ws = words_at(c, a, b); keep = kept_mask(c, ws, 0, len(ws) - 1)
    for x, k in zip(ws, keep):
        t = x["w"] if k else f"[{x['w']}]"
        line.append(f"{t}@{x['s']:.2f}" if not line else t)
        if x["w"].endswith((".", "?", "!")): out.append(" ".join(line)); line = []
    if line: out.append(" ".join(line))
    print("\n".join(out))


def cmd_cut(work, only):
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]; over = []
    for r in picks:
        if only and r["id"] not in only: continue
        d = os.path.join(work, "reels", r["id"]); os.makedirs(d, exist_ok=True)
        tx = reel_words(c, r["lines"])
        lines = [cut_line(c, ln, tx) for ln in r["lines"]]
        used = []   # a source instant may play once: an overlap is a stutter (10-28: 67 ms of "And" twice in R4)
        for l in lines:
            if l.get("clip"): continue
            keep = []
            for p, q in l["pieces"]:
                for a, b in used:
                    if p < b - 1e-3 and q > a + 1e-3:
                        print(f"     {l['id']}: piece {p:.3f}-{q:.3f} overlaps {a:.3f}-{b:.3f}, trimmed"); p = max(p, b) if p >= a else p; q = min(q, a) if q <= b else q
                if q - p >= 2 / c["fps"]: keep.append([p, q])
            l["pieces"] = keep; used += [tuple(x) for x in keep]
        # never cut him off (OB 10-28, twice; M26): the reel's first and last edges go to whole sentences inside a real breath
        # (moves.snap); every piece edge is then checked against its source below, as the gate checks the render
        import moves, qc_gate
        src_of = lambda l: os.path.join(c["longform"], "clips", "audio", l["clip"] + ".wav") if l.get("clip") else c["voice48"]
        f0, fl = lines[0]["pieces"][0], lines[-1]["pieces"][-1]
        a = moves.snap(src_of(lines[0]), f0[0], f0[1])[0]; b = moves.snap(src_of(lines[-1]), fl[0], fl[1])[1]
        if abs(a - f0[0]) > 1e-3 or abs(b - fl[1]) > 1e-3: print(f"     snap: start {f0[0]:.3f} -> {a:.3f}, end {fl[1]:.3f} -> {b:.3f}")
        f0[0], fl[1] = round(a, 4), round(b, 4)
        by_src = {}
        for l in lines: by_src.setdefault(src_of(l), []).extend(l["pieces"])
        for s_, ps in by_src.items():
            mv = breathe(s_, ps)
            if mv: print(f"     breathe {os.path.basename(s_)}: " + ", ".join(f"{x:.3f}->{y:.3f}" for x, y in mv))
        runs = [[]]   # his pieces in the order they play, a new run after each clip (the clip sits between them)
        for l in lines:
            if l.get("clip"): runs.append([])
            else: runs[-1] += l["pieces"]
        tj = [x for run_ in runs for x in tighten_joins(c["voice48"], run_, c["fps"])]
        if tj: print("     joins tightened (s of quiet before -> after): " + ", ".join(f"{x}->{y}" for x, y in tj))
        rep = voice(c, lines, os.path.join(d, "voice.wav"))
        open(os.path.join(d, "script.txt"), "w").write("\n".join((l.get("text") or " ".join(w["w"] for w in l["words"])) for l in lines) + "\n")
        import ytclip_pic as P
        dur = P.LEAD + sum(q - p for l in lines for p, q in l["pieces"])
        v = verify(lines, os.path.join(d, "voice.wav"), c)
        segs = []   # two lines that meet in the source play as one stretch: that join isn't a cut (R1 "Oreos. | You", 10-28)
        for s_, p, q in ((src_of(l), p, q) for l in lines for p, q in l["pieces"]):
            if segs and segs[-1][0] == s_ and abs(segs[-1][2] - p) < 0.002: segs[-1] = (s_, segs[-1][1], q)
            else: segs.append((s_, p, q))
        v["edges"] = list(qc_gate.c_edges(os.path.join(d, "voice.wav"), segs))
        if dur >= MAX_S:   # M33: drop lines from the pick, or drop the reel if it no longer stands alone; never force it
            stale = " (the cut.json there is an older pick)" if os.path.exists(os.path.join(d, "cut.json")) else ""
            print(f"== STOP {r['id']} {r['slug']}: {dur:.1f} s is at or over the 1:30 cap (M33), no cut.json written{stale}"); over.append(r["id"]); continue
        json.dump(dict(id=r["id"], fps=c["fps"], duration=round(dur, 3), lines=lines, master=rep, verify=v, segs=segs),
                  open(os.path.join(d, "cut.json"), "w"), indent=1)
        dd = v["dead"]
        print(f"== {r['id']} {r['slug']}: {dur:.1f} s, {sum(len(l['pieces']) for l in lines)} pieces, {len(lines)} lines | "
              f"silent {dd['silent_pct']}% (longest {dd['longest_silence']} s), dead {dd['dead_pct']}% | words match {v['match']}, "
              f"{len(v['diffs'])} diffs, {v['cut_risk']} CUT-RISK, cues {v['cues']} | {rep['out_lufs']} LUFS, TP {rep['out_true_peak']}, clipped {rep['clipped_samples']}"
              f" | edges {v['edges'][0]}: {v['edges'][1]}")
        for l in lines:
            if l.get("clip"): print(f"     {l['id']}: clip {l['clip']} {l['pieces'][0]} \"{' '.join(w['w'] for w in l['words'])[:80]}\""); continue
            print(f"     {l['id']}: match {l['match']} heard \"{l['heard'][:90]}\"" + (f"  | long-form dropped {l['dropped']}" if l["dropped"] else ""))
        for x in v["diffs"]: print("     WORDS", x)
    if over: sys.exit(f"over the 1:30 cap (M33): {', '.join(over)}")


def cmd_mock(work, only):
    """Stills for the shot page (OB's rule: no full render before he OKs it): frame 0, then one per span (a card receipt once
    its numbers have landed), drawn by the same compositor the render uses (ytclip_look)."""
    import ytclip_look as LK
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]
    for r in picks:
        if only and r["id"] not in only: continue
        K = LK.build(c, r); d = os.path.join(work, "reels", r["id"], "stills"); os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith(".jpg") and not f.startswith("._"): os.remove(os.path.join(d, f))
        LK.still(K, 0.15).convert("RGB").resize((540, 960)).save(os.path.join(d, "f0.jpg"), quality=84); rows = []
        for k, sp in enumerate(K["spans"]):
            if sp["t1"] - sp["t0"] < 0.3: continue
            rc = LK.rc_by(K, sp["rc"]) if sp.get("rc") else None; t = (sp["t0"] + sp["t1"]) / 2
            if rc and not sp.get("cover") and rc["kind"] not in ("video", "photo"): t = min(sp["t1"] - 0.05, max(sp["t0"], rc["t0"]) + 2.2)
            name = f"s{k:02d}.jpg"; LK.still(K, t).convert("RGB").resize((540, 960)).save(os.path.join(d, name), quality=80)
            ws = [w["w"] for w in K["words"] if sp["t0"] - 0.02 <= w["s"] < sp["t1"]]
            rows.append(dict(still=name, t0=round(sp["t0"], 2), t1=round(sp["t1"], 2), state=sp["state"], move=sp.get("move"),
                             cover=bool(sp.get("cover")), receipt=receipt_line(rc), first=" ".join(ws[:3]), last=" ".join(ws[-3:]) if len(ws) > 3 else ""))
        share = {st: round(sum(x["t1"] - x["t0"] for x in K["spans"] if x["state"] == st) / K["T"] * 100) for st in ("split", "full", "clip")}
        json.dump(dict(reel=r["id"], duration=K["T"], label=K["label"], share=share, receipts=len(K["recs"]), rows=rows),
                  open(os.path.join(d, "stills.json"), "w"), indent=1)
        print(f"== {r['id']}: {K['T']:.1f} s, split {share['split']}% full {share['full']}% clip {share['clip']}%, {len(K['recs'])} receipts: "
              + ", ".join(f"{x['kind']}@{x['t0']:.1f}" for x in K["recs"]), flush=True)


def receipt_line(rc):
    """What a receipt is, in a few words, for the shot page."""
    if not rc: return ""
    e = rc["ev"]; k = rc["kind"]
    if k == "video": return e.get("page_label") or f"footage: {rc.get('credit') or e.get('broll', '')}"
    if k == "photo": return f"photo: {e.get('title') or os.path.basename(rc.get('path', ''))}"
    if k == "doc": return f"the page itself: {e.get('source') or (e.get('doc') or {}).get('source', '')}"
    if k == "quote": return f"its own title: {rc.get('credit', '')}"
    if k == "count": return "count-up: " + " vs ".join(str(it[0]) for it in e.get("items", [])[:2]) + (f" ({str(e.get('source'))[:40]})" if e.get("source") else "")
    if k == "bars": return f"bars: {e.get('title', '')}" + (f" ({str(e.get('source'))[:40]})" if e.get("source") else "")
    if k == "versus": return f"comparison: {e.get('title', '')}"
    if k == "study": return "study: " + str((e.get("study") or {}).get("journal", "") if isinstance(e.get("study"), dict) else "")
    return k


def cmd_lookoff(work, only):
    """His eyes at both edges of every camera piece (zero_dead.lookoff: 3 frames per edge, 2 must agree, so a blink isn't a
    flag). The look decides what each flag gets: in the split he is in the box already; in a full-frame line the edge switches
    to the split for 0.67 s (M37: the screen + PiP, never a cutaway)."""
    import ytclip_pic as P
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]
    for r in picks:
        if only and r["id"] not in only: continue
        d = os.path.join(c["work"], "reels", r["id"]); cut = json.load(open(os.path.join(d, "cut.json")))
        shots, nf = P.timeline(c, cut); obs = [s for s in shots if s["kind"] == "ob"]
        rows = Z.lookoff(c["camera"], [(s["a"], s["b"]) for s in obs]); out = []
        for k, side, t, py, yaw, why in rows:
            if not why: continue
            s = obs[k]; out.append(dict(shot=k, side=side, reel_t=round(s["t0"] if side == "start" else s["t1"], 2), src_t=round(t, 2), why=why))
        json.dump(out, open(os.path.join(d, "lookoff.json"), "w"), indent=1)
        print(f"== {r['id']}: {len(obs)} camera shots, {len(out)} edge flags: " + "; ".join(f"{x['reel_t']}s {x['side']} {x['why']}" for x in out), flush=True)


TARGET = dict(silent_pct=3.0, longest_silence=0.2, live=8.6, first_move=1.5, lufs=(-15.0, -13.0), tp=-1.0, open_rms=-15.0)


def open_rms(path):
    """RMS (dBFS) of the first half second: PROVEN-OPENERS #4, no blast at 0.0 s (keep it under -15)."""
    x = np.frombuffer(run_bytes(["ffmpeg", "-nostdin", "-v", "error", "-t", "0.5", "-i", path, "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"]), np.float32)
    return round(float(20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)), 1) if len(x) else -120.0


def faces_in_render(path, L, every=0.5):
    """Apple Vision on the render every 0.5 s: (t, every face box, largest first) per frame, for the frame-1 size check and the
    face-vs-text check (in the split the footage can hold a bigger face than his)."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        step = max(1, round(every * 30000 / 1001))   # exact frame numbers, so each sample's time is exact (11-04: the fps filter's
        # frame sat a few ms before its label, and at R3's 46.747 s cut the last split frame was judged as the full frame after it)
        run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", f"select='not(mod(n\\,{step}))'", "-fps_mode", "passthrough", "-q:v", "3",
             os.path.join(td, "f%04d.jpg")])
        imgs = sorted(f for f in os.listdir(td) if f.endswith(".jpg"))
        if imgs:
            res = run([os.path.join(BIN, "faces")] + [os.path.join(td, f) for f in imgs]).splitlines()
            for line in res:
                pth, rest = line.split(" ", 1); k = int(os.path.basename(pth)[1:5]) - 1
                boxes = [] if rest.strip() in ("none", "error") else [[float(v) for v in b.split()] for b in rest.split("|") if b.strip()]
                out.append((round(k * step * 1001 / 30000, 3), sorted(boxes, key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))))
    return out


def cmd_qa(work, only):
    """Every rendered reel before it can ship (it ships only at all of them): words (whisper on the file vs what he said, every
    missing word at a cut edge heard again on its own), silence, loudness and peaks, the motion score, no blast in the first
    0.5 s, and no caption on his face (Vision every 0.5 s: in the split his head, cap included, stays under the seam captions;
    full frame the captions stay under his chin). Frame 0's face size is reported, not judged: he opens on his face (M37)."""
    import motion_score as MS, ytclip_look as LK
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]; summary = []
    for r in picks:
        if only and r["id"] not in only: continue
        d = os.path.join(c["work"], "reels", r["id"]); cut = json.load(open(os.path.join(d, "cut.json")))
        f = os.path.join(d, "out", f"{r['id']}-{r['slug']}.mp4")
        if not os.path.exists(f): continue
        K = json.load(open(os.path.join(d, "look.json"))); q = dict(file=os.path.basename(f))
        q["words"] = w = verify(cut["lines"], f, c)
        ds = Z.dead_space(f); q["silent_pct"], q["longest_silence"] = ds["silent_pct"], ds["longest_silence"]
        vc = VM.check(f); q["lufs"], q["true_peak"], q["flat_tops"] = vc["lufs"], vc["true_peak"], vc["flat_tops"]
        m = MS.measure(f, 1.2); q["live"], q["first_move"], q["flash"], q["idle"] = m["live"], m["first"], len(m["flash"]), round(m["idle_share"], 3)
        q["open_rms"] = open_rms(f)
        fc = faces_in_render(f, None); f0 = next((bs[0] for t, bs in fc if t <= 0.5 and bs), None)
        q["face_f0"] = round(((f0[2] - f0[0]) * (f0[3] - f0[1])) / (LK.FW * LK.FH), 3) if f0 else 0.0
        over = []
        for t, bs in fc:
            sp = LK.span_at(K, t)
            if not bs or sp["state"] == "clip": continue
            if sp["state"] == "split":   # his head (cap top ~0.55 face boxes over Vision's box) under the captions just above the seam
                mine = [b for b in bs if (b[1] + b[3]) / 2 > LK.SEAM]
                cap = min((b[1] - 0.55 * (b[3] - b[1]) for b in mine), default=None)
                if cap is not None and cap < LK.CAP_SPLIT + 36: over.append((t, round(cap), LK.CAP_SPLIT + 36))
            else:
                chin = LK.ob_shot_at(K, t).get("chin", 1150); up = t < LK.label_end(K)
                y = min(max(chin + 92, 1250), 1460) if not up else min(max(chin + 100, 1180), 1380)
                if bs[0][3] > y - 40: over.append((t, round(bs[0][3]), round(y - 40)))
        q["text_over_face"] = over
        fails = []
        if w["cut_risk"]: fails.append(f"{w['cut_risk']} word(s) at a cut edge not heard")
        if w["cues"]: fails.append(f"retake cue heard: {w['cues']}")
        if q["silent_pct"] > TARGET["silent_pct"] or q["longest_silence"] > TARGET["longest_silence"]: fails.append("dead space")
        if not (TARGET["lufs"][0] <= q["lufs"] <= TARGET["lufs"][1]) or q["true_peak"] > TARGET["tp"] or q["flat_tops"]: fails.append("loudness/peaks")
        if q["flash"]: fails.append(f"{q['flash']} flash frame(s)")
        if q["first_move"] is None or q["first_move"] > TARGET["first_move"]: fails.append(f"first move {q['first_move']}")
        if q["live"] < TARGET["live"]: fails.append(f"live {q['live']}")
        if q["open_rms"] > TARGET["open_rms"]: fails.append(f"loud open {q['open_rms']} dBFS")
        if over: fails.append(f"caption near his face at {[o[0] for o in over][:5]}")
        q["pass"], q["fails"] = not fails, fails
        json.dump(q, open(f[:-4] + ".qa.json", "w"), indent=1, default=str); summary.append(q)
        print(f"{'PASS' if not fails else 'FAIL'} {q['file']}: silent {q['silent_pct']}% ({q['longest_silence']} s), {q['lufs']} LUFS TP {q['true_peak']}, "
              f"live {q['live']} first {q['first_move']} flash {q['flash']}, frame-0 face {q['face_f0']:.1%}, open {q['open_rms']} dBFS"
              + (f" | {'; '.join(fails)}" if fails else ""), flush=True)
    json.dump(summary, open(os.path.join(c["work"], "reels", "qa_summary.json"), "w"), indent=1, default=str)
    return summary


PREDICT = {   # month-relative reach multiple, from brain.py drivers/engines on 10-28 (the Monday review scores these)
    "R1": (1.2, "DEFENSE 1.26x reach, food cover 1.17x; seed oils topic 0.82x"),
    "R2": (1.1, "REACT_OTHER 1.19x reach (150 d); his one Liver King post 0.95x reach, 1.65x shares"),
    "R3": (0.9, "GLP-1 topic 1.17x shares; his Ozempic posts 0.45x reach, 4.67x shares"),
    "R4": (1.1, "steps topic 1.18x reach; EDU 0.88x"),
    "R5": (1.2, "DEFENSE 1.26x reach; numbers in every line"),
}


def cmd_deliver(work, only):
    """Only reels that passed QA go to the AirDrop folder, one file each (M45: no variants, no phone copies): POST-NOTES.txt
    (the caption to post with each), manifest.json (the loop's record of every file) and one prediction row per post in the
    vault's _PREDICTIONS.csv (the operator OS scores it at day 7)."""
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]
    dst = c["airdrop"]; os.makedirs(dst, exist_ok=True); man, notes = [], []
    for n, r in enumerate(picks, 1):
        if only and r["id"] not in only: continue
        d = os.path.join(c["work"], "reels", r["id"]); short = r["slug"].replace("-", " ").title()
        src = os.path.join(d, "out", f"{r['id']}-{r['slug']}.mp4"); qa = src[:-4] + ".qa.json"
        if not os.path.exists(src) or not os.path.exists(qa) or not json.load(open(qa))["pass"]:
            print(f"   not shipped: {os.path.basename(src)} (missing or failed QA)"); continue
        name = f"{n} {short}.mp4"
        import deliver as DV   # the only way a video goes into an AirDrop folder: blocks a gate FAIL, byte-checks
        if not DV.deliver(src, dst, name): print(f"   blocked by the QC gate: {name}"); continue
        notes.append(f"=== {n} {short}  ({r['id']})\nPost '{name}' to the grid.\n\nCaption:\n{r['caption']}\n")
        mb = os.path.getsize(src) / 1e6; q = json.load(open(qa)); K = json.load(open(os.path.join(d, "look.json")))
        man.append(dict(file=name, reel=r["id"], slug=r["slug"], feed=True, title=r.get("label", ""), title_has_number=any(ch.isdigit() for ch in r.get("label", "")),
                        receipts=len(K["recs"]), split_share=round(sum(x["t1"] - x["t0"] for x in K["spans"] if x["state"] == "split") / K["T"], 2),
                        source=c["video"], youtube=c["youtube_id"], seconds=json.load(open(os.path.join(d, "cut.json")))["duration"],
                        qa={k: q.get(k) for k in ("silent_pct", "longest_silence", "lufs", "true_peak", "live", "first_move", "face_f0", "open_rms")},
                        predicted_reach=PREDICT.get(r["id"], (None,))[0], predicted_basis=PREDICT.get(r["id"], (None, None))[1], size_mb=round(mb, 1)))
        print(f"   {name} ({mb:.1f} MB)")
    open(os.path.join(dst, "POST-NOTES.txt"), "w").write(
        f"Clips from {c.get('title', c['video'])}. Every file passed: words whole, no dead space, -14 LUFS, lips in sync, motion score, no text on your face.\n"
        "No music baked in: add your sound in the app. One file per reel; post each to the grid.\n\n"
        + "\n".join(notes))
    json.dump(dict(video=c["video"], youtube=c["youtube_id"], delivered=__import__("time").strftime("%Y-%m-%d %H:%M"), files=man),
              open(os.path.join(dst, "manifest.json"), "w"), indent=1)
    json.dump(man, open(os.path.join(c["work"], "manifest.json"), "w"), indent=1)
    vault = "/Users/YOU/Documents/Claude/Projects/ads/scripts for instagram/80-Performance/_PREDICTIONS.csv"
    if os.path.exists(vault):
        have = open(vault).read(); add = []
        for m in man:
            if not m["feed"] or f"yt-clip {m['reel']} {c['video']}" in have: continue
            add.append(f"{__import__('time').strftime('%Y-%m-%d')},to post,\"yt-clip {m['reel']} {c['video']}: {m['title']}\",yt-clip (feed),reach_multiple,"
                       f"{m['predicted_reach']},\"{m['predicted_basis']}\",,,\"{m['file']}\"")
        if add:
            with open(vault, "a") as fh: fh.write(("" if have.endswith("\n") else "\n") + "\n".join(add) + "\n")
            print(f"   {len(add)} predictions logged in _PREDICTIONS.csv")
    print(f"delivered to {dst}")


def cmd_review(work):
    """The loop's clipper half (Mondays; the Content Lab scores every reel daily). Finds the delivered clips among his posted reels
    (by transcript), shows each one against its month's median reel (trials and grid apart, the Lab's own month_rel), against
    its prediction, which opening won inside each pack, and the YouTube views that came from Instagram since delivery. Writes
    reels/REVIEW-<date>.md and proposes rule changes; it changes nothing on its own (a rule needs 2+ videos; OB OKs it)."""
    import importlib.util, time
    spec = importlib.util.spec_from_file_location("lab", os.path.expanduser("~/ob-ig-insights/lab.py")); LAB = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(LAB)
    c = cfg(work); man = json.load(open(os.path.join(c["work"], "manifest.json"))); picks = {r["id"]: r for r in json.load(open(os.path.join(work, "picks.json")))["reels"]}
    since = min(f.get("delivered", "") for f in [json.load(open(os.path.join(c["airdrop"], "manifest.json")))]) [:10]
    cat = LAB.catalogue(); snaps = LAB.snapshots(); rel, base = LAB.month_rel(cat, snaps)
    feats = json.load(open(os.path.expanduser("~/ob-ig-insights/data/lab/features.json")))
    texts = {}
    for rid in picks:
        cut = json.load(open(os.path.join(c["work"], "reels", rid, "cut.json")))
        texts[rid] = set(TK.toks(" ".join(l.get("text") or "" for l in cut["lines"])))
    found = []
    for code, m in cat.items():
        if m["posted"][:10] < since: continue
        txp = os.path.expanduser(f"~/ob-ig-insights/data/lab/tx/{code}.json")
        if not os.path.exists(txp): continue
        said = set(TK.toks(" ".join(sg[2] for sg in json.load(open(txp)).get("segs", []))))
        best = max(picks, key=lambda rid: len(said & texts[rid]) / max(1, len(texts[rid])))
        share = len(said & texts[best]) / max(1, len(texts[best]))
        if share < 0.5: continue
        f = feats.get(code, {}); r = picks[best]
        ttl = (f.get("title") or "").lower()
        ver = "F" if m["group"] == "grid" else next((v["id"] for v in r["versions"][1:]
               if all(w.lower() in ttl for w in " ".join(r["titles"][v["title"]]).split()[:3])), "T?")
        found.append(dict(code=code, reel=best, version=ver, group=m["group"], posted=m["posted"][:16], frame1=f.get("frame1"),
                          stats=snaps.get(code), rel=rel.get(code)))
    yt = json.loads(run([os.path.expanduser("~/ob-youtube/.venv-google/bin/python"), os.path.join(BIN, "ytclip_yt.py"), c["youtube_id"], since]))
    L = [f"# YouTube clips review, {time.strftime('%Y-%m-%d')} ({c['video']}, delivered {since})", ""]
    if not found: L += ["No delivered clip is posted yet (or the Lab hasn't ingested it: it reads the last 10 days at 7:00).", ""]
    for rid in picks:
        rows = [x for x in found if x["reel"] == rid]
        if not rows: continue
        L.append(f"## {rid} {picks[rid]['slug']} (pack tests: {picks[rid]['lever']}; predicted reach {PREDICT.get(rid, ('?',))[0]}x)")
        for x in sorted(rows, key=lambda z: z["version"]):
            rl = x["rel"] or {}; st = x["stats"] or {}
            fmt = lambda v, u="x": "-" if v is None else (f"{v:.2f}{u}" if u == "x" else f"{v:+.1f}{u}")
            L.append(f"- {x['version']} {x['group']} {x['code']} ({x['posted']}): reach {st.get('reach', '-')} = {fmt(rl.get('reach_x'))} of its month, "
                     f"skip {fmt(rl.get('skip_pts'), ' pts')}, watch {fmt(rl.get('watch_x'))}, shares {fmt(rl.get('shares_x'))}, saves {fmt(rl.get('saves_x'))}"
                     + (" (provisional: under 2 days)" if st.get("provisional") else ""))
        L.append("")
    L += [f"## YouTube: {yt['views']} views since {since}, {yt['instagram_views']} from Instagram links, {yt['shorts_views']} from Shorts",
          f"Sources: {json.dumps(yt['by_source'])}", "",
          "## Proposed rule changes (none apply without OB's OK; a rule needs 2+ videos agreeing)",
          "- Read the Content Lab RULEBOOK for each pack's lever; add each clip pack's result to the clipper preset only when 2+ packs agree.", ""]
    out = os.path.join(c["work"], "reels", f"REVIEW-{time.strftime('%Y-%m-%d')}.md"); open(out, "w").write("\n".join(L)); print(out); print("\n".join(L))


BUSY = re.compile(r"assemble\.py|react_render\.py|lecture_render\.py|tier_render\.py|hyperframes render|trial_variants\.py render|"
                  r"render_final|_render\.py")


def machine_busy():
    """Another session rendering? (one render at a time on this 8 GB Mac; never stop someone else's.) Their render scripts, or an
    ffmpeg encode that isn't ours."""
    me = os.getpid(); rows = run(["ps", "-axo", "pid=,ppid=,command="]).splitlines(); kids = {me}
    procs = [(int(x.split()[0]), int(x.split()[1]), x.split(None, 2)[2] if len(x.split()) > 2 else "") for x in rows]
    for _ in range(4): kids |= {pid for pid, pp, cm in procs if pp in kids}
    for pid, pp, cm in procs:
        if pid in kids or "ytclip" in cm: continue
        if BUSY.search(cm) or (cm.startswith(("ffmpeg", "/opt/homebrew/bin/ffmpeg")) and re.search(r"-c:v (libx26[45]|h264_videotoolbox|hevc_videotoolbox|prores)", cm)):
            return cm[:120]
    return None


def wait_free(log=print, settle=10):
    """Waits until no other session has rendered for `settle` s. Lowest priority (OB 10-28: "this is the lowest priority so
    queue it behind the more important ones") uses 180 s, so it never slips into the gap between another session's steps."""
    import time
    since, said = None, False
    while True:
        b = machine_busy()
        if b:
            if not said: log(f"waiting: another render is running ({b})"); said = True
            since = None; time.sleep(20); continue
        since = since or time.time()
        if time.time() - since >= settle: return
        time.sleep(5)


def cmd_render(work, only, test=False, low=False):
    """After OB's OK: one file per reel (M45). The picture renders in parallel chunks on the Mac mini (ytclip_look.render, 6
    workers), the voice is muxed, and the QC gate checks the file with every piece (M26 edges) and the camera map (M36 lip
    sync). --test: the first 10 s, no gate. --yield: lowest priority (OB 10-28: "queue it behind the more important ones"):
    nice 19, and no other heavy job on the Mac (render_slots) for 3 minutes before each reel."""
    import time, ytclip_look as LK, render_slots as RS
    if low: os.nice(19)
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]
    for r in picks:
        if only and r["id"] not in only: continue
        d = os.path.join(c["work"], "reels", r["id"]); rd = os.path.join(d, "render"); os.makedirs(rd, exist_ok=True)
        os.makedirs(os.path.join(d, "out"), exist_ok=True)
        RS.wait_free(log=lambda m: print(m, flush=True), max_jobs=1 if low else None, quiet=9 if low else 2)
        K = LK.build(c, r); plan = os.path.join(d, "look.json")
        if test:
            K["frames"] = min(K["frames"], int(10 * c["fps"])); plan = os.path.join(rd, "look_test.json"); json.dump(K, open(plan, "w"), default=str)
        t0 = time.time(); vid = os.path.join(rd, "video.mp4")
        LK.render(K, plan, vid, workers=6, scratch=os.path.join(os.path.expanduser("~/ob-scratch"), "ytclip", os.path.basename(work), r["id"]),
                  log=lambda m: print(m, flush=True))
        out = os.path.join(d, "out", f"{r['id']}-{r['slug']}{'-TEST' if test else ''}.mp4"); dur = K["frames"] / c["fps"]
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", vid, "-i", os.path.join(d, "voice.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac_at", "-b:a", "256k", "-t", f"{dur:.4f}", "-movflags", "+faststart", out])
        print(f"   {os.path.basename(out)}: {dur:.1f} s rendered in {time.time() - t0:.0f} s", flush=True)
        if not test:   # the QC gate on every render; it never raises, deliver.py blocks a FAIL
            try:
                import qc_gate
                segs = [tuple(x) for x in json.load(open(os.path.join(d, "cut.json"))).get("segs", [])]
                qc_gate.after_render(out, script=os.path.join(d, "script.txt"), segs=segs or None, cam=LK.cam_map(K))
            except Exception as e: print(f"   qc_gate could not run: {e!r}")


PAGE_CSS = """
:root { --bg: #f7f7f4; --surface: #ffffff; --ink: #141416; --muted: #5d5f66; --line: #dcdcd6; --hook: #ffd400; --hook-ink: #141416; --ok: #1f7a46;
  --display: "Barlow Condensed", "DIN Condensed", "Arial Narrow", sans-serif; --body: "Public Sans", -apple-system, "Helvetica Neue", Arial, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #111113; --surface: #1b1b1e; --ink: #f2f2ee; --muted: #a3a4ab; --line: #303035; --ok: #4cc584; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #111113; --surface: #1b1b1e; --ink: #f2f2ee; --muted: #a3a4ab; --line: #303035; --ok: #4cc584; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font: 400 15px/1.5 var(--body); }
.wrap { max-width: 980px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 20px 120px; display: grid; gap: 30px; }
h1, h2 { font-family: var(--display); font-weight: 700; line-height: 1.02; margin: 0; text-wrap: balance; }
h1 { font-size: clamp(36px, 8vw, 56px); } h2 { font-size: 32px; }
.kicker { font: 600 12px var(--body); letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
p { margin: 0; max-width: 70ch; } .muted { color: var(--muted); }
section.reel { display: grid; gap: 14px; border-top: 2px solid var(--ink); padding-top: 16px; }
.qa { font: 500 12.5px/1.6 var(--mono); color: var(--muted); }
.qa b { color: var(--ok); font-weight: 600; }
.vers, .shots { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); }
.vers { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
figure { margin: 0; display: grid; gap: 5px; min-width: 0; }
figure img { width: 100%; height: auto; border-radius: 10px; border: 1px solid var(--line); display: block; }
figcaption { font-size: 12px; line-height: 1.35; color: var(--muted); }
figcaption b { color: var(--ink); font-family: var(--mono); font-weight: 500; font-size: 11.5px; }
.cap { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; white-space: pre-wrap; font-size: 14px; }
.calls { display: grid; gap: 10px; } .call { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.call .q { font-weight: 700; min-width: 3.2em; }
.call button { font: 600 14px var(--body); background: var(--surface); color: var(--ink); border: 1.5px solid var(--line); border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.call button[aria-pressed="true"] { background: var(--hook); color: var(--hook-ink); border-color: var(--hook); }
.call button:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.reply { position: fixed; left: 0; right: 0; bottom: 0; z-index: 3; background: var(--ink); color: var(--bg); padding-block: 10px calc(10px + env(safe-area-inset-bottom, 0px)); padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.reply .in { max-width: 980px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; }
.reply output { flex: 1 1 200px; min-width: 0; font: 500 14px var(--mono); }
.reply button { font: 700 14px var(--body); background: var(--hook); color: var(--hook-ink); border: 0; border-radius: 10px; padding: 9px 16px; cursor: pointer; }
.reply .hint { flex-basis: 100%; font-size: 12px; opacity: .75; }
"""


def cmd_page(work, out):
    """The shot-by-shot page (OB's rule: he OKs every reel's shots before anything renders): frame 0, one still per span with
    its time, layout, receipt and words, the cut checks and the post caption. Images inline; nothing renders from it."""
    import base64, html
    c = cfg(work); picks = json.load(open(os.path.join(work, "picks.json")))["reels"]
    def uri(p, w=270):
        from PIL import Image
        import io
        im = Image.open(p).convert("RGB"); im = im.resize((w, int(im.height * w / im.width))); b = io.BytesIO(); im.save(b, "JPEG", quality=78)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    lay = {"split": "split", "full": "you, full frame", "clip": "the clip, its own sound"}
    secs = []
    for r in picks:
        d = os.path.join(work, "reels", r["id"]); st = json.load(open(os.path.join(d, "stills", "stills.json"))); cut = json.load(open(os.path.join(d, "cut.json")))
        v = cut["verify"]; dd = v["dead"]; n_p = sum(len(l["pieces"]) for l in cut["lines"]); sh = st["share"]
        shots = []
        for k, row in enumerate(st["rows"]):
            mm = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
            words = html.escape((row["first"] + (" … " + row["last"] if row["last"] else "")).strip())
            what = html.escape(row["receipt"]) if row["receipt"] else ""
            note = " (a look-down at a cut)" if row["cover"] else ""
            shots.append(f'<figure><img loading="lazy" src="{uri(os.path.join(d, "stills", row["still"]))}" alt="Shot {k + 1}"><figcaption><b>{mm(row["t0"])}–{mm(row["t1"])}</b> {lay[row["state"]]}{note}'
                         f'{("<br><i>" + what + "</i>") if what else ""}<br>{words}</figcaption></figure>')
        qa = (f"{cut['duration']:.1f} s · {n_p} cuts · every cut edge in a real breath ({v.get('edges', ['?'])[0]}) · silence {dd['silent_pct']}% (longest {dd['longest_silence']} s)"
              f" · every word heard · {cut['master']['out_lufs']} LUFS, 0 clipped · split {sh['split']}%, you full frame {sh['full']}%" + (f", clip {sh['clip']}%" if sh['clip'] else "")
              + f" · {st['receipts']} receipts")
        secs.append(f"""<section class="reel" id="{r['id'].lower()}">
  <div class="kicker">{r['id']} · {html.escape(r['slug'])}</div>
  <h2>{html.escape(r.get('label', '') or r['slug'])}</h2>
  <p class="qa"><b>Cut checks passed.</b> {html.escape(qa)}</p>
  <div class="vers"><figure><img src="{uri(os.path.join(d, "stills", "f0.jpg"), 300)}" alt="Frame 0 of {r['id']}"><figcaption><b>Frame 0</b> what the feed shows first</figcaption></figure></div>
  <div class="kicker">Every span</div><div class="shots">{''.join(shots)}</div>
  <div class="kicker">Post caption</div><div class="cap">{html.escape(r['caption'])}</div>
</section>""")
    calls = "".join(f'<div class="call" data-q="{r["id"]}"><span class="q">{r["id"]}</span><button type="button" id="c_{r["id"]}_ok" data-v="OK" aria-pressed="true">Render it</button><button type="button" id="c_{r["id"]}_ch" data-v="change" aria-pressed="false">Change it</button></div>' for r in picks)
    ids = json.dumps([r["id"] for r in picks])
    PG = c.get("page") or {}   # 11-09: clipper.json "page" {title, h1, intro} replaces the 10-28 seed-oils header (defaults unchanged)
    page = f"""<title>{PG.get("title", "Seed Oils Clips Review")}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap">
<style>{PAGE_CSS}</style>
<div class="wrap">
  <header style="display:grid;gap:10px"><div class="kicker">YouTube to Reels · shot by shot · nothing rendered yet</div>
  <h1>{PG.get("h1", "Seed oils reels, rebuilt")}</h1>
  <p class="muted">{PG["intro"] if "intro" in PG else '5 reels from "How America Got Fat", rebuilt to your rules since R1 ("im not on the screen at all"). You are on screen every frame you talk. While you make a claim, its receipt fills the top: the long-form\'s own footage, the actual page with the line highlighted as you say it, or the sourced numbers. Lines with no receipt are you full frame, never stock and never a text card. Look-downs at cuts switch to the split, never a cutaway. Big Shoulders, no boxes, no black. One file per reel. Every still is a real graded frame drawn by the code that renders.'}</p></header>
  {''.join(secs)}
  <section style="display:grid;gap:12px"><h2>Your call</h2><p class="muted">Tap "Change it" on any reel you want different and tell me what (the shot time helps). Everything left on "Render it" renders behind your other edits, then goes through the QC gate (every word, every cut edge, your lips, motion, text off your face) before one file per reel lands in AirDrop.</p><div class="calls">{calls}</div></section>
</div>
<div class="reply" role="region" aria-label="Your reply"><div class="in"><output id="reply" aria-live="polite"></output><button type="button" id="copy">Copy reply</button><span class="hint" id="hint">Tap to change, then copy and paste it to me.</span></div></div>
<script>
(function () {{
  var ids = {ids}, picks = {{}}; ids.forEach(function (i) {{ picks[i] = "OK"; }});
  var out = document.getElementById("reply"), hint = document.getElementById("hint");
  function line() {{ var ch = ids.filter(function (i) {{ return picks[i] !== "OK"; }}); return ch.length ? ("Render " + ids.filter(function (i) {{ return picks[i] === "OK"; }}).join(" ") + ". Change " + ch.join(" ") + ": ") : "OK, render all {len(picks)}"; }}
  function paint() {{ document.querySelectorAll(".call").forEach(function (c) {{ var q = c.getAttribute("data-q"); c.querySelectorAll("button").forEach(function (b) {{ b.setAttribute("aria-pressed", b.getAttribute("data-v") === picks[q] ? "true" : "false"); }}); }}); out.textContent = line(); }}
  document.querySelectorAll(".call").forEach(function (c) {{ c.addEventListener("click", function (e) {{ var b = e.target.closest("button"); if (!b) return; picks[c.getAttribute("data-q")] = b.getAttribute("data-v"); paint(); }}); }});
  document.getElementById("copy").addEventListener("click", function () {{ var t = line(); function fb() {{ var r = document.createRange(); r.selectNodeContents(out); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); hint.textContent = "Selected. Copy it and paste it to me."; }}
    try {{ navigator.clipboard.writeText(t).then(function () {{ hint.textContent = "Copied: " + t; }}, fb); }} catch (e) {{ fb(); }} }});
  paint();
}})();
</script>
"""
    open(out, "w").write(page); print(out, len(page) // 1024, "KB")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(2)
    {"cut": lambda: cmd_cut(a[1], a[2:]), "words": lambda: cmd_words(a[1], a[2], a[3]), "mock": lambda: cmd_mock(a[1], a[2:]),
     "page": lambda: cmd_page(a[1], a[2]),
     "lookoff": lambda: cmd_lookoff(a[1], a[2:]),
     "qa": lambda: cmd_qa(a[1], a[2:]),
     "deliver": lambda: cmd_deliver(a[1], a[2:]),
     "review": lambda: cmd_review(a[1]),
     "render": lambda: cmd_render(a[1], [x for x in a[2:] if not x.startswith("--")], "--test" in a, "--yield" in a)}[a[0]]()
