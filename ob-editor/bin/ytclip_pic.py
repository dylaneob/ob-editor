"""ytclip's picture: the 9:16 reel from the cut (reels/R?/cut.json), the long-form's events rebuilt for 9:16, captions and the
frame-1 versions. One compositor draws both the shot-by-shot stills OB approves and the render, so what he OKs is what ships.

Layout (measured on the C4372 mocks, 10-28): the 4K frame cropped 1215x2160 around his face (108% punch-ins alternate, zoomed
about his eyes so the cap stays in), his chin around y 1120-1260. Instagram covers the top 220 px and everything under y 1500.
  captions   3 words, live word yellow (OB's locked look), centred at y 1428, under his chin on every shot
  chest      small long-form cards (facequote, stamp, pills, checklist, split) between his chin + 36 and the captions
  cutaway    big ones (num, versus, stat_bars, study, doc, photo_full) full frame for at most 2.5 s
  split      horizontal B-roll and news clips (OB 10-28, Dylan Page's layout): 50/50, the footage filling the top half and him
             chest-up under it, captions on the seam, the source tag at the top; where he can't be on screen (a look-off cover,
             a clip playing its own sound) his words fill the bottom half instead. Vertical footage fills the frame.
  frame 1    the version's opening (no face / small face / two faces) under a 2-line title from his words, until the first cut
             after 1.8 s; the content lab reads which opening wins (RULEBOOK 10-28: a big face in frame 1 costs shares and saves)
Springs only (cards.py's closed-form damped spring), nothing on frame 1 that isn't already a finished picture.
"""
import hashlib, json, math, os, re, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BIN = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.expanduser("~/ob-editor/fonts")
HEAVY, DEMI, DIN = f"{FONTS}/AvenirNext-Heavy.ttf", f"{FONTS}/AvenirNext-DemiBold.ttf", f"{FONTS}/DINCondensed-Bold.ttf"
FW, FH = 1080, 1920
CAP_Y, CARD_BOTTOM, TITLE_Y = 1428, 1352, 300
CROP_W, CROP_H, PUNCH = 1215, 2160, 1.0   # 11-07 OB: no zooming in or out, no punch-ins (was 1.08 on every other shot)
YEL, WHITE, INK, RED = (255, 212, 0), (255, 255, 255), (16, 16, 18), (226, 40, 40)
MAX_CUTAWAY, MAX_CHEST, INTRO_MIN = 2.5, 3.6, 1.8
LEAD = 0.45   # s of picture and title before his first word: the hook spec's silent prop beat, and no blast in the first 0.5 s
              # (PROVEN-OPENERS #4: keep it under -15 dBFS; the 10-28 test opened at -13.3 with the voice on frame 1)
# the split (OB 10-28: "for the horizontal clips do the 50/50 split screen formats like dylan paige"; styles/dylan-page-split.md):
# on his 3 biggest TikToks that week the clip fills the top half edge to edge, no divider, and he sits chest-up under it with
# about 100 px over his cap. OB's cap top is about 0.55 face boxes above Vision's box (4 frames 10-28: 0.46-0.67), so his face
# box is 332 px with the cap top at 1025, clear of the captions riding just above the seam; his chin lands near y 1535.
SEAM, SPLIT_BOX, SPLIT_TOP, HEAD, SPLIT_CAP_Y, SPLIT_TAG_Y = 960, 332, 1025, 1.55, 930, 236
CHEST ={"facequote", "stamp", "pills", "checklist", "split", "selfquote"}
FULL = {"num", "versus", "stat_bars", "study", "doc", "photo_full"}
VIDEO = {"insert"}


def font(p, s): return ImageFont.truetype(p, s)


def spring(t, w=22.0, z=0.55):
    z = 0.92   # 11-07: every entrance spring damped at 0.92, no overshoot

    """Damped spring 0 -> 1 (cards.py POP): overshoots about 8% and settles in about 0.35 s."""
    if t <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode: raise RuntimeError(" ".join(str(c) for c in cmd[:8]) + "\n" + p.stderr[-1500:])
    return p.stdout


# ---------------------------------------------------------------------------------------------------- the timeline
def timeline(c, cut):
    """Shots in reel time from the cut: every piece is a shot (his camera, or a long-form clip with its own sound)."""
    fps = c["fps"]; shots, f = [], int(round(LEAD * fps))
    for l in cut["lines"]:
        for p, q in l["pieces"]:
            n = int(round((q - p) * fps))
            shots.append(dict(kind="clip" if l.get("clip") else "ob", line=l["id"], clip=l.get("clip"), a=p, b=q, f0=f, n=n,
                              t0=f / fps, t1=(f + n) / fps))
            f += n
    return shots, f


def reel_time(shots, line_id, t_src):
    """A source (or clip) second of line `line_id` in reel seconds (a word in a cut gap lands on the next piece)."""
    best = None
    for s in shots:
        if s["line"] != line_id: continue
        if s["a"] - 1e-3 <= t_src <= s["b"] + 1e-3: return s["t0"] + (t_src - s["a"])
        if t_src < s["a"] and best is None: best = s["t0"]
    return best if best is not None else max(s["t1"] for s in shots if s["line"] == line_id)


def words_reel(c, cut, shots):
    """Caption words: each line's text (what he said) on Apple's word times, mapped into the reel."""
    import difflib, takes as TK
    out = []
    for l in cut["lines"]:
        disp = (l.get("text") or " ".join(w["w"] for w in l["words"])).split()
        ws = l["words"]; wt, wi = [], []
        for k, w in enumerate(ws):
            for t in TK.toks(w["w"]): wt.append(t); wi.append(k)
        dt, di = [], []
        for k, w in enumerate(disp):
            for t in TK.toks(w): dt.append(t); di.append(k)
        times = [None] * len(disp)
        for blk in difflib.SequenceMatcher(None, dt, wt, autojunk=False).get_matching_blocks():
            for x in range(blk.size):
                k = di[blk.a + x]
                if times[k] is None: times[k] = ws[wi[blk.b + x]]["s"]
        lo, hi = l["pieces"][0][0], l["pieces"][-1][1]
        if times and times[0] is None: times[0] = lo
        for k in range(1, len(times)):   # unmatched words share the time to the next matched one
            if times[k] is None:
                j = k
                while j < len(times) and times[j] is None: j += 1
                nxt = times[j] if j < len(times) else hi - 0.1
                for m in range(k, j): times[m] = times[k - 1] + (nxt - times[k - 1]) * (m - k + 1) / (j - k + 1)
        for w, t in zip(disp, times):
            out.append(dict(w=w, t=reel_time(shots, l["id"], max(lo, min(t, hi))), line=l["id"]))
    for k in range(1, len(out)): out[k]["t"] = max(out[k]["t"], out[k - 1]["t"] + 0.06)
    return out


def chunks(words, n=3):
    """3-word caption chunks (OB's locked look), breaking after punctuation; each shows until the next starts."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == n or w["w"].endswith((".", "?", "!", ",", ":")): out.append(cur); cur = []
    if cur: out.append(cur)
    return [dict(words=ch, t0=ch[0]["t"], t1=(out[k + 1][0]["t"] if k + 1 < len(out) else ch[-1]["t"] + 0.8)) for k, ch in enumerate(out)]


# ---------------------------------------------------------------------------------------------------- faces and crops
def grab(c, t, out, w=1920):
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", c["camera"], "-frames:v", "1", "-vf", f"scale={w}:-2", "-q:v", "3", out])


def faces_of(c, shots):
    """Face box (4K px) per camera shot: Apple Vision on the shot's middle frame, cached by source time."""
    cp = os.path.join(c["work"], "cache", "faces.json"); cache = json.load(open(cp)) if os.path.exists(cp) else {}
    todo = [s for s in shots if s["kind"] == "ob" and f"{(s['a'] + s['b']) / 2:.3f}" not in cache]
    if todo:
        with tempfile.TemporaryDirectory() as td:
            imgs = []
            for k, s in enumerate(todo):
                p = os.path.join(td, f"f{k}.jpg"); grab(c, (s["a"] + s["b"]) / 2, p); imgs.append(p)
            for line in run([os.path.join(BIN, "faces")] + imgs).splitlines():
                path, rest = line.split(" ", 1)
                k = int(os.path.basename(path)[1:-4]); s = todo[k]
                box = None if rest.strip() in ("none", "error") else [float(v) * 2 for v in rest.split("|")[0].split()]
                cache[f"{(s['a'] + s['b']) / 2:.3f}"] = box
        json.dump(cache, open(cp, "w"))
    for s in shots:
        if s["kind"] == "ob": s["face"] = cache.get(f"{(s['a'] + s['b']) / 2:.3f}")
    prev = None   # a shot where Vision missed him keeps the last one's box (he doesn't leave the frame)
    for s in shots:
        if s["kind"] != "ob": continue
        if s["face"] is None: s["face"] = prev or [1560, 300, 2400, 1320]
        prev = s["face"]


