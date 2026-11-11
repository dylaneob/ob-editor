#!/usr/bin/env python3
"""Reactions in OB's brand look (2026-10-28; OB approved the backlog reaction shot lists: "Yes, render").

One reaction = her clip's beats (her own sound, edges snapped to whole sentences) then his lines (takes.py EDL: bad takes
out, zero dead space, every word whole, the voice mastered). Brand look from ~/ob-editor/brand/brand.json: Big Shoulders,
no boxes, a soft shadow, his yellow on the word that matters, captions 3 words with the live word yellow, nothing on his face.
  vertical take   versions R (him watching, her clip in the box under the title), G (her clip full, his cutout at the bottom),
                  S (him on his phone, her words big); his lines full frame, 100/112% alternating per line. The three share
                  one body and one mix.
  horizontal take (styles/split-punch-bubble.md) her beats full frame with his face in a round bubble; his lines split
                  (her clip muted on top, him below, captions on the seam), full (punch + one big word) or bubble.
Music bed under his lines (ducked), off under her clip; ONE file (a no-music copy only with --nomusic, OB 11-03). -14 LUFS, limiter at -2 dBFS, never clipped.
Bleeps: a 1 kHz tone over the word. Every render: the QC gate with every piece (his mic, her source) and his script.
Waits for any other render on the Mac (one at a time); its own name keeps "react_render.py" visible to the other engines.

  python3 -I brand_react_render.py PLAN.json TAKE [--versions R,G,S] [--still SECONDS] [--no-wait]
"""
import io, json, math, os, re, subprocess, sys, tempfile, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
WORK = "/Volumes/T7/OB-EDITS/2026-10-28-backlog/_work"; sys.path.insert(0, WORK)
import shotlist as SL          # brand text, captions, frames (the shot lists' look)
import moves as MV             # snap, spring
import voice_master as VM
import birefnet_cut as BC      # 11-11: his cut-out is BiRefNet only (rule 9); no Apple person mask, no fallback

W, H, FPS, SR = 1080, 1920, 30000 / 1001, 48000
FFM = os.path.expanduser("~/ob-editor/bin/ffmpeg-full")
LUT = SL.LUT
MUSIC = os.environ.get("OB_MUSIC") or sys.exit("brand_react_render: no OB_MUSIC. The bed is picked, not defaulted: run music_pick.py WORK --route ROUTE, then music_pick.py apply WORK, and pass its pick as OB_MUSIC (rebuild 2026-11-10; the Funk Anthem default is gone)")   # 11-07: OB_MUSIC overrides; OB_GAP=27 puts the bed 27 LU under the voice stem; OB_FADE seconds
MUSIC_REL, MUSIC_DUCK, HER_LUFS = -19.0, 4.0, -15.0
BUBBLE_ZOOM = 2.1   # his face crop in the round bubble (OB 10-29: "make me a little bigger in the circle"; was 1.6)
OUTDIR = "/Volumes/T7/OB-EDITS/2026-10-28-backlog/finals"
POP = (320, 2 * 0.92 * 320 ** 0.5)   # 11-07: damping ratio 0.92, no bounce


# ------------------------------------------------------------------------------------------------ one at a time
def busy_renders():
    """Other renders running now (scripts by name, or any video encode that isn't ours). The clipper's yielding queue
    (ytclip --yield) waits for us, so it isn't counted unless it is encoding. Never counted: our own children, each of our
    ancestors (not their other children), and `sh -c` wrapper shells, whose children carry the real work. The shell that
    queued us on 10-29 named feed_render.py in its own wait, and this queue sat behind its own launcher 01:28-08:25."""
    names = re.compile(r"assemble\.py|hyperframes render|render_final\.sh|run_feed\.sh|feed_render\.py|tenten\d*_?\w*\.py (render|prep)|"
                       r"c43\d\d\w*\.py (render|prep)|wordsafe_c4378_edit\.py (render|prep)|render_clip\.py|lecture_render\.py|tier_render\.py|"
                       r"trial_variants\.py render|moves\.py (kick|counter|comments)|make_\w+\.py")
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines()
    rows = [(int(l.split(None, 2)[0]), int(l.split(None, 2)[1]), l.split(None, 2)[2]) for l in out if len(l.split(None, 2)) == 3]
    kids, up = {os.getpid(), os.getppid()}, {p: pp for p, pp, c in rows}
    for _ in range(4):
        kids |= {p for p, pp, c in rows if pp in kids}
    p = os.getpid()
    while p > 1 and p in up: kids.add(p); p = up[p]
    return [f"{p} ...{c[-100:]}" for p, pp, c in rows if p not in kids and not re.match(r"(\S*/)?(z|ba|da)?sh -\w*c ", c) and
            (names.search(c) or (re.match(r"\S*ffmpeg", c) and re.search(r"-c:v (libx26[45]|h264_videotoolbox|hevc_videotoolbox|prores)", c)))]


def wait_free(log=lambda m: print(m, flush=True)):
    """Wait until no other render has run for a minute (3 polls, 20 s apart)."""
    said = None; quiet = 0
    while True:
        busy = busy_renders()
        if not busy:
            quiet += 1
            if quiet >= 3: return
        else:
            quiet = 0
            if busy[0] != said: log(f"{time.strftime('%H:%M:%S')} waiting for another render to finish: {busy[0]}"); said = busy[0]
        time.sleep(20)


# ------------------------------------------------------------------------------------------------ plan
def load(plan_path, take):
    P = json.load(open(plan_path)); r = next(x for x in P["reactions"] if x["take"] == take)
    E = json.load(open(f"{WORK}/{take}_edl.json")); A = json.load(open(f"{WORK}/{take}_apple_words.json"))
    # a talking head (10-29: C4361, C4362) has no reacted-to clip: no source, no her beats, his lines only
    src_words = [] if not r.get("source") else next(json.load(open(f"{WORK}/{f}"))["words"] for f in sorted(os.listdir(WORK)) if re.match(r"src\d+_words\.json$", f)
                     and json.load(open(f"{WORK}/{f}"))["file"] == r["source"])
    return r, E, A, src_words


def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())


def watch_offset(A, S):
    """Take time minus source time while her clip plays in the room (matched words, median)."""
    import difflib
    a, b = [norm(x["w"]) for x in A], [norm(x["w"]) for x in S]; d = []
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        if blk.size >= 3: d += [A[blk.a + k]["s"] - S[blk.b + k]["s"] for k in range(blk.size)]
    return float(np.median(d)) if d else 0.0


_ENV = {}


_SPENV = {}


