#!/usr/bin/env python3
"""Three moves from the reels OB sent on 2026-10-28 (motion library §F), built after he said "Build them":
  kick      zoom kick on a stressed word: a POP-spring punch to 1.08 on his face, held 0.35 s, a SOFT-spring return
            (Adilet De4byPBoLWT "zoom kick x1.08"); on top of the static punch-in alternation, never instead of it
  counter   running total pill (Adilet's live-metric strip, made for the FDOE): "DAY SO FAR  615 kcal", a "+225" chip
            that pops when the next meal lands, and the total counting up to the new value
  comments  comment-keyword ending: an IG-style comment sheet where masked viewers comment the code, the viewer types it
            and sends, then a DM from ob_health.fit drops in with what they get (all four reels end on one). OB
            2026-10-28: "you can do fake comment section ... i dont mind that". Handles are masked ("ja•••nn") so none can
            be a real account, avatars are coloured initials (no faces, no AI people), comments are the code only.
Springs are cards.py's (stiffness, damping): POP (320, 17), SNAP (260, 22), SOFT (170, 26), SLIDE (200, 28).

  python3 -I moves.py kick IN OUT --start S --dur D --at T [--at T ...] [--audio MIC.wav] [--scale 1.08] [--hold 0.35]
  python3 -I moves.py counter IN OUT --segments S:E[,S:E] --steps T:LABEL:VALUE[,...] [--y 770]
  python3 -I moves.py comments IN OUT --start S --dur D --at T --code 631724 --dm "Here's your full gut health protocol."
                     [--box 80,230,920,412] [--avatar FACE.jpg]
All times are the input file's seconds. Every clip edge is snapped to whole words first (snap(): never inside a word; OB
2026-10-28 "stop cutting me off when im saying a word"), and the pieces go to the QC gate's word-edge check. The output is H.264 1080x1920 29.97 with AAC 256k; the kick's voice goes through
voice_master.py, the others keep the input's audio. Every render goes through the QC gate (qc_gate.after_render).
"""
import json, math, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
W, H, FPS = 1080, 1920, 30000 / 1001
HN = "/System/Library/Fonts/HelveticaNeue.ttc"; DIN = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"
POP, SNAP, SOFT, SLIDE = (320, 17), (260, 22), (170, 26), (200, 28)
YEL = (255, 212, 0)
SEGS = []   # the pieces actually used, in order: (audio, start, end), handed to the QC gate's word-edge check


def font(size, bold=True): return ImageFont.truetype(HN, size, index=1 if bold else 0)


def spring(t, kc):
    """Step response 0 -> 1 of a unit-mass spring (stiffness k, damping c) t seconds after it starts; 0 before."""
    if t <= 0: return 0.0
    k, c = kc; w0 = math.sqrt(k); z = c / (2 * w0)
    if z < 1:
        wd = w0 * math.sqrt(1 - z * z)
        return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))
    return 1 - math.exp(-w0 * t) * (1 + w0 * t)


# ------------------------------------------------------------------------------------------------ frame pipe
LUT = os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")   # the grade the 10/10 renders use (OB's pick, 10-16)


def frames(path, start, dur, size=(W, H), lut=None):
    if lut:   # graded like tenten2: bt709 in, then the Hald LUT (OB 10-28 on the zoom-kick mock: "you just didnt color grade at all")
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-i", lut, "-t", f"{dur:.3f}", "-filter_complex",
               f"[0:v]scale={size[0]}:{size[1]}:flags=lanczos:in_color_matrix=bt709:in_range=tv,format=rgb24[s];[s][1:v]haldclut,fps=30000/1001",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    else:
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-t", f"{dur:.3f}",
               "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos,fps=30000/1001", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = size[0] * size[1] * 3; k = 0
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield start + k / FPS, Image.frombytes("RGB", size, b); k += 1
    p.wait()


def writer(out_video):
    return subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", "30000/1001", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out_video], stdin=subprocess.PIPE)


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac_at", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out], check=True)


def cut_audio(path, segs, out):
    """The input's own audio for the segments, joined with 5 ms fades."""
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for k, (a, b) in enumerate(segs):
            p = os.path.join(td, f"a{k}.wav"); parts.append(p)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", path, "-vn", "-ac", "2", "-ar", "48000",
                            "-af", f"afade=t=in:d=0.005,afade=t=out:st={max(0, b - a - 0.005):.3f}:d=0.005", p], check=True)
        lst = os.path.join(td, "l.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s24le", out], check=True)