def crops(shots):
    """Crop per camera shot: 1215x2160 around his face, every other shot 108% about his eyes; chin line in reel px."""
    k = 0
    for s in shots:
        if s["kind"] != "ob": continue
        x0f, y0f, x1f, y1f = s["face"]; cx, cy = (x0f + x1f) / 2, y0f + 0.42 * (y1f - y0f)
        z = PUNCH if k % 2 else 1.0; k += 1
        w, h = CROP_W / z, CROP_H / z
        x = min(max(cx - w / 2, 0), 3840 - w); y = min(max(cy * (1 - 1 / z), 0), 2160 - h)
        s["zoom"], s["crop"] = z, [round(w), round(h), round(x), round(y)]
        s["chin"] = (y1f - y) * FH / h


def split_crops(shots):
    """His crop in the split's bottom half (1080x960): face box SPLIT_BOX px with his cap top at SPLIT_TOP. The full frame's 108%
    shots go to 93% here instead (a punch-in would push his cap into the captions), so the cuts still change size."""
    for s in shots:
        if s["kind"] != "ob": continue
        x0f, y0f, x1f, y1f = s["face"]; bh = y1f - y0f
        sc = max(SPLIT_BOX / s["zoom"] / bh, (FH - SEAM) / 2160, FW / 3840); w, h = FW / sc, (FH - SEAM) / sc
        cap = y0f - (HEAD - 1) * bh
        x = min(max((x0f + x1f) / 2 - w / 2, 0), 3840 - w); y = min(max(cap - (SPLIT_TOP - SEAM) / sc, 0), 2160 - h)
        s["scrop"] = [round(w), round(h), round(x), round(y)]
        s["sface"] = [round(SEAM + (cap - y) * sc), round(SEAM + (y0f - y) * sc), round(SEAM + (y1f - y) * sc)]   # cap top, face box top, chin


# ---------------------------------------------------------------------------------------------------- the long-form's events
def events_in(c, cut, shots):
    """The long-form's graphics that fall inside the reel's camera shots, as reel-timed cards (rebuilt for 9:16, never cropped)."""
    evs = json.load(open(os.path.join(c["longform"], "events_resolved.json")))["events"]
    obs = [s for s in shots if s["kind"] == "ob"]; cards = []
    def to_reel(t):
        for s in obs:
            if s["a"] - 0.05 <= t <= s["b"] + 0.05: return s["t0"] + min(max(t - s["a"], 0), s["b"] - s["a"])
        return None
    for e in evs:
        typ = e["type"]
        if typ not in CHEST | FULL | VIDEO: continue
        a, b = e.get("anchor_src"), e.get("end_src")
        if a is None or b is None: continue
        hits = [s for s in obs if s["b"] > a and s["a"] < b]
        if not hits: continue
        t0 = to_reel(max(a, hits[0]["a"])); t1 = to_reel(min(b, hits[-1]["b"]))
        if t0 is None or t1 is None or t1 - t0 < 0.4: continue
        kind = "chest" if typ in CHEST else ("video" if typ in VIDEO else "full")
        t1 = min(t1, t0 + (MAX_CHEST if kind == "chest" else MAX_CUTAWAY))
        sub = {}   # item times (source) -> reel
        for key, val in (e.get("at") or {}).items():
            if isinstance(val, dict) and "src" in val:
                r = to_reel(val["src"])
                if r is not None: sub[key] = r - t0
        if e.get("items_src"): sub["items"] = [((to_reel(x) or t0) - t0) for x in e["items_src"]]
        if e.get("bars_t"): sub["bars"] = list(e["bars_t"])
        span = t1 - t0; lastt = max([v for v in sub.values() if isinstance(v, (int, float))] + [x for v in sub.values() if isinstance(v, list) for x in v] + [0.0])
        if kind != "video" and lastt > 0.6 * span:   # every item lands by 60% of the card, in its order
            f = 0.6 * span / lastt
            sub = {k: ([x * f for x in v] if isinstance(v, list) else v * f) for k, v in sub.items()}
        cards.append(dict(id=e["id"], type=typ, kind=kind, t0=round(t0, 3), t1=round(t1, 3), ev=e, sub=sub))
    cards.sort(key=lambda x: x["t0"]); keep = []
    for cd in cards:   # one card at a time: a later one starts when the earlier one ends
        if keep and cd["t0"] < keep[-1]["t1"]:
            if cd["kind"] == keep[-1]["kind"] == "chest" or cd["t0"] - keep[-1]["t0"] > 0.8: keep[-1]["t1"] = cd["t0"]
            else: continue
        keep.append(cd)
    return [cd for cd in keep if cd["t1"] - cd["t0"] >= 0.4]


def add_covers(L, flags, lead=0.12, hold=0.55):
    """A full-frame cutaway over every cut edge where he looks down, shuts his eyes or turns away (OB 10-28: "you either cut me
    off mid sentence or have me looking off"; the long-form hid these behind cards beside his face, which become chest cards in
    9:16 and no longer cover him). The chest card showing there goes full screen ("fullquote"); otherwise his words land big on a
    dark frame ("kinetic"). A start flag is covered from just before the cut to 0.55 s in, an end flag the mirror."""
    covers = []
    for x in flags:
        if x.get("covered"): continue
        te = x["reel_t"]
        a, b = (te - lead, te + hold) if x["side"] == "start" else (te - hold, te + lead)
        a, b = max(a, L["intro_end"]), min(b, L["frames"] / L["fps"])
        if b - a < 0.2: continue
        ch = next((cd for cd in L["cards"] if cd["kind"] == "chest" and cd["t0"] - 0.05 <= te <= cd["t1"] + 0.05), None)
        said = " ".join(w["w"] for w in L["words"] if a - 0.3 <= w["t"] <= b + 0.3) + " " + (ch["ev"].get("text", "") if ch else "")
        # M16 (OB 10-19: "you just put text... not even a photo"): a cover over a number or a food shows a real visual, so the
        # nearest long-form photo, B-roll or chart in this reel (within 8 s) flashes back; plain words only when there is none
        vis = sorted((cd for cd in L["cards"] if cd["kind"] in ("full", "video") and not cd["id"].startswith("COVER")),
                     key=lambda cd: min(abs(cd["t0"] - te), abs(cd["t1"] - te)))
        near = vis[0] if vis and min(abs(vis[0]["t0"] - te), abs(vis[0]["t1"] - te)) <= 8.0 else None
        needs_visual = bool(re.search(r"\d|calorie|food|oil|oreo|chip|fries|meat|organ|steroid|oat|lime|chicken|protein|grocer", said, re.I))
        if near is not None and (needs_visual or ch is None):
            covers.append(dict(id=f"COVER{len(covers):02d}", type=near["type"], kind=near["kind"], t0=round(a, 3), t1=round(b, 3),
                               ev=near["ev"], sub={}, src="visual", of=near["id"]))
        else:
            covers.append(dict(id=f"COVER{len(covers):02d}", type="fullquote" if ch else "kinetic", kind="full", t0=round(a, 3), t1=round(b, 3),
                               ev=(ch["ev"] if ch else {}), sub={}, src=ch["type"] if ch else None, m16_risk=needs_visual))
    m = []
    for cv in sorted(covers, key=lambda z: z["t0"]):
        # the same card again within 1.5 s holds through instead of flashing on and off (R4 10-28: one quote 4 times in 4 s)
        same = m and cv["type"] == m[-1]["type"] and cv.get("ev", {}).get("id") == m[-1].get("ev", {}).get("id") and cv["kind"] == m[-1]["kind"]
        if m and ((same and cv["t0"] <= m[-1]["t1"] + 1.5) or (cv["type"] == m[-1]["type"] == "kinetic" and cv["t0"] <= m[-1]["t1"] + 0.6)):
            m[-1]["t1"] = max(m[-1]["t1"], cv["t1"])
        else: m.append(cv)
    keep = [cd for cd in L["cards"] if not (cd["kind"] == "full" and any(cv["t0"] < cd["t1"] and cv["t1"] > cd["t0"] for cv in m))]
    L["cards"] = sorted(keep + m, key=lambda z: (z["t0"], 0 if z["id"].startswith("COVER") else 1))
    return m


# ---------------------------------------------------------------------------------------------------- drawing
def text_w(d, s, f): return d.textlength(s, font=f)


def shadow_text(im, xy, s, f, fill=WHITE, stroke=5, anchor="mm", blur=7):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.text((xy[0] + 3, xy[1] + 5), s, font=f, fill=(0, 0, 0, 180), anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0, 180))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, path, size, maxw):
    while size > 30 and d.textlength(s, font=font(path, size)) > maxw: size -= 2
    return font(path, size)