def gate_edge_ok(src, e, t, side):
    """qc_gate.c_edges' own test for one piece edge, kept identical: the 0.1 s outside it (before a start, after an end) under
    max(floor + 6, p90 - 25) of the 2 s around it, or a clean valley between two words (qc_gate.valley_cut)."""
    import zero_dead as Z, qc_gate as Q
    e = _SPENV.setdefault(src, Q.speech_env(src))   # 11-07: the gate's own envelope and margin (it was tightened after 10-29: C4397's edges failed)
    i = int(round(t / Z.HOP)); w = e[max(0, i - 100):i + 100]
    if len(w) < 10: return True
    Pl = float(np.percentile(w, 90)); o = e[max(0, i - 10):i] if side == "starts" else e[i:i + 10]
    lv = float(20 * np.log10(np.mean(10 ** (o / 20)) + 1e-9)) if len(o) else -120.0
    floor = float(np.percentile(e[max(0, i - 300):i + 300], 10))
    return lv <= max(floor + Q.EDGE_FLOOR_MARGIN, Pl - 25) or Q.valley_cut(src, e, t)


def her_pieces(src, a, b):
    """Her beat as pieces. a and b are picked by hand at her sentence edges and proved by ear-equivalent (_work/her_check.py
    transcribes every cut beat): the reel's own word times can't place them (Apple put "For 43%" 1.6 s late in C4364's clip,
    and the first render cut in at 2.92 s, mid-sentence). Each edge snaps to the nearest point within 80 ms that passes the
    QC gate's own edge test, outward first. Inside, every pause is cut where both new edges pass that test: digital silence
    (her editor's jump cuts) of 0.10 s+ keeping 0.02 s each side, and dead air (20 dB under her speech) of 0.25 s+ keeping
    0.04 s each side."""
    import zero_dead as Z
    if src not in _ENV: _ENV[src] = Z.level_env(src)
    e = _ENV[src]; HOP = Z.HOP; n = len(e); i = lambda t: max(0, min(n - 1, int(round(t / HOP))))
    def snap(t, side):
        out = -1 if side == "starts" else 1
        for d in sorted(range(-8, 9), key=lambda d: (abs(d), -d * out)):
            u = round(t + d * HOP, 3)
            if 0 <= u <= n * HOP and gate_edge_ok(src, e, u, side): return u
        return None
    st, en = snap(a, "starts"), snap(b, "ends")
    if st is None or en is None: raise SystemExit(f"her beat {a}-{b} in {os.path.basename(src)}: no clean {'start' if st is None else 'end'} within 80 ms")
    P = float(np.percentile(e[i(st):i(en)], 90)); pieces, cur, k = [], st, i(st) + 1
    def runs(k0, k1, lim):
        out, k = [], k0
        while k < k1:
            if e[k] <= lim:
                j = k
                while j < k1 and e[j] <= lim: j += 1
                out.append((k, j)); k = j
            else: k += 1
        return out
    for k, j in runs(i(st) + 1, i(en) - 1, P - 20):
        # a dead run of 0.25 s+ goes whole; failing that (or shorter), the silences inside it of 0.10 s+ (a soft word tail
        # can lead into one, as before C4364's "No!", so the run as a whole is not silent)
        tries = [[(k * HOP + 0.04, j * HOP - 0.04)]] if (j - k) * HOP >= 0.25 else []
        tries.append([(m * HOP + 0.02, q * HOP - 0.02) for m, q in runs(k, j, P - 32) if (q - m) * HOP >= 0.10])
        for cuts in tries:
            ok = [(round(ca, 3), round(cb, 3)) for ca, cb in cuts if cb - ca >= 0.03 and ca - cur >= 2 / FPS
                  and gate_edge_ok(src, e, round(ca, 3), "ends") and gate_edge_ok(src, e, round(cb, 3), "starts")]
            if ok:
                for ca, cb in ok:
                    if ca - cur >= 2 / FPS: pieces.append((cur, ca)); cur = cb
                break
    pieces.append((cur, en))
    return [(x, y) for x, y in pieces if y - x >= 2 / FPS]


def timeline(r, E, A, S):
    """[(seg dict)] in order with t0 (output start)."""
    take, hz = r["take"], r["horizontal"]; segs = []; off = watch_offset(A, S); t = 0.0
    cams = r.get("watch_cam")   # his reaction picked by frame, one start per beat (OB 10-30, C4371: a song-only reel has no words to
    # match, so the word offset landed on him talking: "you didnt need to cut me reacting it was perfect"; ledger M34)
    for j, (a, b, say) in enumerate(r["her"]):   # a reel that is only a song (C4371) has no words to cut around: its beats play whole
        for a2, b2 in ([(a, b)] if r.get("her_audio") == "music" else her_pieces(r["source"], a, b)):
            c0 = cams[j] + a2 - a if cams else a2 + off
            segs.append(dict(kind="her", a=a2, b=b2, cam=(c0, c0 + b2 - a2), say=say, t0=t)); t += b2 - a2
    n = 0; her_end = segs[-1]["b"] if segs else 0.0
    for l in E["lines"]:
        spec = r["lines"].get(l["id"], {})
        if spec.get("drop"): continue
        look = spec.get("look", "split" if hz else "full"); punch = 1.0; n += 1   # 11-07 OB: no zooming in or out, no punch-ins
        for k, (a, b) in enumerate(l["pieces"]):
            segs.append(dict(kind="ob", line=l["id"], text=l["text"], a=a, b=b, look=look, punch=punch, spec=spec, first=k == 0,
                             last=k == len(l["pieces"]) - 1, t0=t)); t += b - a
    # the file ends on his room tone (2026-10-29): a last word that runs to the cut (the "-ce" of C4380's "advice.") left the
    # file's last 45 ms at speech level for the gate, and the AAC mux trims up to 21 ms more; take up to 0.25 s of the pause after it
    if segs and segs[-1]["kind"] == "ob":
        import zero_dead as Z
        mic = f"{WORK}/{take}_mic.wav"
        if mic not in _ENV: _ENV[mic] = Z.level_env(mic)
        e = _ENV[mic]; s = segs[-1]; i = int(round(s["b"] / Z.HOP)); P = float(np.percentile(e[max(0, i - 200):i], 90))
        for tail in (0.25, 0.2, 0.15, 0.1):
            j = int(round((s["b"] + tail) / Z.HOP))
            if j + 10 < len(e) and e[i + 3:j].max() <= P - 30 and gate_edge_ok(mic, e, round(s["b"] + tail, 3), "ends"):
                s["b"] = round(s["b"] + tail, 3); break
    # frames from the running total of exact times (2026-10-29): rounding each piece on its own let the picture drift off the
    # sound by up to 66 ms (C4364 at 9.4 s, sound early). Each piece's sound sits at its exact t0; its frames now start within
    # half a frame of it, and the last piece gets a frame more if needed so the picture is never shorter than the sound.
    for s in segs:
        f0, f1 = int(round(s["t0"] * FPS)), int(round((s["t0"] + s["b"] - s["a"]) * FPS)); s["n"] = max(1, f1 - f0)
    if segs:
        end = segs[-1]["t0"] + segs[-1]["b"] - segs[-1]["a"]
        while sum(s["n"] for s in segs) / FPS < end: segs[-1]["n"] += 1
    return segs, off