_WORDS, _ENV = {}, {}
def snap(audio, a, b):
    """(a, b) moved to whole words in `audio` (OB 2026-10-28: "stop cutting me off when im saying a word"; the first mocks cut
    clip edges by time and started and ended mid-word). The start goes to the onset of the first word that isn't over by `a`
    (20 ms before it), the end to the end of the sound of the last word that started before `b`. Never inside a word,
    never into the next or previous word. Words from Apple's speech_words, edges from zero_dead.word_core on the same audio."""
    import zero_dead as Z
    if audio not in _ENV: _ENV[audio] = Z.level_env(audio)
    env = _ENV[audio]; lo, hi = max(0.0, a - 12), b + 12; key = (audio, round(lo, 1), round(hi, 1))
    if key not in _WORDS:
        with tempfile.TemporaryDirectory() as td:
            w = os.path.join(td, "w.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-i", audio, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
            o = subprocess.run([os.path.join(BIN, "speech_words"), "words", w], capture_output=True, text=True).stdout
        _WORDS[key] = [dict(w=x["w"], s=x["s"] + lo, e=x["e"] + lo) for x in json.loads(o[o.index("["):])]
    ws = _WORDS[key]
    if not ws: return a, b
    Pat = lambda t: float(np.percentile(env[max(0, int(t / Z.HOP) - 200):int(t / Z.HOP) + 200], 90))   # his level around each edge
    P = Pat(a); A, T = P - Z.ACTIVE, P - Z.TAIL
    cores = [Z.word_core(env, w, A, T) for w in ws]   # where his sound really starts and ends (cores of joined words overlap)
    na, nb = a, b   # an edge in a pause cuts nothing: it stays where it was (the card or the moment it was picked for)
    f = next((k for k, w in enumerate(ws) if w["e"] > a), None)        # the first word not finished by a
    if f is not None:
        c = cores[f]
        if c[0] < a < c[1]:   # a cuts into it: take it whole if most of it is still to come, else start just after its sound
            na = c[0] - 0.02 if (ws[f]["e"] - a) >= (a - ws[f]["s"]) else c[1] + 0.005
        if f > 0 and cores[f - 1][1] > na: na = cores[f - 1][1] + 0.005   # never start on the tail of the word before
    l = max((k for k, w in enumerate(ws) if w["s"] < b), default=None)  # the last word that started before b
    if l is not None:
        c = cores[l]
        if c[0] < b < c[1]:   # b cuts into it: keep it whole (and anything joined to it) if most of it is in, else end before it
            nb = c[1] if (b - ws[l]["s"]) >= (ws[l]["e"] - b) else max(c[0] - 0.02, cores[l - 1][1] if l > 0 else c[0] - 0.02)
        if l + 1 < len(ws) and cores[l + 1][0] < nb and ws[l + 1]["s"] >= b: nb = min(nb, cores[l + 1][0] - 0.01)   # not into the next one
    # an edge with sound right next to it is still a chop, even between two words: "...rich in calcium and a | probiotic"
    # (C4378, 40.55 s; OB 10-28 "stop cutting me off"), or loud sound that isn't a word (her clip, music). Such an edge moves
    # to the nearest real pause (0.15 s+ under his level - 30 dB) within 4 s: a start back to where the pause ends, an end
    # forward to where it begins, so the moment the clip was picked for stays in
    def lim(t):   # the same pause test as the QC gate: 25 dB under his speech, or near the bed when one runs under him
        i = int(t / Z.HOP); return max(float(np.percentile(env[max(0, i - 300):i + 300], 10)) + 6, Pat(t) - 25)
    def loud_at(t, after):
        i = int(t / Z.HOP); o = env[i:i + 10] if after else env[max(0, i - 10):i]
        return len(o) > 0 and 20 * np.log10(np.mean(10 ** (o / 20)) + 1e-9) > lim(t)
    def pause_runs(lo, hi):
        # a pause is 15 dB under his speaking level: the FDOE has her clip and music under him, so his pauses sit about
        # -35 dB, never silent
        i0, i1 = max(0, int(lo / Z.HOP)), min(len(env), int(hi / Z.HOP)); q = env[i0:i1] < lim((lo + hi) / 2); out, k = [], 0
        while k < len(q):
            if q[k]:
                j = k
                while j < len(q) and q[j]: j += 1
                if (j - k) * Z.HOP >= 0.15: out.append(((i0 + k) * Z.HOP, (i0 + j) * Z.HOP))
                k = j
            else: k += 1
        return out
    if loud_at(na, False):
        r = pause_runs(na - 4, na)
        if r: na = r[-1][1] - 0.02
        elif pause_runs(na, na + 4): na = pause_runs(na, na + 4)[0][1] - 0.02
    if loud_at(nb, True):
        r = pause_runs(nb, nb + 4)
        if r: nb = r[0][0] + 0.03
        elif pause_runs(nb - 4, nb): nb = pause_runs(nb - 4, nb)[-1][0] + 0.03
    def runs(lo, hi):   # contiguous quiet stretches of 40 ms+ (under the pause level) in [lo, hi]: [(start, end), ...]
        i0, i1 = max(0, int(lo / Z.HOP)), min(len(env), int(hi / Z.HOP)); L = lim((lo + hi) / 2); out, i = [], i0
        while i < i1:
            if env[i] < L:
                j = i
                while j < i1 and env[j] < L: j += 1
                if j - i >= 4: out.append((i * Z.HOP, j * Z.HOP))
                i = j
            else: i += 1
        return out
    def cut_after(k):   # end the clip just after word k's sound has gone down: the first quiet stretch after its sound
        nxt = ws[k + 1]["s"] if k + 1 < len(ws) else ws[k]["e"] + 0.6
        r = [x for x in runs(ws[k]["e"] - 0.05, max(nxt, ws[k]["e"]) + 0.2) if x[0] >= max(cores[k][0] + 0.05, ws[k]["e"] - 0.05)]
        return None if not r else r[0][0] + min(0.08, (r[0][1] - r[0][0]) / 2)   # well inside the breath, not on the word's tail
    def cut_before(k):   # start the clip just before word k rises out of the quiet: the last quiet stretch before it
        r = [x for x in runs(ws[k - 1]["e"] - 0.1, ws[k]["s"] + 0.2) if x[1] <= ws[k]["s"] + 0.2]
        return None if not r else r[-1][1] - 0.01
    def sits_in_pause(t, after):   # an edge already inside a quiet stretch needs no moving
        return any(a_ - 0.005 <= t <= b_ + 0.005 for a_, b_ in runs(t - 0.3, t + 0.3)) or (after and t >= len(env) * Z.HOP - 0.05)
    na, nb = sentences(ws, cores, na, nb, cut_before, cut_after, sits_in_pause)
    return round(na, 3), round(nb, 3)


END = (".", "?", "!")
def sentences(ws, cores, na, nb, cut_before, cut_after, sits_in_pause=lambda t, after: False, reach=12.0):
    """Whole sentences (OB 10-28: "you still cut off on the fdoe"; the clip began on "coach." of "...as a fitness coach" and
    ended on "...a probiotic for your gut health" with "and high protein, triple whammy" still to come). A clip starts on the
    first word of a sentence and ends on a word that ends one, by the transcript's punctuation, and only where there is a
    real breath: cut_before(k) / cut_after(k) find the quiet dip between word k and its neighbour (None when he runs
    straight on, as "triple whammy," did into "and..."), and the edge goes inside that dip."""
    f = next((k for k, c in enumerate(cores) if c[1] > na + 0.02), None)   # the first word actually sounding in the clip
    if f is not None and f > 0 and not (ws[f - 1]["w"].endswith(END) and sits_in_pause(na, False)):
        k = f
        while k > 0 and ws[f]["s"] - ws[k - 1]["s"] <= reach:
            if ws[k - 1]["w"].endswith(END):
                t = cut_before(k)
                if t is not None: na = t; break
            k -= 1
        else:
            if k == 0: na = max(0.0, cores[0][0] - 0.02)
    l = max((k for k, c in enumerate(cores) if c[0] < nb - 0.02), default=None)   # the last word actually sounding in it
    if l is not None and not (ws[l]["w"].endswith(END) and sits_in_pause(nb, True)):
        k = l
        while k < len(ws) and ws[k]["e"] - ws[l]["e"] <= reach:
            if ws[k]["w"].endswith(END):
                t = cut_after(k)
                if t is not None: nb = t; break
            k += 1
    return na, nb


def face_center(path, t, size=(W, H)):
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "f.jpg")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf", f"scale={size[0]}:{size[1]}", f], check=True)
        d = json.loads(subprocess.run([os.path.join(BIN, "frame_obstacles"), f], capture_output=True, text=True).stdout)
    if not d.get("faces"): return None
    x, y, w, h = max(d["faces"], key=lambda r: r[2] * r[3]); return x + w / 2, y + h / 2, w, h