def draw_caption(im, ch, t, y=CAP_Y):
    d = ImageDraw.Draw(im); ws = [w["w"] for w in ch["words"]]
    f = fit(d, " ".join(ws), HEAVY, 80, FW - 140); gap = 20
    widths = [text_w(d, w, f) for w in ws]; x = (FW - sum(widths) - gap * (len(ws) - 1)) / 2
    live = max([k for k, w in enumerate(ch["words"]) if w["t"] <= t] or [0])
    for k, w in enumerate(ws):
        shadow_text(im, (x + widths[k] / 2, y), w, f, YEL if k == live else WHITE)
        x += widths[k] + gap


def words_half(im, ch, t, lt):
    """His words big in the split's bottom half, where his face can't show (a look-off cover, or a clip playing its own sound):
    the full-frame word cover's look, live word yellow, popping in on each 3-word chunk."""
    if ch is None: return
    d = ImageDraw.Draw(im); ws = [w["w"].upper() for w in ch["words"]]
    live = max([k for k, w in enumerate(ch["words"]) if w["t"] <= t] or [0])
    f = fit(d, max(ws, key=len), HEAVY, 120, FW - 160); f = font(HEAVY, int(f.size * min(1.0, 0.82 + 0.18 * spring(lt))))
    for k, w in enumerate(ws):
        shadow_text(im, (FW / 2, 1225 + (k - (len(ws) - 1) / 2) * 140), w, f, YEL if k == live else WHITE, stroke=6)


def card_top(im, text, lt):
    """A title too small to read at 1080 wide, rebuilt on the split's white top half from its own words (RIG 2: 76 px or more)."""
    import textwrap
    d = ImageDraw.Draw(im); lines = textwrap.wrap(text, 20); f = fit(d, max(lines, key=len), DEMI, 84, FW - 140)
    f = font(DEMI, int(f.size * min(1.0, 0.9 + 0.1 * spring(lt)))); lh = int(f.size * 1.2)
    for k, l in enumerate(lines): d.text((FW / 2, 540 + (k - (len(lines) - 1) / 2) * lh), l, font=f, fill=INK, anchor="mm")


def balance(text, n):
    """text in n lines of about equal width (never drops a word)."""
    ws = text.split()
    if n <= 1 or len(ws) < 4: return [text]
    best = min(range(1, len(ws)), key=lambda k: abs(len(" ".join(ws[:k])) - len(" ".join(ws[k:]))))
    return [" ".join(ws[:best]), " ".join(ws[best:])]


def plate(im, cx, y, lines, f, fill=(255, 255, 255, 255), ink=INK, pad=(34, 18), lh=None, scale=1.0, radius=24):
    """A white rounded plate with black text (the reference's title box), drawn at `scale` around its centre (springs)."""
    d = ImageDraw.Draw(im); lh = lh or int(f.size * 1.22)
    w = max(text_w(d, l, f) for l in lines) + 2 * pad[0]; h = lh * len(lines) + 2 * pad[1]
    lay = Image.new("RGBA", (int(w) + 40, int(h) + 40), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([24, 28, 20 + w, 24 + h], radius, fill=(0, 0, 0, 80)); lay = lay.filter(ImageFilter.GaussianBlur(7))
    ImageDraw.Draw(lay).rounded_rectangle([20, 20, 20 + w, 20 + h], radius, fill=fill)
    for k, l in enumerate(lines): ImageDraw.Draw(lay).text((20 + w / 2, 20 + pad[1] + lh * k + lh / 2), l, font=f, fill=ink, anchor="mm")
    if scale != 1.0:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.LANCZOS)
    im.alpha_composite(lay, (int(cx - lay.width / 2), int(y + (h + 40) * (1 - scale) / 2 - 20)))
    return y + h


def draw_title(im, lines, chip=None, y=TITLE_Y):
    yb = plate(im, FW / 2, y, lines, font(HEAVY, 60))
    if chip:
        d = ImageDraw.Draw(im); f = font(HEAVY, 44); w = text_w(d, chip, f) + 56
        d.rounded_rectangle([(FW - w) / 2, yb + 30, (FW + w) / 2, yb + 106], 38, fill=YEL)
        d.text((FW / 2, yb + 68), chip, font=f, fill=INK, anchor="mm")


def cover(img, w, h, focal=(0.5, 0.5)):
    s = max(w / img.width, h / img.height); im = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x = int((im.width - w) * focal[0]); y = int((im.height - h) * focal[1])
    return im.crop((x, y, x + w, y + h))