# ------------------------------------------------------------------------------------------------ pixels
def decode(path, start, n, size, lut=False, crop=None):
    """n frames from path at start, as RGB arrays of size; crop=(w, h, x, y) in source pixels first."""
    vf = (f"crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]}," if crop else "") + \
         f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase:flags=lanczos,crop={size[0]}:{size[1]},fps=30000/1001,format=rgb24"
    if lut:
        cmd = [FFM, "-nostdin", "-v", "error", "-ss", f"{start:.4f}", "-i", path, "-i", LUT, "-filter_complex", f"[0:v]{vf}[s];[s][1:v]haldclut",
               "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    else:
        cmd = [FFM, "-nostdin", "-v", "error", "-ss", f"{start:.4f}", "-i", path, "-vf", vf, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE); fb = size[0] * size[1] * 3; got = 0; last = None
    while got < n:
        b = p.stdout.read(fb)
        if len(b) < fb: break
        last = Image.frombytes("RGB", size, b); got += 1; yield last
    p.stdout.close(); p.wait()
    while got < n and last is not None: got += 1; yield last   # hold the last frame if the source ends early


def cam_info(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                       capture_output=True, text=True).stdout
    st = json.loads(o)["streams"][0]; w, h = st["width"], st["height"]
    rot = next((abs(int(sd.get("rotation", 0))) for sd in st.get("side_data_list", []) if "rotation" in sd), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def face_of(img):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.png"); img.save(p)
        o = subprocess.run([os.path.expanduser("~/ob-editor/bin/faces"), p], capture_output=True, text=True).stdout.split()
    return tuple(int(v) for v in o[1:5]) if len(o) >= 5 and o[1] != "none" else None


def hz_crop(cam, t, aspect, scale=1.0):
    """For a horizontal 4K take: the source crop (w, h, x, y) of the given aspect (w/h) around his face, his face ~30% down."""
    full = next(decode(cam, t, 1, cam_info(cam), lut=False)); fb = face_of(full); cw0, ch0 = full.size
    ch = min(int(ch0 / scale), ch0); cw = int(ch * aspect)   # never bigger than the frame (a split's 0.85 zoom-out asked for 2541 of 2160)
    if cw > cw0: cw = cw0; ch = int(cw / aspect)
    cx = (fb[0] + fb[2]) / 2 if fb else cw0 / 2; fy = fb[1] if fb else ch0 * 0.2
    x = int(min(max(0, cx - cw / 2), cw0 - cw)); y = int(min(max(0, fy - ch * 0.24), ch0 - ch))
    return (cw // 2 * 2, ch // 2 * 2, x // 2 * 2, y // 2 * 2)


def punch_img(im, p):
    if p == 1.0: return im
    w, h = int(W / p), int(H / p); x0 = (W - w) // 2; y0 = int((H - h) * 0.35)
    return im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.LANCZOS)


CUT_LOG = []   # 11-11: what cut him out, per piece (written to WORK/qc/matte.json when OB_WORK names a WORK off the T7)


def cutouts(frames, td, src=None, t0=0.0, n_want=0, look=""):
    """His cut-out, streamed through disk: BiRefNet mattes from birefnet_cut.py (cached; 11-11, rule 9: never Apple's person mask)."""
    BC.check()
    fd, md = os.path.join(td, "f"), os.path.join(td, "m"); os.makedirs(fd, exist_ok=True); os.makedirs(md, exist_ok=True); n = 0
    for k, im in enumerate(frames): im.save(f"{fd}/{k:05d}.png", compress_level=1); n += 1
    lm = os.path.getmtime(LUT) if os.path.exists(str(LUT)) else 0
    st = {"src": src or "unknown", "t0": t0, "n": n, "fps": FPS, "size": (540, 960), "look": f"brand_react decode {look} lut={LUT}@{lm:.0f}",
          "frames": [f"{fd}/{k:05d}.png" for k in range(n)]}
    CUT_LOG.append(BC.masks([st], md, td, work=BC.find_work(None, None)))


def record_cuts(plan_path):
    """After a render: what cut him out goes to WORK/qc/matte.json (OB_WORK, never the T7), so the gate reads the engine, not the editor."""
    if not CUT_LOG: return
    i0 = dict(CUT_LOG[0]); i0["stretches"] = [x for i in CUT_LOG for x in i["stretches"]]
    for k in ("frames", "computed", "cached"): i0[k] = sum(i[k] for i in CUT_LOG)
    rp = BC.record(BC.find_work(None, None), "brand_react_render.py", plan_path, i0, ["green"]); CUT_LOG.clear()
    print(f"  matte record: {rp}" if rp else "  matte record: none (set OB_WORK to the job's WORK folder; declare matte birefnet in the manifest)", flush=True)
    for k in range(n):
        im = Image.open(f"{fd}/{k:05d}.png").convert("RGBA"); m = Image.open(f"{md}/{k:05d}.png").convert("L").resize(im.size); im.putalpha(m); yield im


# ------------------------------------------------------------------------------------------------ text layers (made once, composited per frame)
def text_layer(fn, *args, **kw):
    """Render a shotlist text call onto a transparent layer: draw it over pure black and pure white, recover alpha + color."""
    k = Image.new("RGB", (W, H), (0, 0, 0)); w = Image.new("RGB", (W, H), (255, 255, 255))
    out = fn(k, *args, **kw); fn(w, *args, **kw)
    ka, wa = np.asarray(k).astype(np.float32), np.asarray(w).astype(np.float32)
    alpha = np.clip(1.0 - (wa - ka).mean(2) / 255.0, 0, 1)
    rgb = np.where(alpha[..., None] > 1e-3, ka / np.maximum(alpha[..., None], 1e-3), 0)
    L = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    return L, out


def pop(L, age, anchor_y):
    """POP spring in: 0.82 -> 1.0 scale over the first ~0.3 s, around the layer's content centre."""
    s = 0.82 + 0.18 * min(1.0, MV.spring(age, POP)) if age < 0.45 else 1.0
    if s >= 0.999: return L
    bb = L.getbbox()
    if not bb: return L
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2; part = L.crop(bb); nw, nh = max(1, int(part.width * s)), max(1, int(part.height * s))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(part.resize((nw, nh), Image.LANCZOS), (int(cx - nw / 2), int(cy - nh / 2))); return out


def chunks(words):
    """[(word, t0, t1)] -> caption chunks of 3 words: [(t0, t1, [(word, t0, t1)...])]."""
    out = []
    for k in range(0, len(words), 3):
        grp = words[k:k + 3]; out.append((grp[0][1], words[k + 3][1] if k + 3 < len(words) else grp[-1][2] + 0.25, grp))
    return out


def caption_layer(grp, live, y):
    """3 words, the live one yellow (brand caption)."""
    ws = [w for w, a, b in grp]; d = ImageDraw.Draw(Image.new("RGB", (8, 8))); f = SL.font(88, SL.BRAND["caption"]["weight"]); tr = SL.BRAND["caption"]["tracking_em"] * 88; gap = 26
    U = [w.upper() for w in ws]; tw = sum(SL.tracked_len(d, w, f, tr) for w in U) + gap * (len(U) - 1); x = (W - tw) / 2; runs = []
    for k, w in enumerate(U):
        runs.append((x, y, w, f, SL.YEL if k == live else (255, 255, 255), tr)); x += SL.tracked_len(d, w, f, tr) + gap
    L, _ = text_layer(lambda im: SL.put(im, runs, stroke=2)); return L


_LW = {}


def align_words(disp, toks, a0, b0):
    """[(word, (t0, t1))] for display words over [a0, b0]: matched to the ASR's tokens, a replaced run spread evenly over its
    tokens, and words with no heard token between their neighbours."""
    import difflib
    sm = difflib.SequenceMatcher(None, [norm(d) for d in disp], [norm(x["w"]) for x in toks], autojunk=False); tm = [None] * len(disp)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1): tm[i1 + k] = (max(toks[j1 + k]["s"], a0), min(toks[j1 + k]["e"], b0))
        elif op == "replace":
            s0, s1 = max(toks[j1]["s"], a0), min(toks[j2 - 1]["e"], b0); m = i2 - i1
            for k in range(m): tm[i1 + k] = (s0 + (s1 - s0) * k / m, s0 + (s1 - s0) * (k + 1) / m)
    for k in range(len(disp)):
        if tm[k] is None:
            prev = next((tm[j][1] for j in range(k - 1, -1, -1) if tm[j]), a0); nxt = next((tm[j][0] for j in range(k + 1, len(disp)) if tm[j]), b0)
            tm[k] = (prev, max(prev + 0.05, nxt))
    return list(zip(disp, tm))


def placed_words(wt, pieces, seg):
    """The words of wt this seg shows, as [(word, t_out0, t_out1)]. A word's piece holds its midpoint; when that falls between
    two pieces, its end, then its start (Apple starts words early over the cut pause: C4380's "they" ran 230.82-233.34 across
    a 2 s cut, sat in neither piece, and the caption lost it, 10-29)."""
    def here(t0, t1):
        for x in ((t0 + t1) / 2, t1, t0):
            if any(p - 0.02 <= x < q for p, q in pieces): return seg["a"] - 0.02 <= x < seg["b"]
        return False
    return [(w, seg["t0"] + max(t0, seg["a"]) - seg["a"], seg["t0"] + min(t1, seg["b"]) - seg["a"]) for w, (t0, t1) in wt if here(t0, t1)]


def display_words(text):
    return [re.sub(r"^f+u+c+k", "F**K", w, flags=re.I) for w in re.sub(r"[,.?!]", "", text).split()]


def line_words(seg, A, lines):
    """His words in this piece as [(word, t_out0, t_out1)]: the line's display words (its script text, his real words)
    aligned once to Apple's words over the whole line."""
    lid = seg["line"]
    if lid not in _LW:
        L = lines[lid]; a0, b0 = L["pieces"][0][0], L["pieces"][-1][1]
        _LW[lid] = align_words(display_words(L["text"]), [x for x in A if x["e"] > a0 - 0.05 and x["s"] < b0 + 0.05], a0, b0)
    return placed_words(_LW[lid], lines[lid]["pieces"], seg)


def lost_words(segs, A, lines):
    """His display words that no piece shows: [(line, [words])]. A render with any stops before it starts."""
    shown = {}
    for s in segs:
        if s["kind"] == "ob": shown.setdefault(s["line"], []).extend(w for w, a, b in line_words(s, A, lines))
    out = []
    for lid, got in shown.items():
        miss = [w for w, _ in _LW[lid]]
        for w in got:
            if w in miss: miss.remove(w)
        if miss: out.append((lid, miss))
    return out


# ------------------------------------------------------------------------------------------------ audio
def pcm(path, a, b):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                                      "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
    n = int(round((b - a) * SR)); return np.pad(x, (0, max(0, n - len(x))))[:n]


def lufs(x):
    import voice_master as V
    return V.lufs(np.stack([x, x], 1), SR)["I"]


def bleep(x, a, b, level=None):
    """A 1 kHz tone over x[a:b] (samples), 10 ms fades, at the speech level around it."""
    a, b = max(0, a), min(len(x), b)
    if b <= a: return
    rms = level if level else float(np.sqrt(np.mean(x[max(0, a - SR // 2):min(len(x), b + SR // 2)] ** 2)) + 1e-6)
    t = np.arange(b - a) / SR; tone = np.sin(2 * np.pi * 1000 * t) * rms * 1.2; f = min(int(0.01 * SR), (b - a) // 2)
    env = np.ones(b - a); env[:f] = np.linspace(0, 1, f); env[-f:] = np.linspace(1, 0, f); x[a:b] = x[a:b] * (1 - env) + tone * env


def build_audio(r, segs, A, mic, out_wav):
    """Her sound under her beats, his mastered voice under his lines, the bed ducked under him and off under her."""
    import scipy.io.wavfile as wf
    from music_bed import long_bed
    from music_mix import lufs_of
    # as long as the picture (which is never shorter than the sound); each piece's sound at its exact place and length, so it
    # never reads past its clean edge (the old frame-rounded length ran up to 17 ms past b, or stopped up to 17 ms short of it)
    N = int(round(sum(s["n"] for s in segs) / FPS * SR)); voice, herp = np.zeros(N), np.zeros(N); lines = []; f5 = int(0.005 * SR)
    for j, s in enumerate(segs):
        o0 = int(round(s["t0"] * SR)); L = min(int(round((s["b"] - s["a"]) * SR)), N - o0)
        if s["kind"] == "her":
            g = pcm(r["source"], s["a"], s["a"] + L / SR)
            # 10 ms edge fades (no click, no bitten word); 30 ms at the very start of the file, where her reel may open at full
            # level (C4396 starts on "I'm" at once) and the gate wants a start that rises into the first word
            fi, fo = int((0.03 if j == 0 else 0.01) * SR), int(0.01 * SR)
            if r.get("her_audio") == "music": fi = fo = int(0.15 * SR)   # a song cut mid-bar fades
            g[:fi] *= np.linspace(0, 1, fi); g[-fo:] *= np.linspace(1, 0, fo)
            for w0, w1 in r.get("bleep_her", []):
                if s["a"] <= w0 < s["b"]: bleep(g, int((w0 - s["a"]) * SR), int((w1 - s["a"]) * SR))
            herp[o0:o0 + L] = g[:L]
        else:
            g = pcm(mic, s["a"], s["a"] + L / SR)
            prv, nxt = (segs[j - 1] if j else None), (segs[j + 1] if j + 1 < len(segs) else None)
            if not (prv and prv["kind"] == "ob" and abs(prv["b"] - s["a"]) < 0.002): g[:f5] *= np.linspace(0, 1, f5)
            if not (nxt and nxt["kind"] == "ob" and abs(s["b"] - nxt["a"]) < 0.002): g[-f5:] *= np.linspace(1, 0, f5)
            for lid, w0, w1 in r.get("bleep_ob", []):
                if lid == s["line"] and s["a"] <= w0 < s["b"]: bleep(g, int((w0 - s["a"]) * SR), int((w1 - s["a"]) * SR))
            voice[o0:o0 + L] = g[:L]
            if lines and lines[-1][2] == s["line"]: lines[-1][1] = o0 + L
            else: lines.append([o0, o0 + L, s["line"]])
    vm, rep = VM.master(voice, SR, -14.0, [(a, b) for a, b, _ in lines]); v = vm[:, 0]
    gh = 10 ** ((HER_LUFS - 3.01 - lufs(herp)) / 20) if np.abs(herp).max() > 0 else 0.0
    env = np.ones(N)
    for s in segs:
        if s["kind"] == "her": env[int(round(s["t0"] * SR)):int(round((s["t0"] + s["b"] - s["a"]) * SR))] = 0.0
    k = int(0.15 * SR); env = np.convolve(env, np.ones(k) / k, mode="same")   # 150 ms ramps at the edges
    # the bed goes out under his last word: un-ducking after it, it swelled back up and the file ended mid-swell (C4380 R's
    # gate, 10-29: "ends mid-word", -24 dB in the last 45 ms)
    fo = min(N, int(float(os.environ.get('OB_FADE', 0.4)) * SR)); env[N - fo:] *= np.linspace(1, 0, fo)
    outs = {}
    for name, track in (("music", MUSIC), ("nomusic", None)):
        mix = np.stack([v + herp * gh] * 2, 1)
        if track:
            bed = long_bed(track, v, SR, MUSIC_REL, MUSIC_DUCK)[:N]
            if os.environ.get("OB_GAP"):   # 11-07 OB: bed stem GAP LU under the voice stem (his voice + hers), integrated LUFS
                vs_ = np.stack([v + herp * gh] * 2, 1); gap0 = lufs_of(vs_, SR) - lufs_of(bed * env[:, None], SR); bed = bed * 10 ** ((gap0 - float(os.environ["OB_GAP"])) / 20)
                print(f"   music pass: gap was {gap0:.2f} LU -> now {lufs_of(vs_, SR) - lufs_of(bed * env[:, None], SR):.2f} LU", flush=True)
            mix = mix + bed * env[:, None]
        mix *= 10 ** ((-14.0 - lufs_of(mix, SR)) / 20)
        tmp = out_wav.replace(".wav", f"_{name}_raw.wav"); wf.write(tmp, SR, mix.astype(np.float32))   # float: never clipped before the limiter
        fin = out_wav.replace(".wav", f"_{name}.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", tmp, "-af", "aresample=192000,alimiter=limit=0.794:attack=1:release=50:level=false,aresample=48000",
                        "-c:a", "pcm_s24le", fin], check=True); outs[name] = fin
    print(f"   voice {rep['in_lufs']} -> {rep['out_lufs']} LUFS (rows {rep['line_gains_db']} dB, limiter p99 {rep['limiter']['p99']} dB, clipped {rep['clipped_samples']})", flush=True)
    return outs


# ------------------------------------------------------------------------------------------------ video
STOCK = "/Volumes/OB-ARCHIVE/OB-EDITS/stock/pexels"   # stock_pexels.py downloads
_nrm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


class TopReader:
    """One shot for the split's top half (W x 960), read in order, re-seeking only on a jump; y = where the 960 band sits in
    a frame taller than that (0 top, 1 bottom)."""
    def __init__(self, path, y=0.5):
        self.path, self.y, self.p, self.pos, self.last = path, y, None, -1, None

    def frame(self, t):
        idx = max(0, int(round(t * FPS))); nb = W * 960 * 3
        if self.p is None or idx < self.pos or idx > self.pos + 4:
            self.close()
            vf = f"scale={W}:960:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:960:(iw-{W})/2:(ih-960)*{self.y:.3f},fps=30000/1001,format=rgb24"
            self.p = subprocess.Popen([FFM, "-nostdin", "-v", "error", "-stream_loop", "-1", "-ss", f"{idx / FPS:.4f}", "-i", self.path, "-vf", vf,
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE); self.pos = idx - 1
        while self.pos < idx:
            b = self.p.stdout.read(nb)
            if len(b) < nb: break
            self.last = Image.frombytes("RGB", (W, 960), b); self.pos += 1
        return self.last

    def close(self):
        if self.p: self.p.kill(); self.p.wait(); self.p = None


class Composer:
    def __init__(self, r, segs, A, S, version, E):
        self.r, self.segs, self.A, self.S, self.v = r, segs, A, S, version; self.cam = f"/Volumes/T7/{r['take']}.MP4"
        self.hz = r["horizontal"]; self.cache = {}; self.lines = {l["id"]: l for l in E["lines"]}
        self._tplan, self._tops, self._tline = {}, {}, None

    def _top_plan(self, lid):
        """The split line's top-half shots, [(t_out, path, in, y)]: each starts on its cue word (or the line's start). Plan "top":
        [{"src": "pexels:ID" | "her" | path, "in": s, "at": word, "nth": n, "y": 0..1}]."""
        if lid in self._tplan: return self._tplan[lid]
        segs = [x for x in self.segs if x["kind"] == "ob" and x["line"] == lid]
        words = [w for x in segs for w in line_words(x, self.A, self.lines)]; out = []
        for e in self.r["lines"][lid]["top"]:
            src = self.r["source"] if e["src"] == "her" else f"{STOCK}/{e['src'][7:]}.mp4" if e["src"].startswith("pexels:") else e["src"]
            if not os.path.exists(src): raise SystemExit(f"{lid}: top shot {src} is missing")
            t = segs[0]["t0"]
            if e.get("at"):
                hits = [a for w, a, b in words if _nrm(w) == _nrm(e["at"])]
                if len(hits) <= e.get("nth", 0): raise SystemExit(f"{lid}: top cue word {e['at']!r} is not in the line")
                t = max(t, hits[e.get("nth", 0)] - 0.05)
            out.append((t, src, float(e.get("in", 0.0)), float(e.get("y", 0.5))))
        self._tplan[lid] = sorted(out); return self._tplan[lid]

    def top_frames(self, s):
        """OB 10-30 on the split reactions: "you were suppose to have relevant split screen", "not just through the orginal reaction
        above me", "you were suppose to find relevant things like you do for youtube": the line's own shots on top, a slow push on each."""
        plan = self._top_plan(s["line"])
        if self._tline != s["line"]:
            for rd in self._tops.values(): rd.close()
            self._tops, self._tline = {}, s["line"]
        for k in range(s["n"]):
            t = s["t0"] + k / FPS; st, path, tin, y = [x for x in plan if x[0] <= t + 1e-6][-1] if t >= plan[0][0] - 1e-6 else plan[0]
            dt = max(0.0, t - st); im = self._tops.setdefault((path, tin, y), TopReader(path, y)).frame(tin + dt)
            z = 1.0   # 11-07 no zooming (was a 5% push over 3 s)
            if z > 1.001:
                cw, ch = W / z, 960 / z; im = im.crop((int((W - cw) / 2), int((960 - ch) / 2), int((W + cw) / 2), int((960 + ch) / 2))).resize((W, 960), Image.BILINEAR)
            yield im

    def her_words(self, s):
        """Her words in this piece as [(word, t_out0, t_out1)]: her beat's checked text (plan "her") aligned to her clip's ASR
        words (srcN_words.json: 93% of its word time is speech, against 86% for whisper's word list, 10-29)."""
        beat = next((b for b in self.r["her"] if b[0] - 0.05 <= s["a"] and s["b"] <= b[1] + 0.05), None)
        if beat is None: return []
        key = ("herwords", beat[0])
        if key not in self.cache:
            self.cache[key] = align_words(display_words(beat[2]), [x for x in self.S if x["e"] > beat[0] - 0.05 and x["s"] < beat[1] + 0.05], beat[0], beat[1])
        pieces = [(x["a"], x["b"]) for x in self.segs if x["kind"] == "her" and beat[0] - 0.05 <= x["a"] and x["b"] <= beat[1] + 0.05]
        return placed_words(self.cache[key], pieces, s)

    def her_frames(self, s, size, start=None, n=None):
        return decode(self.r["source"], s["a"] if start is None else start, n or s["n"], size)

    def ob_frames(self, s, size=(W, H), span=None, scale=1.0, aspect=None):
        a = span[0] if span else s["a"]
        if self.hz:
            crop = hz_crop(self.cam, a + 0.2, aspect or size[0] / size[1], scale)
            return decode(self.cam, a, s["n"], size, lut=True, crop=crop)
        return (punch_img(im, s.get("punch", 1.0) if scale == 1.0 else scale) for im in decode(self.cam, a, s["n"], (W, H), lut=True))

    def line_t0(self, lid):
        return next(x["t0"] for x in self.segs if x["kind"] == "ob" and x["line"] == lid)

    def broll_frames(self, s, ref):
        """ref "folder/FILE.MP4@seconds" (under /Volumes/T7 unless absolute): the clip from that second, carried on across the line's pieces."""
        f, at = ref.rsplit("@", 1); path = f if f.startswith("/") else f"/Volumes/T7/{f}"
        return decode(path, float(at) + s["t0"] - self.line_t0(s["line"]), s["n"], (W, H), lut=True)

    def segment(self, s):
        """Yield the segment's frames (RGB) with everything on it."""
        r, A = self.r, self.A
        if s["kind"] == "her":
            yield from self.her_segment(s); return
        # his lines
        look = s["look"]; spec = s["spec"]
        if look == "split":
            her_t = (s["t0"] * 0.37) % max(1.0, r["her"][-1][1])   # her clip, muted, keeps moving on top, unless the line has its own shots
            tops = self.top_frames(s) if spec.get("top") else decode(r["source"], her_t, s["n"], (W, 960)); bots = self.ob_frames(s, (W, 960), aspect=W / 960, scale=0.85)
            base = (self._stack(t, b) for t, b in zip(tops, bots)); cap_y = 900; text_top = None
        elif look == "bubble":
            her_t = (s["t0"] * 0.37) % max(1.0, r["her"][-1][1])
            base = (self._bubble(h, f) for h, f in zip(decode(r["source"], her_t, s["n"], (W, H)), self.ob_frames(s, (600, 600), aspect=1.0, scale=BUBBLE_ZOOM)))
            cap_y = 1250; text_top = None
        else:
            if spec.get("broll") and not self.hz: base = self.broll_frames(s, spec["broll"])   # his own b-roll over the line (talking heads)
            elif spec.get("dms") and not self.hz:   # the DM flash: each DM full width over him blurred, 0.3 s each (the brand's DM beat)
                t_l = self.line_t0(s["line"]); n_dm = len(SL.dm_files())
                base = (SL.dm_flash(im, int((s["t0"] + k / FPS - t_l) / 0.3) % n_dm) for k, im in enumerate(self.ob_frames(s)))
            else: base = self.ob_frames(s, scale=s.get("punch", 1.0)) if self.hz else self.ob_frames(s)
            cap_y = None
        words = line_words(s, A, self.lines); chunk = chunks(words)
        for k, im in enumerate(base):
            t = s["t0"] + k / FPS
            if cap_y is None:   # full frame: text from 60 px under his chin, captions under the text
                if "face" not in s: s["face"] = face_of(im)
                top = (s["face"][3] + 60) if s.get("face") else 820; cap_y = 1200
                for key in ("word", "text"):
                    if spec.get(key):
                        lk = (s["line"], key)
                        if lk not in self.cache:
                            L, bottom = text_layer(lambda img: SL.brand_text(img, spec[key], top, spec.get("label") if key == "text" else None,
                                                                             spec.get("size", 190 if key == "word" else 150)))
                            self.cache[lk] = L; self.cache[lk + ("t0",)] = s["t0"]; self.cache[lk + ("bottom",)] = bottom
                        cap_y = max(cap_y, self.cache[lk + ("bottom",)] + 24)
                cap_y = min(cap_y, H - 420 - 110)
            if look not in ("split", "bubble"):
                for key in ("word", "text"):
                    lk = (s["line"], key)
                    if spec.get(key) and lk in self.cache:
                        im = im.convert("RGBA"); im.alpha_composite(pop(self.cache[lk], t - self.cache[lk + ("t0",)], 0)); im = im.convert("RGB")
            for c0, c1, grp in chunk:
                if c0 - 0.02 <= t < c1:
                    live = max([i for i, (w, a, b) in enumerate(grp) if a <= t + 0.02] or [0])
                    key = ("cap", grp[0][1], live, cap_y)
                    if key not in self.cache: self.cache[key] = caption_layer(grp, live, cap_y)
                    im = im.convert("RGBA"); im.alpha_composite(self.cache[key]); im = im.convert("RGB"); break
            yield im

    def _stack(self, top, bot):
        im = Image.new("RGB", (W, H)); im.paste(top, (0, 0)); im.paste(bot, (0, 960)); return im

    def _bubble(self, her, face):
        d = 280; m = Image.new("L", (d, d), 0); ImageDraw.Draw(m).ellipse([0, 0, d - 1, d - 1], fill=255)
        f = face.resize((d, d), Image.LANCZOS).convert("RGBA"); f.putalpha(m); b = her.convert("RGBA"); b.alpha_composite(f, (70, 240)); return b.convert("RGB")

    def her_segment(self, s):
        r = self.r; v = self.v; cam_span = s["cam"]
        if self.hz:   # her clip full frame, his face in the bubble, watching; her words captioned like his (OB 10-29: "Caption hers")
            faces = self.ob_frames(s, (600, 600), span=cam_span, aspect=1.0, scale=BUBBLE_ZOOM)
            chunk = chunks(self.her_words(s)); cap_y = None
            for k, (h, f) in enumerate(zip(self.her_frames(s, (W, H)), faces)):
                if cap_y is None:   # under her chin, clear of the IG band
                    fb = face_of(h); cap_y = min(max(1150, fb[3] + 50), H - 420 - 110) if fb else 1250
                im = self._bubble(h, f); t = s["t0"] + k / FPS
                for c0, c1, grp in chunk:
                    if c0 - 0.02 <= t < c1:
                        live = max([i for i, (w, a, b) in enumerate(grp) if a <= t + 0.02] or [0])
                        key = ("cap", grp[0][1], live, cap_y)
                        if key not in self.cache: self.cache[key] = caption_layer(grp, live, cap_y)
                        im = im.convert("RGBA"); im.alpha_composite(self.cache[key]); im = im.convert("RGB"); break
                yield im
            return
        if v == "G":   # her clip full frame, his watching cutout at the bottom, the title at the top
            title = self._title(240)
            with tempfile.TemporaryDirectory() as td:
                cuts = cutouts(decode(self.cam, cam_span[0], s["n"], (540, 960), lut=True), td, src=self.cam, t0=cam_span[0], look="540x960 lut=True")
                for h, c in zip(self.her_frames(s, (W, H)), cuts):
                    im = h.convert("RGBA"); cc = c.resize((760, 1351), Image.LANCZOS); im.alpha_composite(cc, ((W - 760) // 2, H - 1351 + 300)); im.alpha_composite(title); yield im.convert("RGB")
            return
        obs = decode(self.cam, cam_span[0], s["n"], (W, H), lut=True)
        first = True
        for k, (o, hfr) in enumerate(zip(obs, self.her_frames(s, (608, 1080)))):
            # 11-07 no zooming: the S 1.12 punch-in is off
            if first:
                fb = face_of(o); chin = fb[3] if fb else 760; first = False
                self.cache[("title", s["t0"])] = self._title(chin + 50)   # 11-07: no punch-in, so S needs no extra chin room
                # when he looks down at the phone (C4371 S 10-30, the gate: "SHOU" on his face at 2.5 s)
                self.cache[("tbottom",)] = getattr(self, "_tb", chin + 300)
            im = o.convert("RGBA"); im.alpha_composite(self.cache[("title", s["t0"])])
            if v == "R" or (v == "S" and r.get("sober_clip", True)):   # 11-04 default ON (OB again, C4417: "the frozen ice cream video of me reacting isnt showing the reaction")   # C4364 (OB 10-30): "there isnt the reaction on this one at all"
                y = self.cache[("tbottom",)] + 16; bh = min(1080, H - y); bw = int(bh * 9 / 16)
                im.alpha_composite(hfr.resize((bw, bh), Image.LANCZOS).convert("RGBA"), ((W - bw) // 2, y))
            if v == "S" and not r.get("sober_clip", True):   # her words, one at a time, big
                t = s["a"] + k / FPS
                # a word only if it starts inside this piece (0.25 s slack for the ASR's early starts): Apple's "For" over the intro
                # music of C4364's reel ran to 4.02 s and opened the S version (and its thumbnail) on "FOR" (10-28)
                cur = next((x for x in self.S if x["s"] <= t < x["e"] + 0.15 and x["s"] >= s["a"] - 0.25), None)
                if cur:
                    key = ("herword", cur["s"])
                    if key not in self.cache:
                        self.cache[key] = text_layer(lambda img: SL.brand_text(img, re.sub(r"[^\w'%$]", "", cur["w"]), self.cache[("tbottom",)] + 40, None, 170))[0]
                    im.alpha_composite(self.cache[key])
            yield im.convert("RGB")

    def _title(self, top):
        L, bottom = text_layer(lambda img: SL.brand_text(img, self.r["title"], top, None, 92)); self._tb = bottom; return L


def cover_spans(segs, v):
    """The gate's cover spans: her beats in the looks where her clip fills the frame (G: his cutout at the bottom; H: his face
    in the bubble). His face is off its usual spot there, so the gate must not borrow his box from a nearby frame: on C4364 G
    it borrowed the box of the man in her clip and failed her screenshot's text at 14.5 s, 280 px above his real face."""
    return [[s["t0"], s["t0"] + s["n"] / FPS] for s in segs if s["kind"] == "her"] if v in ("G", "H") else None


def render_video(comp, segs, out):
    w = subprocess.Popen([FFM, "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                          "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    total = 0
    for s in segs:
        k = 0; im = None
        for im in comp.segment(s):
            if k >= s["n"]: break
            if im.size != (W, H): im = im.resize((W, H))
            w.stdin.write(im.tobytes()); k += 1
        while k < s["n"] and im is not None: w.stdin.write(im.tobytes()); k += 1   # hold if a decoder came up short
        total += k
    w.stdin.close(); w.wait(); return total


# ------------------------------------------------------------------------------------------------ main
def main():
    a = sys.argv[1:]; plan, take = a[0], a[1]; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    r, E, A, S = load(plan, take); segs, off = timeline(r, E, A, S)
    lost = lost_words(segs, A, {l["id"]: l for l in E["lines"]})
    if r["horizontal"]:   # her captions too
        comp = Composer(r, segs, A, S, "H", E)
        for b in r["her"]:
            got = [w for s in segs if s["kind"] == "her" and b[0] - 0.05 <= s["a"] and s["b"] <= b[1] + 0.05 for w, x, y in comp.her_words(s)]
            miss = display_words(b[2])
            for w in got:
                if w in miss: miss.remove(w)
            if miss: lost.append((f"her {b[0]}", miss))
    if lost: raise SystemExit(f"{take}: caption words in no piece, in lines {[lid for lid, _ in lost]}: {lost}")
    versions = (opt("--versions") or r.get("versions") or ("T" if not r["her"] else "S" if not r["horizontal"] else "H")).split(",")   # 11-04 OB: "only 1 is needed we arent doing the variations anymore"
    print(f"{take}: {len(segs)} pieces, {segs[-1]['t0'] + segs[-1]['n'] / FPS:.1f} s; her clip in the room at {off:+.2f} s; versions {versions}", flush=True)
    if opt("--still") is not None:   # one composed frame per version at an output time, for checking
        t = float(opt("--still")); s = next(x for x in segs if x["t0"] <= t < x["t0"] + x["n"] / FPS)
        for v in versions:
            comp = Composer(r, segs, A, S, v, E); k = int((t - s["t0"]) * FPS)
            for i, im in enumerate(comp.segment(s)):
                if i == k: im.save(f"{WORK}/still_{take}_{v}_{t:.1f}.png"); print("still", v, s["kind"], s.get("line", ""), f"{WORK}/still_{take}_{v}_{t:.1f}.png"); break
        return
    if "--remux-picture" in a:   # 11-07 no-zoom pass: re-render the picture only, mux an existing finished audio (stream copy), gate with the camera map
        aud, dst = opt("--remux-picture"), a[a.index("--remux-picture") + 2]; v = versions[0]
        if "--no-wait" not in a: wait_free()
        import qc_gate as Q
        os.makedirs(OUTDIR + "/_nozoom", exist_ok=True); vid = f"{OUTDIR}/_nozoom/_{take}_{v}.mp4"; comp = Composer(r, segs, A, S, v, E); t0 = time.time(); n = render_video(comp, segs, vid); record_cuts(plan)
        print(f"{take} {v}: {n} frames in {time.time() - t0:.0f} s", flush=True)
        if aud == "BUILD":   # the cut changed: rebuild the sound (OB_MUSIC / OB_GAP / OB_FADE set the bed) and encode it as the engine always did
            auds = build_audio(r, segs, A, f"{WORK}/{take}_mic.wav", f"{OUTDIR}/_nozoom/_{take}_mix.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", vid, "-i", auds["music"], "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac_at", "-b:a", "256k", "-shortest", "-movflags", "+faststart", dst], check=True)
        else: subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", vid, "-i", aud, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)
        script = f"{OUTDIR}/_{take}_script.txt"
        pieces = [(f"{WORK}/{take}_mic.wav", s["a"], s["b"], s["t0"]) if s["kind"] == "ob" else (r["source"], s["a"], s["b"], s["t0"]) for s in segs]
        talk = [p for p, s in zip(pieces, segs) if not (s["kind"] == "her" and r.get("her_audio") == "music")]
        cam = [(comp.cam, s["a"], s["b"], s["t0"]) for s in segs if s["kind"] == "ob"]
        Q.after_render(dst, segs=talk, script=script, cards=cover_spans(segs, v), cam=cam)
        if len(talk) < len(pieces): Q.record_pieces(dst, pieces, cam)
        print("remuxed", dst); return
    if "--no-wait" not in a: wait_free()
    os.makedirs(OUTDIR, exist_ok=True)
    name = r["name"].split(":")[0] + " " + re.sub(r"[^\w ]", "", r["name"].split(":")[1].split("(")[0]).strip()
    wav = f"{OUTDIR}/_{take}_mix.wav"; auds = build_audio(r, segs, A, f"{WORK}/{take}_mic.wav", wav)
    import qc_gate as Q
    script = f"{OUTDIR}/_{take}_script.txt"   # her words (as heard in each cut beat, her_check.py) first, then his lines
    open(script, "w").write("\n".join([w for w in r.get("her_words", []) if w] + [l["text"] for l in E["lines"] if not r["lines"].get(l["id"], {}).get("drop")]) + "\n")
    pieces = [(f"{WORK}/{take}_mic.wav", s["a"], s["b"], s["t0"]) if s["kind"] == "ob" else (r["source"], s["a"], s["b"], s["t0"]) for s in segs]
    tag = {"R": "R reacting", "G": "G green screen", "S": "S sober", "H": "split", "T": "talking head"}
    for v in versions:
        t0 = time.time(); vid = f"{OUTDIR}/_{take}_{v}.mp4"; n = render_video(Composer(r, segs, A, S, v, E), segs, vid); record_cuts(plan)
        for mixname, suffix in (("music", ""),) + ((("nomusic", " (no music)"),) if "--nomusic" in sys.argv else ()):   # M45 (OB 11-03): one file per edit
            out = f"{OUTDIR}/{name} - {tag[v]}{suffix}.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", vid, "-i", auds[mixname], "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-c:a", "aac_at", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], check=True)
            if not suffix:   # the gate checks every edge with words at it; a song-only reel's beats are recorded, not checked
                talk = [p for p, s in zip(pieces, segs) if not (s["kind"] == "her" and r.get("her_audio") == "music")]
                Q.after_render(out, segs=talk, script=script, cards=cover_spans(segs, v))
                if len(talk) < len(pieces): Q.record_pieces(out, pieces)
        print(f"{take} {v}: {n} frames in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