# ------------------------------------------------------------------------------------------------ kick
def onto_cut(video, t, look=0.15):
    """If the picture cuts within `look` s after t, the clip starts on that cut, not one frame before it (the 10-28 comment
    mock opened on the last frame of the previous shot: a one-frame flash)."""
    best, prev, k = None, None, 0
    for tt, im in frames(video, max(0, t - 0.02), look + 0.05, (144, 256)):
        a = np.asarray(im, np.int16)
        if prev is not None and (np.abs(a - prev) > 14).mean() > 0.25: best = tt; break   # similar shots of him: 38% changed
        prev = a
    return best if best is not None else t


def kick(inp, out, start, dur, ats, audio=None, scale=1.08, hold=0.35):
    """Punch to `scale` 0.05 s before each word (POP: lands with a little overshoot), hold, SOFT back to 1."""
    start, end = snap(audio or inp, start, start + dur); dur = end - start; SEGS.append((audio or inp, start, end))
    big = (int(W * 1.5), int(H * 1.5))   # decode 1.5x, so the zoom is cut from real pixels, not upscaled
    fc = face_center(inp, ats[0], big); cx, cy = (fc[0], fc[1]) if fc else (big[0] / 2, big[1] * 0.4)
    def z(t):
        k = sum(spring(t - (a - 0.05), POP) - spring(t - (a - 0.05 + hold), SOFT) for a in ats)
        return 1 + (scale - 1) * k
    with tempfile.TemporaryDirectory() as td:
        vid = os.path.join(td, "v.mp4"); wp = writer(vid)
        raw = bool(re.match(r"C\d+\.MP4$", os.path.basename(inp), re.I))   # straight off the Sony: grade it; renders already are
        for t, im in frames(inp, start, dur, big, LUT if raw else None):
            zz = max(1.0, z(t)); cw, ch = big[0] / zz, big[1] / zz
            x0, y0 = cx * (1 - 1 / zz), cy * (1 - 1 / zz)   # zoom toward his face: it stays where it is on screen
            wp.stdin.write(im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).tobytes())
        wp.stdin.close(); wp.wait()
        wav = os.path.join(td, "a.wav")
        if audio:   # his mic for the same seconds, mastered the safe way
            import voice_master as VM
            from scipy.io import wavfile
            raw = np.frombuffer(subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", audio, "-ac", "1",
                                                "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
            m, rep = VM.master(raw, 48000, -14.0); wavfile.write(wav, 48000, m.astype(np.float32)); print("voice:", rep)
        else: cut_audio(inp, [(start, start + dur)], wav)
        mux(vid, wav, out)


# ------------------------------------------------------------------------------------------------ counter
def card_box(im):
    """(top, bottom) of the big white Cronometer card in the frame, or None: rows that are 60%+ near-white across the middle."""
    a = np.asarray(im.convert("RGB"))[:, 60:W - 60]; frac = ((a > 232).all(axis=2)).mean(axis=1)
    runs, k = [], 0   # rows that are mostly white, joined across the card's busier rows (the nutrient rings): gaps up to 60 px
    while k < len(frac):
        if frac[k] > 0.3:
            j = k
            while j < len(frac) and frac[j] > 0.3: j += 1
            if runs and k - runs[-1][1] <= 60: runs[-1][1] = j
            else: runs.append([k, j])
            k = j
        else: k += 1
    runs = [r for r in runs if r[1] - r[0] > 150 and frac[r[0]:r[1]].max() > 0.6]
    return tuple(max(runs, key=lambda r: r[1] - r[0])) if runs else None


def counter_layer(t, steps, y):
    """steps: [(time, label, total)]. The pill slides in at the first step; each later step pops a "+delta" chip and counts up."""
    if t < steps[0][0] - 0.05: return None
    cur = max(i for i, s in enumerate(steps) if s[0] <= t + 1e-6) if t >= steps[0][0] else 0
    t_i, label, total = steps[cur]; prev = steps[cur - 1][2] if cur > 0 else 0
    v = total if t - t_i > 0.6 else prev + (total - prev) * min(1.0, spring(t - t_i - 0.15, SNAP))   # lands on the exact total
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    e = spring(t - steps[0][0], SLIDE); a = int(235 * min(1.0, e * 1.4))
    pw, ph = 620, 104; px = (W - pw) // 2; py = int(y - 40 * (1 - e))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([px, py + 8, px + pw, py + ph + 8], 52, fill=(0, 0, 0, int(a * 0.45)))
    L = Image.alpha_composite(L, sh.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(L)
    d.rounded_rectangle([px, py, px + pw, py + ph], 52, fill=(14, 14, 14, a), outline=(255, 255, 255, int(a * 0.12)), width=2)
    f1, f2, f3 = font(24), ImageFont.truetype(DIN, 78), font(30)
    d.text((px + 44, py + 24), "DAY SO FAR", font=f1, fill=(190, 190, 190, a))
    d.text((px + 44, py + 56), label, font=font(26), fill=(255, 255, 255, a))
    num = f"{int(round(v)):,}"; nw = d.textlength(num, font=f2); kw = d.textlength(" kcal", font=f3)
    d.text((px + pw - 44 - kw - nw, py + 14), num, font=f2, fill=YEL + (a,))
    d.text((px + pw - 44 - kw, py + 48), " kcal", font=f3, fill=(255, 255, 255, a))
    if cur > 0 and t - t_i < 1.4:   # the "+225" chip, just under the number (clear of the card and of him)
        s = spring(t - t_i, POP); fade = 1.0 if t - t_i < 1.0 else max(0.0, 1 - (t - t_i - 1.0) / 0.4)
        chip = f"+{total - prev:,}"; cf = font(36); cw_ = int(d.textlength(chip, font=cf)) + 44
        C = Image.new("RGBA", (cw_, 64), (0, 0, 0, 0)); cd = ImageDraw.Draw(C)
        cd.rounded_rectangle([0, 0, cw_ - 1, 63], 32, fill=YEL + (int(255 * fade),)); cd.text((22, 11), chip, font=cf, fill=(14, 14, 14, int(255 * fade)))
        sc = max(0.05, s); C = C.resize((max(1, int(cw_ * sc)), max(1, int(64 * sc))), Image.LANCZOS)
        L.alpha_composite(C, (px + pw - 44 - int(kw + nw / 2) - C.width // 2, py + ph + 14 + (64 - C.height) // 2))
    return L


def counter(inp, out, segs, steps, y=None):
    segs = [snap(inp, a, b) for a, b in segs]; SEGS.extend((inp, a, b) for a, b in segs)
    """y=None: the pill sits 24 px under the Cronometer card wherever the layout puts it (the FDOE switches between her clip
    with the card on top and him at the desk with the card low); above the card when under it would reach the IG band."""
    with tempfile.TemporaryDirectory() as td:
        vid = os.path.join(td, "v.mp4"); wp = writer(vid); yy = y or 770
        for a, b in segs:
            for t, im in frames(inp, a, b - a):
                if y is None:
                    cb = card_box(im)
                    if cb: yy = cb[1] + 24 if cb[1] + 24 + 104 + 80 < H - 420 else max(230, cb[0] - 104 - 24)
                L = counter_layer(t, steps, yy)
                if L is not None: im = Image.alpha_composite(im.convert("RGBA"), L).convert("RGB")
                wp.stdin.write(im.tobytes())
        wp.stdin.close(); wp.wait()
        wav = os.path.join(td, "a.wav"); cut_audio(inp, segs, wav); mux(vid, wav, out)


# ------------------------------------------------------------------------------------------------ comments
COMMENTERS = [((214, 92, 112), "J", "ja•••nn", "631724"), ((84, 132, 214), "M", "mi•••ra", "631724 please"), ((92, 170, 120), "D", "da•••ez", "631724"),
              ((205, 140, 60), "K", "kr•••ss", "631724!!"), ((150, 96, 200), "A", "al•••ia", "631724"), ((60, 160, 170), "T", "to•••yb", "631724 thank you")]


def circle(img, size):
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA"); m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255); img.putalpha(m); return img


def initial_avatar(color, letter, size):
    A = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(A); d.ellipse([0, 0, size - 1, size - 1], fill=color + (255,))
    f = font(int(size * 0.46)); w = d.textlength(letter, font=f); d.text(((size - w) / 2, size * 0.2), letter, font=f, fill=(255, 255, 255, 255)); return A


def heart(d, x, y, s, col):
    r = s / 4; d.ellipse([x, y, x + 2 * r, y + 2 * r], outline=col, width=2); d.ellipse([x + 2 * r, y, x + 4 * r, y + 2 * r], outline=col, width=2)
    d.line([(x + 0.3 * r, y + 1.6 * r), (x + 2 * r, y + 3.6 * r), (x + 3.7 * r, y + 1.6 * r)], fill=col, width=2)


def comments_layer(t, t0, box, code, dm, avatar):
    if t < t0 - 0.15: return None
    x, y, w, h = box[0] - 8, box[1] - 8, box[2] + 16, box[3] + 16   # a little larger than the panel it replaces
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    e = spring(t - (t0 - 0.15), SLIDE); a = int(255 * min(1.0, e * 1.3)); oy = int(30 * (1 - e))
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 36, fill=(18, 18, 18, a), outline=(255, 255, 255, int(a * 0.10)), width=2)
    d.rounded_rectangle([w // 2 - 32, 12, w // 2 + 32, 18], 3, fill=(90, 90, 90, a))
    hf = font(32); d.text(((w - d.textlength("Comments", font=hf)) / 2, 26), "Comments", font=hf, fill=(255, 255, 255, a))
    d.line([(0, 72), (w, 72)], fill=(255, 255, 255, int(a * 0.08)), width=1)
    # comments arrive every 0.35 s, newest on top, sliding in from above; the list is clipped to its area
    list_top, list_bot = 78, h - 92; rowh = 86
    shown = [(k, t0 + 0.1 + 0.35 * k) for k in range(len(COMMENTERS)) if t >= t0 + 0.1 + 0.35 * k]
    LST = Image.new("RGBA", (w, list_bot - list_top), (0, 0, 0, 0)); ld = ImageDraw.Draw(LST)
    s = min(1.0, spring(t - shown[-1][1], SNAP)) if shown else 1.0   # the newest one slides in, the rest move down a row
    for rank, (k, ta) in enumerate(reversed(shown)):
        col, ini, name, text = COMMENTERS[k]
        yy = int((-(1 - s) if rank == 0 else (rank - 1 + s)) * rowh) + 8
        if yy > LST.height: continue
        al = int(a * (min(1.0, s * 1.5) if rank == 0 else 1.0))
        LST.alpha_composite(initial_avatar(col, ini, 58), (26, yy + 8))
        ago = "now" if t - ta < 1.5 else f"{int(t - ta)}s"
        ld.text((100, yy), f"{name}  {ago}", font=font(26, False), fill=(165, 165, 165, al))
        ld.text((100, yy + 32), text, font=font(36), fill=(255, 255, 255, al))
        heart(ld, w - 72, yy + 26, 30, (170, 170, 170, al))
    card.alpha_composite(LST, (0, list_top))
    # the viewer's comment bar: types the code, then sends
    by = h - 80; d.rounded_rectangle([88, by, w - 96, by + 58], 29, fill=(38, 38, 38, a))
    you = Image.new("RGBA", (48, 48), (0, 0, 0, 0)); yd = ImageDraw.Draw(you); yd.ellipse([0, 0, 47, 47], fill=(110, 110, 110, a))
    yd.ellipse([16, 8, 32, 24], fill=(200, 200, 200, a)); yd.pieslice([8, 26, 40, 58], 180, 360, fill=(200, 200, 200, a)); card.alpha_composite(you, (28, by + 5))
    t_type = t0 + 0.1 + 0.35 * len(COMMENTERS) - 0.4; nchar = max(0, min(len(code), int((t - t_type) / 0.09))) if t >= t_type else 0
    if nchar == 0: d.text((112, by + 13), "Add a comment for ob_health.fit...", font=font(28, False), fill=(150, 150, 150, a))
    else:
        txt = code[:nchar]; d.text((112, by + 9), txt, font=font(34), fill=(255, 255, 255, a))
        if int(t * 2.5) % 2 == 0 and nchar < len(code): cx_ = 112 + d.textlength(txt, font=font(34)) + 3; d.line([(cx_, by + 10), (cx_, by + 48)], fill=(0, 149, 246, a), width=3)
    t_send = t_type + 0.09 * len(code) + 0.15; ps = 1 + 0.25 * (spring(t - t_send, POP) - spring(t - t_send - 0.12, SNAP)) if t >= t_send else 1.0
    r = int(29 * ps); cxs, cys = w - 52, by + 29
    d.ellipse([cxs - r, cys - r, cxs + r, cys + r], fill=(0, 149, 246, a) if nchar == len(code) else (60, 60, 60, a))
    d.line([(cxs, cys + 12), (cxs, cys - 12)], fill=(255, 255, 255, a), width=4); d.line([(cxs - 10, cys - 2), (cxs, cys - 12), (cxs + 10, cys - 2)], fill=(255, 255, 255, a), width=4)
    L.alpha_composite(card, (x, y + oy))
    # his DM drops in after the send
    t_dm = t_send + 0.35
    if t >= t_dm:
        s = spring(t - t_dm, SLIDE); bw, bh = w - 40, 116; bx = x + 20; byy = int(y + 10 - (1 - s) * 150)
        B = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); bd = ImageDraw.Draw(B); al = int(250 * min(1.0, s * 1.5))
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], 30, fill=(44, 44, 46, al), outline=(255, 255, 255, int(al * 0.12)), width=2)
        if avatar is not None: B.alpha_composite(avatar, (20, 24))
        bd.text((106, 18), "ob_health.fit", font=font(31), fill=(255, 255, 255, al))
        nw = bd.textlength("ob_health.fit", font=font(31)); bd.text((106 + nw + 12, 22), "· now", font=font(27, False), fill=(170, 170, 170, al))
        bd.text((106, 62), dm, font=font(30, False), fill=(235, 235, 235, al))
        L.alpha_composite(B, (bx, max(0, byy)))
    return L


def comments(inp, out, start, dur, t0, code, dm, box=(80, 230, 920, 412), avatar_img=None):
    start, end = snap(inp, start, start + dur); start = onto_cut(inp, start); dur = end - start; SEGS.append((inp, start, end))
    av = None
    if avatar_img: av = circle(Image.open(avatar_img), 68)
    with tempfile.TemporaryDirectory() as td:
        vid = os.path.join(td, "v.mp4"); wp = writer(vid)
        for t, im in frames(inp, start, dur):
            Lr = comments_layer(t, t0, box, code, dm, av)
            if Lr is not None: im = Image.alpha_composite(im.convert("RGBA"), Lr).convert("RGB")
            wp.stdin.write(im.tobytes())
        wp.stdin.close(); wp.wait()
        wav = os.path.join(td, "a.wav"); cut_audio(inp, [(start, start + dur)], wav); mux(vid, wav, out)


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] not in ("kick", "counter", "comments"): print(__doc__); sys.exit(2)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    cmd, inp, out = a[0], a[1], a[2]
    if cmd == "kick":
        ats = [float(a[i + 1]) for i, x in enumerate(a) if x == "--at"]
        kick(inp, out, float(opt("--start")), float(opt("--dur")), ats, opt("--audio"), float(opt("--scale", 1.08)), float(opt("--hold", 0.35)))
    elif cmd == "counter":
        segs = [tuple(float(v) for v in s.split(":")) for s in opt("--segments").split(",")]
        steps = [(float(s.split(":")[0]), s.split(":")[1], int(s.split(":")[2])) for s in opt("--steps").split(",")]
        counter(inp, out, segs, steps, int(opt("--y")) if opt("--y") else None)
    else:
        box = tuple(int(v) for v in opt("--box", "80,230,920,412").split(","))
        comments(inp, out, float(opt("--start")), float(opt("--dur")), float(opt("--at")), opt("--code"), opt("--dm"), box, opt("--avatar"))
    print("pieces (snapped to whole words):", [(os.path.basename(p), a, b) for p, a, b in SEGS])
    try:
        import qc_gate; qc_gate.after_render(out, segs=SEGS)
    except Exception as e: print("qc_gate not run:", e)


if __name__ == "__main__":
    main()