def dark_bg():
    im = Image.new("RGBA", (FW, FH), (17, 17, 20, 255)); d = ImageDraw.Draw(im)
    for y in range(0, FH, 4): d.line([0, y, FW, y], fill=(17 + y // 120, 17 + y // 140, 22 + y // 110, 255))
    return im


def asset(c, rel): return os.path.join(c["longform"], "hf", "assets", rel)


_IMG = {}
def img(path):
    if path not in _IMG: _IMG[path] = Image.open(path).convert("RGB")
    return _IMG[path]


def chest_card(im, cd, t, chin):
    """Small long-form cards on his chest, between his chin + 36 and the captions; springs in, every item on its word."""
    e, lt = cd["ev"], t - cd["t0"]; top = max(chin + 36, 980)
    room = (1480 if cd["type"] in ("facequote", "selfquote") else CARD_BOTTOM) - top   # a quote stands in for the captions: it may use their room
    s = min(1.0, 0.7 + 0.3 * spring(lt)) if lt < 0.6 else 1.0
    d = ImageDraw.Draw(im)
    if cd["type"] in ("facequote", "selfquote"):
        lines = balance(e["text"].replace("\n", " "), 2 if room >= 150 or len(e["text"]) > 30 else 1)
        f = fit(d, max(lines, key=len), HEAVY, 60, FW - 150)
        plate(im, FW / 2, top, lines, f, scale=s)
    elif cd["type"] == "stamp":
        txt = e["text"].replace("\n", " "); f = fit(d, txt, DIN, 128 if len(txt) <= 8 else 100, FW - 260)
        lay = Image.new("RGBA", (FW, 260), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); w = text_w(ld, txt, f) + 70
        ld.rounded_rectangle([(FW - w) / 2, 30, (FW + w) / 2, 170], 16, outline=RED, width=10, fill=(255, 255, 255, 240))
        ld.text((FW / 2, 103), txt, font=f, fill=RED, anchor="mm")
        if e.get("sub") and room > 210: ld.text((FW / 2, 200), e["sub"][:48], font=font(DEMI, 30), fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
        lay = lay.rotate(-4 if e.get("side") != "R" else 4, resample=Image.BICUBIC, center=(FW / 2, 100))
        if s != 1.0: lay = lay.resize((int(FW * s), int(260 * s)), Image.LANCZOS)
        im.alpha_composite(lay, (int((FW - lay.width) / 2), int(top - 30 + 130 * (1 - s))))
    elif cd["type"] in ("pills", "split", "checklist"):
        if cd["type"] == "pills": rows = [it[0] for it in e["items"]]; ts = cd["sub"].get("items") or [0.0] * len(rows)
        elif cd["type"] == "split": rows = [it[0] if isinstance(it, list) else it for it in e["items"]]; ts = cd["sub"].get("items") or [k * 0.5 for k in range(len(rows))]
        else: rows = [r[0] for r in e["rows"]]; ts = [cd["sub"].get(r[2], k * 0.6) for k, r in enumerate(e["rows"])]
        title = e.get("title") if cd["type"] != "pills" else None
        n = max(1, min(len(rows), int((room - (74 if title else 0)) // 84)))
        rows, ts = rows[:n], ts[:n]; y = top
        if title: d.text((FW / 2, y + 30), title.upper(), font=font(DIN, 76), fill=YEL, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0)); y += 74
        for k, (r, rt) in enumerate(zip(rows, ts)):
            if lt < rt: continue
            sc = min(1.0, 0.6 + 0.4 * spring(lt - rt))
            plate(im, FW / 2, y + k * 84, [r], fit(d, r, HEAVY, 52, FW - 200), pad=(30, 10), scale=sc, radius=32)


L_CUR = None   # the reel being drawn (kinetic covers read its captions)


def full_card(c, cd, t):
    """Big long-form cards rebuilt as full 9:16 frames for at most 2.5 s (bigger type, fewer elements); None = no picture."""
    e, lt = cd["ev"], t - cd["t0"]; im = dark_bg(); d = ImageDraw.Draw(im); typ = cd["type"]
    push = 1.0   # 11-07 no zooming (was a 2% slow dolly on every full-frame card)
    title = e.get("title")
    if title: d.text((FW / 2, 330), title, font=fit(d, title, HEAVY, 74, FW - 140), fill=WHITE, anchor="mm")
    if typ == "kinetic":   # his words, big (the caption of that moment), on a dark frame
        ch = next((h for h in L_CUR["chunks"] if h["t0"] <= t < h["t1"]), None) if L_CUR else None
        if ch:
            ws = [w["w"] for w in ch["words"]]; live = max([k for k, w in enumerate(ch["words"]) if w["t"] <= t] or [0])
            f = fit(d, max(ws, key=len), HEAVY, 150, FW - 160); sc = min(1.0, 0.82 + 0.18 * spring(lt))
            for k, w in enumerate(ws):
                y = 960 + (k - (len(ws) - 1) / 2) * 175
                shadow_text(im, (FW / 2, y), w.upper(), font(HEAVY, int(f.size * sc)), YEL if k == live else WHITE, stroke=6)
        return im
    if typ == "fullquote":   # the chest card that was showing, full screen
        e = cd["ev"]; src = cd.get("src")
        if src in ("facequote", "selfquote"): txt = e.get("text", "").replace("\n", " ")
        elif src == "stamp": txt = e.get("text", "").replace("\n", " ")
        elif src == "pills": txt = " · ".join(it[0] for it in e.get("items", [])[:2])
        elif src == "checklist": txt = (e.get("title") or "") + ": " + ", ".join(r[0] for r in e.get("rows", [])[:3])
        else: txt = (e.get("title") or "") + " " + " · ".join((it[0] if isinstance(it, list) else it) for it in e.get("items", [])[:3])
        import textwrap
        own = e.get("text", "").split("\n") if src in ("facequote", "selfquote", "stamp") and "\n" in e.get("text", "") else None
        lines = [l for l in (own or textwrap.wrap(txt.strip(), 16)) if l.strip()][:5]; f = fit(d, max(lines, key=len), HEAVY, 110, FW - 140)
        sc = min(1.0, 0.85 + 0.15 * spring(lt)); f = font(HEAVY, int(f.size * sc)); lh = int(f.size * 1.18)
        for k, l in enumerate(lines):
            shadow_text(im, (FW / 2, 900 + (k - (len(lines) - 1) / 2) * lh), l, f, YEL if k == len(lines) - 1 else WHITE, stroke=5)
        return im
    if typ == "num":
        items = e["items"][:2]
        for k, it in enumerate(items):
            at = cd["sub"].get("b", 0.0) if k else 0.0
            if lt < at: continue
            y = 640 + k * 420; sc = min(1.0, 0.5 + 0.5 * spring(lt - at))
            f = font(DIN, int(230 * sc)); d.text((FW / 2, y), it[0], font=f, fill=YEL if k == len(items) - 1 else WHITE, anchor="mm")
            d.text((FW / 2, y + 150), it[1][:44], font=fit(d, it[1][:44], DEMI, 38, FW - 160), fill=(205, 205, 205), anchor="mm")
    elif typ == "versus":
        items = e["items"][:3]; n = len(items); cw = (FW - 120) // n
        for k, it in enumerate(items):
            at = cd["sub"].get(it[3], 0.0) if len(it) > 3 else 0.0
            if lt < at: continue
            x = 60 + k * cw + cw // 2; sc = min(1.0, 0.6 + 0.4 * spring(lt - at))
            if it[0]:
                ph = img(asset(c, it[0])).copy(); ph.thumbnail((cw - 30, 560)); card = Image.new("RGBA", (cw - 20, 600), (255, 255, 255, 255))
                card.paste(ph, ((cw - 20 - ph.width) // 2, (600 - ph.height) // 2)); im.alpha_composite(card, (x - (cw - 20) // 2, 470))
                y = 1150
            else: y = 820
            d.text((x, y), it[1], font=fit(d, it[1], DIN, int((150 if n == 2 else 120) * sc), cw - 24), fill=YEL if k == 0 else WHITE, anchor="mm")
            d.text((x, y + 110), it[2][:30], font=fit(d, it[2][:30], DEMI, 36, cw - 20), fill=(210, 210, 210), anchor="mm")
    elif typ == "stat_bars":
        bars = e["bars"][:4]; mx = max(b[1] for b in bars); ts = cd["sub"].get("bars") or [k * 0.3 for k in range(len(bars))]
        for k, b in enumerate(bars):
            bt = ts[k] if k < len(ts) else 0.0
            if lt < bt: continue
            y = 520 + k * 220; g = spring(lt - bt, w=14, z=0.8); wbar = (FW - 160 - 250) * b[1] / mx * min(g, 1.0)
            d.text((80, y), b[0], font=fit(d, b[0], HEAVY, 46, FW - 160), fill=WHITE, anchor="lm")
            d.rounded_rectangle([80, y + 44, 80 + max(wbar, 14), y + 134], 16, fill=YEL if k == len(bars) - 1 else (235, 235, 235))
            d.text((100 + wbar, y + 89), b[2], font=fit(d, b[2], DIN, 84, 230), fill=YEL if k == len(bars) - 1 else WHITE, anchor="lm")
    elif typ == "study":
        st = e["study"]; card = Image.new("RGBA", (FW - 120, 820), (250, 248, 242, 255)); cdd = ImageDraw.Draw(card)
        cdd.text((50, 60), f"{st['journal']} · {st['year']}", font=font(DEMI, 40), fill=(90, 90, 90))
        import textwrap
        for k, l in enumerate(textwrap.wrap(st["title"], 28)[:4]): cdd.text((50, 140 + k * 72), l, font=font(HEAVY, 54), fill=INK)
        fnd = st.get("finding", ""); hl = st.get("hl", "")
        for k, l in enumerate(textwrap.wrap(fnd, 34)[:4]):
            y = 470 + k * 64
            if hl and hl in l and lt > 0.4:
                x0 = 50 + cdd.textlength(l[:l.index(hl)], font=font(DEMI, 44)); x1 = x0 + cdd.textlength(hl, font=font(DEMI, 44)) * min(1, (lt - 0.4) / 0.4)
                cdd.rectangle([x0 - 6, y - 4, x1 + 6, y + 54], fill=YEL)
            cdd.text((50, y), l, font=font(DEMI, 44), fill=INK)
        im.alpha_composite(card, (60, 380))
    elif typ == "doc":
        pg = e.get("page")
        if pg:
            page = img(asset(c, pg["img"])); hl = pg.get("hl") or []
            # the highlighted lines big enough to read on a phone: a window about 1.2x the highlight's width, never the whole page
            if hl:
                hx0, hy0 = min(x for x, y, w, h in hl), min(y for x, y, w, h in hl); hx1, hy1 = max(x + w for x, y, w, h in hl), max(y + h for x, y, w, h in hl)
            else: hx0, hy0, hx1, hy1 = 0, page.height * 0.4, page.width, page.height * 0.6
            lh = max(h for x, y, w, h in hl) if hl else 60   # the highlighted lines and about one line around them: big enough to read
            vw = min(page.width, (hx1 - hx0) + 2 * lh); vh = (hy1 - hy0) + 3.2 * lh
            x0 = min(max(hx0 - lh, 0), page.width - vw); y0 = min(max(hy0 - 1.6 * lh, 0), page.height - vh)
            s = (FW - 80) / vw; H2 = int(vh * s); crop = page.crop((int(x0), int(y0), int(x0 + vw), int(y0 + vh))).resize((FW - 80, H2), Image.LANCZOS)
            crop = crop.convert("RGBA"); hlay = Image.new("RGBA", crop.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(hlay)
            at = cd["sub"].get("hl", 0.3)
            for x, y, w, h in hl:
                g = min(1.0, max(0.0, (lt - at) / 0.45))
                if g > 0: hd.rectangle([(x - x0) * s, (y - y0) * s, (x - x0 + w * g) * s, (y - y0 + h) * s], fill=(255, 212, 0, 120))
            crop.alpha_composite(hlay); frame = Image.new("RGBA", (crop.width + 24, crop.height + 24), (255, 255, 255, 255)); frame.alpha_composite(crop, (12, 12))
            im.alpha_composite(frame, (28, int(860 - frame.height / 2)))
            src = e.get("source", "")
            if src: d.text((FW / 2, 400), src[:52], font=fit(d, src[:52], HEAVY, 46, FW - 120), fill=WHITE, anchor="mm")
            if e.get("source_sub"): d.text((FW / 2, 1320), e["source_sub"][:60], font=fit(d, e["source_sub"][:60], DEMI, 36, FW - 140), fill=(210, 210, 210), anchor="mm")
        elif e.get("doc"):
            dc = e["doc"]; import textwrap
            card = Image.new("RGBA", (FW - 120, 900), (250, 248, 242, 255)); cdd = ImageDraw.Draw(card)
            cdd.text((50, 60), dc.get("source", "")[:40], font=font(DEMI, 36), fill=(90, 90, 90))
            for k, l in enumerate(textwrap.wrap(dc.get("title", ""), 30)[:2]): cdd.text((50, 130 + k * 66), l, font=font(HEAVY, 50), fill=INK)
            for k, l in enumerate(textwrap.wrap(dc.get("text", ""), 36)[:7]): cdd.text((50, 300 + k * 62), l, font=font(DEMI, 42), fill=INK)
            im.alpha_composite(card, (60, 380))
        else: return None
    elif typ == "photo_full":
        ph = cover(img(asset(c, e["image"])), FW, FH, tuple(e.get("focal") or (0.5, 0.5))).convert("RGBA")
        if push != 1.0: ph = ph.resize((int(FW * push), int(FH * push)), Image.LANCZOS).crop((int(FW * (push - 1) / 2), int(FH * (push - 1) / 2), int(FW * (push - 1) / 2) + FW, int(FH * (push - 1) / 2) + FH))
        im = ph; im.alpha_composite(Image.new("RGBA", (FW, FH), (0, 0, 0, 60)))
        lines = [x for x in (e.get("title"), e.get("sub")) if x]
        if lines: plate(im, FW / 2, TITLE_Y, lines, fit(ImageDraw.Draw(im), max(lines, key=len), HEAVY, 58, FW - 200))
        return im
    if typ != "photo_full" and push != 1.0:
        im = im.resize((int(FW * push), int(FH * push)), Image.LANCZOS).crop((int(FW * (push - 1) / 2), int(FH * (push - 1) / 2), int(FW * (push - 1) / 2) + FW, int(FH * (push - 1) / 2) + FH))
    return im


def chip_text(tag, sub):
    sub = (sub or "").replace(" · link in the description", "").replace("link in the description", "").strip(" ·")
    return f"{tag} · {sub}" if sub else tag


def tag_chip(im, tag, sub, y):
    d = ImageDraw.Draw(im); s = chip_text(tag, sub); f = fit(d, s, DEMI, 34, FW - 200); w = text_w(d, s, f) + 50
    d.rounded_rectangle([(FW - w) / 2, y, (FW + w) / 2, y + 66], 22, fill=(255, 255, 255, 240)); d.text((FW / 2, y + 33), s, font=f, fill=INK, anchor="mm")


# ---------------------------------------------------------------------------------------------------- frame 1 (the versions)
def intro_end(shots, cut):
    """Frame 1's opening lasts until the first cut after 1.8 s (the hook line plays under it)."""
    for s in shots:
        if s["t1"] >= INTRO_MIN: return s["f0"] + s["n"], s["t1"]
    return shots[-1]["f0"] + shots[-1]["n"], shots[-1]["t1"]


def ob_frame(c, s, t_src, box_w=None):
    """One graded camera frame: the 9:16 crop for a body shot, or the whole 16:9 frame at box_w wide (small-face openings)."""
    vf = (f"scale={box_w}:-2:flags=lanczos" if box_w else f"crop={s['crop'][0]}:{s['crop'][1]}:{s['crop'][2]}:{s['crop'][3]},scale={FW}:{FH}:flags=lanczos")
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.png")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t_src:.3f}", "-i", c["camera"], "-i", c["lut"], "-filter_complex",
             f"[0:v]{vf}[a];[a][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", p])
        return Image.open(p).convert("RGBA")


def content_box(fr):
    """The picture inside a vertical phone video saved in a 16:9 file (black or blurred side bars), or None. Bars are columns
    with almost no detail: black ones are dark, the long-form's blurred fill is soft (its sharpness a fraction of the middle's)."""
    a = np.asarray(fr.convert("L").resize((480, 270)), np.float32); W = a.shape[1]
    det = np.abs(np.diff(a, axis=0)).mean(0) + np.append(np.abs(np.diff(a, axis=1)).mean(0), 0.0)
    det = np.convolve(det, np.ones(9) / 9, "same")
    live = np.flatnonzero((det > 0.25 * np.percentile(det, 95)) & (a.mean(0) > 14))
    if len(live) == 0: return None
    x0, x1 = int(live[0]), int(live[-1]) + 1
    if (x1 - x0) >= 0.7 * W: return None
    sc = fr.width / W; return (int(x0 * sc), 0, int(x1 * sc), fr.height)


def video_frame(path, t, box=True, w=FW, lower_third=False):
    """A frame of a B-roll or clip file: boxed full width over its own blurred fill (box), or cover-cropped to 9:16. A vertical
    video inside black side bars fills the 9:16 frame instead of shrinking into a box; lower_third=True keeps a cover crop above
    a TV lower third (the bottom quarter), which a 9:16 crop would cut off mid-word."""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.png")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", path, "-frames:v", "1", p])
        fr = Image.open(p).convert("RGB")
    cb = content_box(fr)
    if cb: return cover(fr.crop(cb), FW, FH).convert("RGBA")
    if lower_third: fr = fr.crop((0, 0, fr.width, int(fr.height * 0.74)))
    return boxed(fr) if box else cover(fr, FW, FH).convert("RGBA")


def boxed(fr, y=None):
    bg = cover(fr, FW, FH).filter(ImageFilter.GaussianBlur(38)); bg = Image.blend(bg, Image.new("RGB", (FW, FH)), 0.45).convert("RGBA")
    bx = fr.resize((FW, int(fr.height * FW / fr.width)), Image.LANCZOS)
    bg.paste(bx, (0, y if y is not None else int((FH - bx.height) / 2 - 140)))
    return bg


# ---------------------------------------------------------------------------------------------------- the split
_FOOT, _DUR = {}, {}
def footage(c, path):
    """How a clip or B-roll fills the split's top half, or None for vertical footage (it fills the frame instead). The default
    fills 1080x960 edge to edge around the middle, as his reference does with TV footage; clipper.json "split" overrides per
    file: crop [x0, y0, x1, y1] (fractions: trims a TV lower third so it isn't cut mid-word), fx (where the crop sits, left to
    right), fit (a wide graphic keeps its whole width over its own blur) or card (a title too small to read, rebuilt)."""
    if path in _FOOT: return _FOOT[path]
    box, (W, H) = probe_box(path, 1.0)
    o = (c.get("split") or {}).get(os.path.splitext(os.path.basename(path))[0], {})
    if box: v = None
    elif o.get("card"): v = dict(mode="card", text=o["card"])
    else:
        x0, y0, x1, y1 = o.get("crop") or (0, 0, 1, 1); rx, ry, rw, rh = x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H
        if o.get("fit"):   # whole width, centred between Instagram's top bar and the seam caption
            hh = int(round(rh * FW / rw / 2) * 2); v = dict(mode="fit", rect=[int(rw), int(rh), int(rx), int(ry)], h=hh, y=int(min(max(560 - hh / 2, 0), SEAM - hh)))
        else:
            A = FW / SEAM
            if rw / rh > A: cw, ch = rh * A, rh; cx, cy = rx + (rw - cw) * o.get("fx", 0.5), ry
            else: cw, ch = rw, rw / A; cx, cy = rx, ry + (rh - ch) * o.get("fy", 0.5)
            v = dict(mode="cover", rect=[int(cw), int(ch), int(cx), int(cy)])
    _FOOT[path] = v
    return v


def dur(path):
    if path not in _DUR: _DUR[path] = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())
    return _DUR[path]


_END = {}
def clean_end(path):
    """Seconds into a clip where its last clean frame ends: the long-form's B-roll can end in a blur or a fade (B_LK_BODY blurs
    over its last 6 frames), and a split that outlasts its footage holds this frame instead."""
    if path not in _END:
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", "scale=320:180,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        fr = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32); n = len(fr)
        sh = np.array([np.abs(np.diff(f, axis=1)).mean() + np.abs(np.diff(f, axis=0)).mean() for f in fr]); lu = fr.mean(axis=(1, 2))
        ref = slice(max(0, n - 30), max(1, n - 8)); rs, rl = np.median(sh[ref]), np.median(lu[ref]); k = n - 1
        while k > n - 30 and (abs(sh[k] - rs) > 0.1 * rs or abs(lu[k] - rl) > 0.06 * rl): k -= 1
        _END[path] = min(dur(path) - 0.1, (k + 1) * 1001 / 30000)
    return _END[path]


def top_filter(v, trim):
    """ffmpeg chain from input 0 to [top], the footage's 1080x960 half; it stops `trim` s after the seek and its last frame holds."""
    src = f"[0:v]trim=end={trim:.4f},setpts=PTS-STARTPTS,fps=30000/1001,tpad=stop_mode=clone:stop_duration=60"
    if v["mode"] == "card": return f"{src},scale={FW}:{SEAM},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill[top]"
    w, h, x, y = v["rect"]; src += f",crop={w}:{h}:{x}:{y}"
    if v["mode"] == "cover": return f"{src},scale={FW}:{SEAM}:flags=lanczos[top]"
    return (f"{src},split[ta][tb];[ta]scale={FW}:{SEAM}:force_original_aspect_ratio=increase,crop={FW}:{SEAM},gblur=sigma=30,"
            f"eq=brightness=-0.09[tbg];[tb]scale={FW}:{v['h']}:flags=lanczos[tfg];[tbg][tfg]overlay=0:{v['y']}[top]")


def split_args(c, v, path, t, shot=None, tc=None):
    """Inputs and filter graph of one split picture: the footage on top from second t, and under it him at camera second tc
    (the shot's split crop, graded) or, with no shot, the dark panel his words go on. Stills and the render share it."""
    end = clean_end(path); t = min(max(t, 0), end - 0.04)   # past its clean end the footage holds (a seek past the end gave a black half)
    ins = ["-ss", f"{t:.4f}", "-i", path]; g = top_filter(v, end - t)
    if shot is None: return ins, f"{g};[top]pad={FW}:{FH}:0:0:0x111114,format=rgb24"
    w, h, x, y = shot["scrop"]
    ins += ["-ss", f"{tc - 0.25 / c['fps']:.4f}", "-i", c["camera"], "-i", c["lut"]]
    return ins, (f"{g};[1:v]crop={w}:{h}:{x}:{y},scale={FW}:{FH - SEAM}:flags=lanczos[b0];[b0][2:v]haldclut=interp=tetrahedral[bot];"
                 f"[top][bot]vstack=2,format=rgb24")


def split_still(c, v, path, t, shot=None, tc=None):
    ins, g = split_args(c, v, path, t, shot, tc)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.png"); run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + ins + ["-filter_complex", g, "-frames:v", "1", p])
        return Image.open(p).convert("RGBA")


def credit_lines(tag, sub):
    """The split's source credit: one line if it fits at 34 px, else the tag over the sub (GEBN's "funded by Coca-Cola" ran off)."""
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8))); one = chip_text(tag, sub); sub = chip_text("", sub).strip(" ·")
    return [one] if not sub or text_w(d, one, font(DEMI, 34)) <= FW - 150 else [tag, sub]


def credit_size(tag, sub):
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8))); lines = credit_lines(tag, sub)
    return max(text_w(d, l, fit(d, l, DEMI, 34, FW - 150)) for l in lines) + 50, 22 + 44 * len(lines)


def credit(im, tag, sub, y, x=30):
    """The split's source credit, left-aligned on the footage."""
    d = ImageDraw.Draw(im); lines = credit_lines(tag, sub); w, h = credit_size(tag, sub)
    d.rounded_rectangle([x, y, x + w, y + h], 22, fill=(255, 255, 255, 240))
    for k, l in enumerate(lines): d.text((x + 25, y + 33 + 44 * k), l, font=fit(d, l, DEMI, 34, FW - 150), fill=INK, anchor="lm")


_SPOT = {}
def tag_spot(c, v, path, t0, t1, tag, sub):
    """Where the source credit sits on the footage: top left, under Instagram's top bar, unless a face in the footage is there at
    the start or end of the shot (the Liver King portrait, 10-28: never text over a face); then bottom left, over the captions."""
    key = (path, round(t0, 2), round(t1, 2), tag, sub)
    if key in _SPOT: return _SPOT[key]
    y = SPLIT_TAG_Y; w, h = credit_size(tag, sub)
    if v["mode"] != "card":
        r = (10, SPLIT_TAG_Y - 20, 50 + w, SPLIT_TAG_Y + h + 20)
        with tempfile.TemporaryDirectory() as td:
            ps = []
            for k, t in enumerate((t0, t1)):
                p = os.path.join(td, f"t{k}.png"); split_still(c, v, path, t).crop((0, 0, FW, SEAM)).save(p); ps.append(p)
            for line in run([os.path.join(BIN, "faces")] + ps).splitlines():
                rest = line.split(" ", 1)[1].strip()
                if rest in ("none", "error"): continue
                for b in rest.split("|"):
                    x0, y0, x1, y1 = [float(q) for q in b.split()]
                    if x0 < r[2] and x1 > r[0] and y0 < r[3] and y1 > r[1]: y = SPLIT_CAP_Y - 45 - 20 - h
    _SPOT[key] = y
    return y


def footage_of(c, L):
    """Each clip's and B-roll card's view in the split (None: vertical, it fills the frame) and its credit's place, and where
    each B-roll card starts in its file: a card touching the same B-roll carries on from it, any other picks up where that B-roll
    last stopped, so a clip flashed four times shows four moments instead of the same one (R5's aisle, 10-28)."""
    for s in L["shots"]:
        if s["kind"] != "clip": continue
        p = os.path.join(c["longform"], "hf", "assets", "clips", s["clip"] + ".mp4"); s["view"] = footage(c, p)
        if s["view"]: s["tag_y"] = tag_spot(c, s["view"], p, s["a"], s["b"] - 0.05, s.get("tag", ""), s.get("sub", ""))
    last, cur = {}, {}
    for cd in sorted((x for x in L["cards"] if x["kind"] == "video"), key=lambda x: x["t0"]):
        p = asset(c, f"broll/{cd['ev']['broll']}.mp4"); cd["view"] = footage(c, p); n = cd["t1"] - cd["t0"]; pv = last.get(p)
        if pv is not None and cd["t0"] <= pv["t1"] + 0.15: cd["boff"] = round(pv["boff"] + cd["t0"] - pv["t0"], 3)
        else: o = cur.get(p, 0.2); cd["boff"] = round(o if o + n <= dur(p) - 0.05 else 0.2, 3)
        cur[p] = max(cur.get(p, 0.0), cd["boff"] + n)
        if pv is None or cd["t1"] > pv["t1"]: last[p] = cd
        if cd["view"]: cd["tag_y"] = tag_spot(c, cd["view"], p, cd["boff"], min(cd["boff"] + n, dur(p) - 0.05), cd["ev"].get("tag", ""), cd["ev"].get("sub", ""))


def split_at(L, t):
    """The split at reel time t: ("ob", src) with him under the footage, ("words", src) with words under it (a look-off cover,
    or a clip playing its own sound), else (None, None). src is the B-roll card or clip shot the footage comes from."""
    s = shot_at(L, t)
    if s["kind"] == "clip": return ("words", s) if s.get("view") else (None, None)
    cd = at(L, t)
    if cd is not None and cd["kind"] == "video" and cd.get("view"): return ("words" if cd["id"].startswith("COVER") else "ob"), cd
    return None, None


def intro_image(c, r, v, t, shots):
    """The opening picture of version v at reel time t (0 .. intro end): no face, small face or two faces."""
    k = v["frame1"]; push = 1.0 if os.environ.get("YTCLIP_NO_PUSH") else 1.0 + 0.035 * min(t / 2.5, 1.0)   # a slow linear dolly so frame 1 isn't a still (YTCLIP_NO_PUSH=1: none, OB 11-07 no zoom; set for 2026-11-09-breakfast-clip)
    def dolly(im):
        if push == 1.0: return im
        W, H = int(FW * push), int(FH * push)
        return im.resize((W, H), Image.LANCZOS).crop(((W - FW) // 2, (H - FH) // 2, (W - FW) // 2 + FW, (H - FH) // 2 + FH))
    s0 = shots[0]; src_t = s0["a"] - LEAD + min(t, s0["b"] - s0["a"] - 0.04)   # the lead shows him just before his first word
    if k == "noface":
        if v.get("image") and v.get("box"):   # a photo with a face in it stays boxed, so that face stays small (RULEBOOK: no big face in frame 1)
            return dolly(boxed(img(asset(c, v["image"])), y=600))
        if v.get("image"):
            im = cover(img(asset(c, v["image"])), FW, FH).convert("RGBA"); im.alpha_composite(Image.new("RGBA", (FW, FH), (0, 0, 0, 70))); return dolly(im)
        if v.get("broll"):
            return dolly(video_frame(asset(c, f"broll/{v['broll']}.mp4"), t + 0.3, box=False, lower_third=True))
        if v.get("card") == "steps":
            im = dark_bg(); d = ImageDraw.Draw(im)
            for k2, (lab, num, col) in enumerate((("The average American", "4,800", WHITE), ("Old Order Amish men", "18,000", YEL))):
                y = 760 + k2 * 360; d.text((FW / 2, y), num, font=font(DIN, 230), fill=col, anchor="mm")
                d.text((FW / 2, y + 140), lab + ", steps a day", font=font(DEMI, 44), fill=(215, 215, 215), anchor="mm")
            return dolly(im)
    if k == "smallface":
        fr = ob_frame(c, s0, src_t, box_w=FW).convert("RGB")
        return boxed(fr, y=600)
    if k == "twoface":
        bg = dark_bg(); src = cover(img(asset(c, v["image"])), FW, 540).convert("RGBA"); bg.alpha_composite(src, (0, 520))
        fr = ob_frame(c, s0, src_t, box_w=900).convert("RGBA"); bg.alpha_composite(fr, ((FW - fr.width) // 2, 1080))
        ImageDraw.Draw(bg).rectangle([0, 1060, FW, 1080], fill=YEL)
        return bg
    raise ValueError(f"unknown frame 1 {v}")


# ---------------------------------------------------------------------------------------------------- the layout
def layout(c, r):
    """Everything the compositor needs for reel r: shots, crops, chin lines, cards, caption chunks, the intro's end."""
    import ytclip
    d = os.path.join(c["work"], "reels", r["id"]); cut = json.load(open(os.path.join(d, "cut.json")))
    shots, nf = timeline(c, cut); faces_of(c, shots); crops(shots); split_crops(shots)
    cards = events_in(c, cut, shots); ws = words_reel(c, cut, shots); chs = chunks(ws)
    fi, ti = intro_end(shots, cut)
    clipev = {e["clip"]: e for e in json.load(open(os.path.join(c["longform"], "events_resolved.json")))["events"] if e["type"] == "clip"}
    for s in shots:
        if s["kind"] == "clip": s["tag"] = clipev.get(s["clip"], {}).get("tag", ""); s["sub"] = clipev.get(s["clip"], {}).get("sub", "")
    cards = [cd for cd in cards if cd["t0"] >= ti - 0.05]   # frame 1's opening owns the screen until its cut
    L = dict(reel=r["id"], frames=nf, fps=c["fps"], intro_frames=fi, intro_end=ti, shots=shots, cards=cards, chunks=chs, words=ws)
    footage_of(c, L)   # before the covers: in the split a B-roll no longer hides him, so its cut edges count as visible
    lp = os.path.join(d, "lookoff.json")
    if os.path.exists(lp): L["covers"] = len(add_covers(L, json.load(open(lp)))); footage_of(c, L)
    global L_CUR; L_CUR = L
    json.dump(L, open(os.path.join(d, "layout.json"), "w"), indent=1, default=str)
    return L


def at(L, t, kind=None):
    hits = [cd for cd in L["cards"] if cd["t0"] <= t < cd["t1"] and (kind is None or cd["kind"] == kind)]
    return next((cd for cd in hits if cd["id"].startswith("COVER")), hits[0] if hits else None)


def shot_at(L, t):
    for s in L["shots"]:
        if s["t0"] <= t < s["t1"] + 1e-6: return s
    return L["shots"][-1]


def overlay(c, L, base, t, version=None, r=None):
    """Graphics on top of the base picture at reel time t: the title (frame 1's opening), chest cards, full cards, the
    clip/B-roll source tag and the captions (always last: y 1428, or on the seam in the split)."""
    im = base; mode = None
    if version is not None and t < L["intro_end"]:
        draw_title(im, r["titles"][version["title"]], version.get("chip"))
    else:
        s = shot_at(L, t); cd = at(L, t); mode, src = split_at(L, t)
        if mode:
            ev = src.get("ev") or src
            if src["view"]["mode"] == "card": card_top(im, src["view"]["text"], t - src["t0"])
            credit(im, ev.get("tag", ""), ev.get("sub", ""), src.get("tag_y", SPLIT_TAG_Y))
            if mode == "words":
                ch = next((h for h in L["chunks"] if h["t0"] <= t < h["t1"]), None)
                words_half(im, ch, t, t - max(ch["t0"], src["t0"]) if ch else 0); return im
        elif cd is not None and cd["kind"] == "full":
            fc = full_card(c, cd, t)
            if fc is not None: im = fc
        elif cd is not None and cd["kind"] == "video":
            tag_chip(im, cd["ev"].get("tag", ""), cd["ev"].get("sub", ""), 1250)
        elif cd is not None and cd["kind"] == "chest" and s["kind"] == "ob":
            chest_card(im, cd, t, s["chin"])
        if s["kind"] == "clip" and not mode: tag_chip(im, s.get("tag", ""), s.get("sub", ""), 1250)
    q = at(L, t, "chest") if (version is None or t >= L["intro_end"]) else None
    cv = at(L, t) if (version is None or t >= L["intro_end"]) else None
    if cv is not None and cv["type"] == "kinetic": return im
    if q is not None and q["type"] in ("facequote", "selfquote") and shot_at(L, t)["kind"] == "ob" and (cv is None or cv["kind"] != "full") and not mode: return im
    ch = next((h for h in L["chunks"] if h["t0"] <= t < h["t1"]), None)
    if ch is not None: draw_caption(im, ch, t, SPLIT_CAP_Y if mode == "ob" else CAP_Y)
    return im


def base_still(c, L, t, version=None, r=None):
    """The base picture at reel time t, one frame (for the stills OB approves; the render decodes whole shots instead)."""
    if version is not None and t < L["intro_end"]: return intro_image(c, r, version, t, L["shots"])
    mode, src = split_at(L, t); s = shot_at(L, t)
    if mode:
        if src is s: path, tb = os.path.join(c["longform"], "hf", "assets", "clips", s["clip"] + ".mp4"), s["a"] + (t - s["t0"])
        else: path, tb = asset(c, f"broll/{src['ev']['broll']}.mp4"), src["boff"] + (t - src["t0"])
        return split_still(c, src["view"], path, tb, s if mode == "ob" else None, s["a"] + (t - s["t0"]))
    cd = at(L, t, "video")
    if cd is not None:
        return video_frame(asset(c, f"broll/{cd['ev']['broll']}.mp4"), cd.get("boff", 0.2) + (t - cd["t0"]), box=True)
    if s["kind"] == "clip": return video_frame(os.path.join(c["longform"], "hf", "assets", "clips", s["clip"] + ".mp4"), s["a"] + (t - s["t0"]), box=True)
    return ob_frame(c, s, s["a"] + (t - s["t0"]))


# ---------------------------------------------------------------------------------------------------- render
class Layers:
    """The last drawn state of each overlay (title, tag, chest card, caption) as a transparent full frame, redrawn only when its
    state changes: captions change per word, cards per frame only while their spring moves (about 0.5 s)."""
    def __init__(self): self.cache = {}
    def get(self, kind, key, draw):
        k = self.cache.get(kind)
        if k is not None and k[0] == key: return k[1]
        lay = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); draw(lay); self.cache[kind] = (key, lay); return lay


def compose(c, L, base, t, fi, layers, version=None, r=None):
    """One finished frame: base picture (RGBA) + overlays, exactly as overlay() draws the stills."""
    im, lays = base, []; mode = None
    intro = version is not None and t < L["intro_end"]
    if intro:
        lays.append(layers.get("title", version["id"], lambda l: draw_title(l, r["titles"][version["title"]], version.get("chip"))))
    else:
        s = shot_at(L, t); cd = at(L, t); mode, src = split_at(L, t)
        if mode:
            ev = src.get("ev") or src; sid = src.get("id") or f"{src['clip']}@{src['f0']}"
            if src["view"]["mode"] == "card":
                k = min(int(round((t - src["t0"]) * L["fps"])), 12)
                lays.append(layers.get("fcard", (sid, k), lambda l: card_top(l, src["view"]["text"], k / L["fps"])))
            ty = src.get("tag_y", SPLIT_TAG_Y)
            lays.append(layers.get("tag", ("split", ev.get("tag", ""), ev.get("sub", ""), ty), lambda l: credit(l, ev.get("tag", ""), ev.get("sub", ""), ty)))
        elif cd is not None and cd["kind"] == "full":
            fc = full_card(c, cd, t)
            if fc is not None: im = fc
        elif cd is not None and cd["kind"] == "video":
            lays.append(layers.get("tag", cd["id"], lambda l: tag_chip(l, cd["ev"].get("tag", ""), cd["ev"].get("sub", ""), 1250)))
        elif cd is not None and cd["kind"] == "chest" and s["kind"] == "ob":
            k = min(int(round((t - cd["t0"]) * L["fps"])), 18)
            lays.append(layers.get("chest", (cd["id"], k, round(s["chin"])), lambda l: chest_card(l, cd, cd["t0"] + k / L["fps"], s["chin"])))
        if s["kind"] == "clip" and not mode: lays.append(layers.get("tag", s["clip"], lambda l: tag_chip(l, s.get("tag", ""), s.get("sub", ""), 1250)))
        q = at(L, t, "chest")
        if mode == "words":   # his (or the clip's) words fill the bottom half instead of the caption line
            ch = None; hw = next(((k, h) for k, h in enumerate(L["chunks"]) if h["t0"] <= t < h["t1"]), None)
            if hw is not None:
                k, h = hw; live = max([j for j, w in enumerate(h["words"]) if w["t"] <= t] or [0]); t0 = max(h["t0"], src["t0"])
                n = min(int(round((t - t0) * L["fps"])), 12)
                lays.append(layers.get("half", (k, live, n, t0), lambda l: words_half(l, h, h["words"][live]["t"], n / L["fps"])))
        elif cd is not None and cd["type"] == "kinetic": ch = None
        elif q is not None and q["type"] in ("facequote", "selfquote") and s["kind"] == "ob" and (cd is None or cd["kind"] != "full") and not mode: ch = None
        else: ch = next(((k, h) for k, h in enumerate(L["chunks"]) if h["t0"] <= t < h["t1"]), None)
    if intro: ch = next(((k, h) for k, h in enumerate(L["chunks"]) if h["t0"] <= t < h["t1"]), None)
    if ch is not None:
        k, h = ch; live = max([j for j, w in enumerate(h["words"]) if w["t"] <= t] or [0]); y = SPLIT_CAP_Y if mode == "ob" else CAP_Y
        lays.append(layers.get("cap", (k, live, y), lambda l: draw_caption(l, h, h["words"][live]["t"], y)))
    if im is base: im = base.copy()
    for l in lays: im.alpha_composite(l)
    return im


def segments(c, L, version=None, r=None, f_from=0, f_to=None):
    """The base picture as decode segments [f0, f1) in reel frames: his camera shots (cut where a B-roll card takes over),
    long-form clips, and frame 1's opening for a version."""
    fps = L["fps"]; f_to = L["frames"] if f_to is None else f_to; out = []
    if version is not None and f_from < L["intro_frames"]:
        out.append(dict(f0=f_from, f1=min(L["intro_frames"], f_to), kind="intro")); f_from = L["intro_frames"]
    vids = [cd for cd in L["cards"] if cd["kind"] == "video"]
    for s in L["shots"]:
        a, b = max(s["f0"], f_from), min(s["f0"] + s["n"], f_to)
        if a >= b: continue
        if s["kind"] == "clip":
            seg = dict(f0=a, f1=b, path=os.path.join(c["longform"], "hf", "assets", "clips", s["clip"] + ".mp4"), t=s["a"] + (a - s["f0"]) / fps)
            out.append(dict(seg, kind="split", view=s["view"]) if s.get("view") else dict(seg, kind="clip")); continue
        cuts = sorted({a, b} | {min(max(int(round(cd[x] * fps)), a), b) for cd in vids for x in ("t0", "t1")})
        for x, y in zip(cuts, cuts[1:]):
            if x >= y: continue
            cd = next((v for v in vids if v["id"].startswith("COVER") and v["t0"] * fps - 0.5 <= x < v["t1"] * fps - 0.5), None) or \
                 next((v for v in vids if v["t0"] * fps - 0.5 <= x < v["t1"] * fps - 0.5), None)
            if cd is not None:
                seg = dict(f0=x, f1=y, path=asset(c, f"broll/{cd['ev']['broll']}.mp4"), t=cd["boff"] + (x / fps - cd["t0"]))
                if not cd.get("view"): out.append(dict(seg, kind="broll"))
                elif cd["id"].startswith("COVER"): out.append(dict(seg, kind="split", view=cd["view"]))   # his words under it
                else: out.append(dict(seg, kind="split", view=cd["view"], shot=s, tc=s["a"] + (x - s["f0"]) / fps))
            else:
                out.append(dict(f0=x, f1=y, kind="ob", shot=s, t=s["a"] + (x - s["f0"]) / fps))
    return out


def probe_box(path, t):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.png")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", path, "-frames:v", "1", p])
        return content_box(Image.open(p).convert("RGB")), Image.open(p).size


def decode_cmd(c, seg, n, version=None):
    """ffmpeg that writes the segment's base picture as rgb24 frames (1080x1920 unless noted)."""
    fps = c["fps"]; rate = f"fps=30000/1001"
    def cam(t): return ["-ss", f"{t - 0.25 / fps:.4f}", "-i", c["camera"], "-i", c["lut"]]
    boxed_fg = f"[0:v]{rate},split[a][b];[a]scale=-2:{FH},crop={FW}:{FH},gblur=sigma=30,eq=brightness=-0.09[bg];[b]scale={FW}:-2[fg];[bg][fg]overlay=0:(H-h)/2-140,format=rgb24"
    if seg["kind"] == "split":
        ins, g = split_args(c, seg["view"], seg["path"], seg["t"], seg.get("shot"), seg.get("tc"))
        return ["ffmpeg", "-nostdin", "-v", "error"] + ins + ["-filter_complex", g, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH)
    if seg["kind"] == "ob":
        w, h, x, y = seg["shot"]["crop"]
        fg = f"[0:v]crop={w}:{h}:{x}:{y},scale={FW}:{FH}:flags=lanczos[a];[a][1:v]haldclut=interp=tetrahedral,format=rgb24"
        return ["ffmpeg", "-nostdin", "-v", "error"] + cam(seg["t"]) + ["-filter_complex", fg, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH)
    if seg["kind"] in ("clip", "broll"):
        box, size = probe_box(seg["path"], seg["t"])
        if box:   # a vertical phone video inside side bars fills the frame
            x0, y0, x1, y1 = box
            fg = f"[0:v]{rate},crop={x1 - x0}:{y1 - y0}:{x0}:{y0},scale={FW}:{FH}:force_original_aspect_ratio=increase,crop={FW}:{FH},format=rgb24"
        else: fg = boxed_fg
        return ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(seg['t'], 0):.4f}", "-stream_loop", "-1", "-i", seg["path"], "-filter_complex", fg,
                "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH)
    raise ValueError(seg["kind"])


def frames_of(cmd, size, n):
    """n RGBA frames from an ffmpeg rawvideo pipe (the last one repeats if the source runs short)."""
    W, H = size; fsz = W * H * 3; p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL); last = None
    for _ in range(n):
        buf = p.stdout.read(fsz)
        if len(buf) == fsz: last = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).convert("RGBA")
        yield last if last is not None else Image.new("RGBA", (W, H), (0, 0, 0, 255))
    p.stdout.close(); p.wait()


def intro_frames(c, L, r, v, n):
    """Frame 1's opening as frames: a still with a slow dolly, a B-roll above its lower third, or his 16:9 frame (small face,
    two faces), decoded once."""
    fps = L["fps"]; s0 = L["shots"][0]; k = v["frame1"]
    if k == "noface" and v.get("broll"):
        path = asset(c, f"broll/{v['broll']}.mp4")
        fg = f"[0:v]fps=30000/1001,crop=iw:ih*0.74:0:0,scale=-2:{FH},crop={FW}:{FH},format=rgb24"
        yield from frames_of(["ffmpeg", "-nostdin", "-v", "error", "-ss", "0.3", "-stream_loop", "-1", "-i", path, "-filter_complex", fg,
                              "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH), n); return
    if k == "noface":
        for f in range(n): yield intro_image(c, r, v, f / fps, L["shots"])
        return
    t0 = s0["a"] - LEAD - 0.25 / fps
    if k == "smallface":
        fg = (f"[0:v][1:v]haldclut=interp=tetrahedral,split[a][b];[a]scale=-2:{FH},crop={FW}:{FH},gblur=sigma=30,eq=brightness=-0.09[bg];"
              f"[b]scale={FW}:-2[fg];[bg][fg]overlay=0:600,format=rgb24")
        yield from frames_of(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t0:.4f}", "-i", c["camera"], "-i", c["lut"], "-filter_complex", fg,
                              "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH), n); return
    if k == "twoface":
        bg = dark_bg(); src = cover(img(asset(c, v["image"])), FW, 540).convert("RGBA"); bg.alpha_composite(src, (0, 520))
        ImageDraw.Draw(bg).rectangle([0, 1060, FW, 1080], fill=YEL)
        fg = "[0:v]scale=900:506:flags=lanczos[a];[a][1:v]haldclut=interp=tetrahedral,format=rgb24"
        for fr in frames_of(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t0:.4f}", "-i", c["camera"], "-i", c["lut"], "-filter_complex", fg,
                             "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (900, 506), n):
            im = bg.copy(); im.alpha_composite(fr, ((FW - 900) // 2, 1080)); yield im
        return
    raise ValueError(k)


ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
       "-x264-params", "keyint=60:min-keyint=1:scenecut=40", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def encode(c, L, out, frames_iter, n):
    """rgb24 frames from frames_iter (PIL RGB/RGBA) -> H.264 at the reel's frame rate (video only; audio is muxed after)."""
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FW}x{FH}",
                          "-r", "30000/1001", "-i", "-"] + ENC + ["-an", out], stdin=subprocess.PIPE)
    k = 0
    for im in frames_iter:
        p.stdin.write(im.convert("RGB").tobytes()); k += 1
    p.stdin.close(); p.wait()
    if p.returncode or k != n: raise RuntimeError(f"encode {out}: {k}/{n} frames, exit {p.returncode}")


def render_body(c, L, out, f_to=None):
    """Everything after frame 1's opening, once per reel (it's the same in every version)."""
    f_from, f_to = L["intro_frames"], (L["frames"] if f_to is None else f_to); layers = Layers(); fps = L["fps"]
    def gen():
        for seg in segments(c, L, f_from=f_from, f_to=f_to):
            n = seg["f1"] - seg["f0"]; cmd, size = decode_cmd(c, seg, n)
            for k, fr in enumerate(frames_of(cmd, size, n)):
                f = seg["f0"] + k; yield compose(c, L, fr, f / fps, f, layers)
    encode(c, L, out, gen(), f_to - f_from)


def render_intro(c, L, r, v, out):
    n = L["intro_frames"]; layers = Layers(); fps = L["fps"]
    def gen():
        for f, fr in enumerate(intro_frames(c, L, r, v, n)): yield compose(c, L, fr, f / fps, f, layers, v, r)
    encode(c, L, out, gen(), n)
