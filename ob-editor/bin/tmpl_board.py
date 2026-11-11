"""tmpl_board: Trainbloom's board grammar for T17, as one tmpl element of type "tb" (built 11-07 from DECODE-V3 section 4,
69 reels at 10-30 fps: /Volumes/T7/OB-EDITS/2026-11-07-style-truth/trainbloom/DECODE-V3.md; clips in reference/REFERENCE.md).

What it reproduces (his numbers, not house rules):
  - a full-screen flat board (#F5F5F5 his, warm #F3F1EC ours), no texture, no camera moves on the page;
  - scenes of up to ~8 items built one beat every ~1.2 s, each item timed to its word (onset - 0.1 s; titles and placeholders
    0-0.2 s after the scene opens);
  - his enter presets: pop from a dot seed (0.06 -> 1.10 at 0.20 s -> 1.00 at 0.27 s), rise through a mask (0.22 s,
    cubic-bezier(.2,.7,.3,1), 16 px), type-on (14 chars/s, centred lines grow both ways), fade (0.3 s), number fill bottom-up
    (0.4 s ease-in-out, optional 2% ghost), draw (axis 0.75 s from the corner, check 0.2 s, leader 0.3 s), bars grow (0.9 s
    ease-in-out, staggered, value labels after the settle), slide-in from an edge (0.7 s expo-out), header bar grow (0.6 s),
    gauge fill (1.0 s, colour by level), waffle rows (0.3 s a row), scale markers (0.4 s drop), strike (0.2 s), dim (0.3 s);
  - scene changes: clear (all fade 0.33 s, 3 blank frames), promote (one item shrinks up into the title row, 1.0 s
    ease-in-out), dock (the scene scales and parks on the left edge as a rail, 1.1 s); a hard cut when the line ends;
  - something alive between beats (a +-2 px sine drift on popped items).
OB's upgrade (OB 11-04 / 11-07: "we wanna upgrade trainblooms style with blender"): "seq3d" plays a Blender render (clay
objects with real contact shadows, made by ~/ob-editor/bin/board3d.py) on the board with his pop, and the 2D items line up
with it from the render's own projected coordinates (board3d writes them to meta.json).

Plan element:
  {"type": "tb", "only": [LINE_IDS], "palette": "ob" | "tb" | "hz" (T23 violet) | "dark", "fill": true, "scenes": [SCENE, ...]}
  ("fill": false draws only the items, so the same builds work as cards over another look: Karan's navy board, a T23 plate)
  SCENE: {"on": WORD (first scene: the board's first frame), "out": "clear" | "promote" | "dock" | "cut", "keep": ITEM_ID,
          "items": [ITEM, ...]}
  ITEM:  {"id", "kind": text|hero|icon|image|seq3d|axis|bars|gauge|waffle|scale|line|strike|header|tiles|progress,
          "on": WORD | "at": seconds after the scene opens, "lead": 0.1, "enter": pop|snap|rise|type|fade|fill|draw|grow|slide|none,
          "dim_on": WORD, "recolor_on": WORD + "to": COLOUR, "out_on": WORD, "micro": bool, ...kind fields (see each _k_*)}
Colours are palette names: ink, mid, dim, light, a (group A / good), b (group B), red, green, yellow, tile, bar, white.
"""
import math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import tmpl_fx as FX

W, H, FPS = FX.W, FX.H, FX.FPS
FONTS = os.path.expanduser("~/ob-editor/fonts")
PAL = {
    # his, measured (DECODE-V3 4.3)
    "tb": dict(board=(245, 245, 245), ink=(10, 10, 10), mid=(165, 165, 165), dim=(148, 151, 154), light=(196, 196, 196),
               a=(35, 172, 250), b=(246, 173, 222), red=(221, 88, 86), green=(39, 222, 68), yellow=(244, 193, 42),
               tile=(60, 60, 60), bar=(218, 218, 218), white=(255, 255, 255), orange=(245, 158, 11)),
    # ours: a warm light board, ink, brand yellow (fills, and a highlighter band behind accent words: yellow text does not
    # read on a light board), charcoal as the second group, Big Shoulders numbers
    "ob": dict(board=(243, 241, 236), ink=(18, 18, 18), mid=(150, 148, 144), dim=(160, 158, 154), light=(206, 203, 197),
               a=FX.YEL, b=(44, 44, 44), red=(229, 72, 77), green=(34, 180, 85), yellow=FX.YEL,
               tile=(28, 28, 28), bar=(224, 221, 214), white=(255, 255, 255), orange=(245, 158, 11)),
    # T23 (Hormozi bulk 11-07): his violet board cutaways (#6D00FC, 48-73% of his top reels), white heading, items building
    # on his words; captions stay on at y ~1390 (look "plate" + "cap_y": 1390)
    "hz": dict(board=(109, 0, 252), ink=(255, 255, 255), mid=(225, 214, 255), dim=(170, 150, 235), light=(150, 110, 250),
               a=FX.YEL, b=(255, 255, 255), red=(255, 70, 70), green=(70, 230, 120), yellow=FX.YEL,
               tile=(60, 0, 150), bar=(140, 80, 250), white=(255, 255, 255), orange=(255, 170, 40)),
    # items over a dark look with no board fill ("fill": false): Karan's cards on his navy board with him small on it
    "dark": dict(board=(15, 20, 45), ink=(255, 255, 255), mid=(200, 206, 218), dim=(120, 130, 150), light=(90, 100, 122),
                 a=FX.YEL, b=(40, 88, 200), red=(240, 80, 80), green=(60, 220, 110), yellow=FX.YEL,
                 tile=(20, 24, 40), bar=(60, 70, 92), white=(255, 255, 255), orange=(245, 158, 11)),
}
_FC = {}


def font(kind, size, weight="Bold", pal="ob"):
    """kind "label" = Inter; "hero" = Big Shoulders Display (ours) or Inter Black (his vector era)."""
    path = (f"{FONTS}/BigShoulders/BigShouldersDisplay[wght].ttf" if kind == "hero" and pal == "ob" else f"{FONTS}/Inter/Inter-VF.ttf")
    k = (path, int(size), weight)
    if k not in _FC:
        f = ImageFont.truetype(path, int(size))
        try: f.set_variation_by_name(weight)
        except Exception: pass
        _FC[k] = f
    return _FC[k]


# ---------- easing ----------
def c01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def e_out(u): u = c01(u); return 1 - (1 - u) ** 3
def e_in(u): u = c01(u); return u ** 3
def e_inout(u): u = c01(u); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
def e_expo(u): u = c01(u); return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def bezier(u, p1x=0.2, p1y=0.7, p2x=0.3, p2y=1.0):
    """CSS cubic-bezier easing (his text rise is (0.2, 0.7, 0.3, 1))."""
    u = c01(u)
    bx = lambda s: 3 * (1 - s) ** 2 * s * p1x + 3 * (1 - s) * s * s * p2x + s ** 3
    by = lambda s: 3 * (1 - s) ** 2 * s * p1y + 3 * (1 - s) * s * s * p2y + s ** 3
    lo, hi = 0.0, 1.0
    for _ in range(24):
        m = (lo + hi) / 2
        if bx(m) < u: lo = m
        else: hi = m
    return by((lo + hi) / 2)


def pop_scale(ti):
    """His pop (30 fps, 22 pops measured): 0.06 -> 1.05-1.12 at 0.20 s -> 1.00 at 0.27 s, a back-out. None before it starts."""
    if ti < 0: return None
    if ti < 0.20: return 0.06 + (1.10 - 0.06) * e_out(ti / 0.20)
    if ti < 0.27: return 1.10 - 0.10 * e_inout((ti - 0.20) / 0.07)
    return 1.0


def lerp(a, b, u): return a + (b - a) * u
def mix(c1, c2, u): return tuple(int(round(lerp(x, y, c01(u)))) for x, y in zip(c1, c2))


# ---------- time ----------
def _when(spec, words, after, base, lead=0.1):
    """A start time: "at" seconds after base, or the onset of the first word matching spec["on"] heard after `after`, minus lead."""
    if spec.get("at") is not None: return base + float(spec["at"])
    if spec.get("on"):
        w = FX._n(spec["on"])
        for x in words:
            if x["s"] >= after and FX._n(x["w"]).startswith(w): return x["s"] - spec.get("lead", lead)
        return 1e9
    return base + 0.1


def _plan(el, ctx):
    """Scene start times and every item's times, resolved once against the edit-clock words."""
    cache = ctx["cache"]; k = ("tb", id(el))
    if k in cache: return cache[k]
    words = ctx["words"]; lt = ctx.get("line_t0") or {}
    t_board = min([lt[i] for i in el.get("only", []) if i in lt] or [FX.trigger(el, words)])
    scenes = []; prev = t_board - 0.3
    for si, sc in enumerate(el["scenes"]):
        ts = t_board if si == 0 and not sc.get("on") and sc.get("at") is None else _when(sc, words, prev, t_board, sc.get("lead", 0.25))
        items = {}
        for it in sc["items"]:
            T = {"t0": _when(it, words, ts - 0.6, ts, it.get("lead", 0.1))}
            for key in ("dim_on", "recolor_on", "out_on", "fill_on", "mark_on"):
                if it.get(key): T[key] = _when({"on": it[key], "lead": it.get("lead2", 0.05)}, words, ts - 0.6, ts)
            if it.get("ons"): T["ons"] = [_when({"on": w, "lead": it.get("lead", 0.1)}, words, ts - 0.6, ts) if w else None for w in it["ons"]]
            if it.get("marks"): T["ons"] = [_when({"on": mk.get("on"), "at": mk.get("at"), "lead": mk.get("lead", 0.1)}, words, ts - 0.6, ts) for mk in it["marks"]]
            items[it.get("id", f"i{len(items)}")] = T
        scenes.append({"t": ts, "items": items}); prev = ts
    end = max([ctx.get("line_t1", {}).get(i, 0) for i in el.get("only", [])] or [0]) or 1e9
    for si, S in enumerate(scenes): S["t_end"] = scenes[si + 1]["t"] if si + 1 < len(scenes) else end
    cache[k] = scenes; return scenes


# ---------- drawing primitives ----------
def _text_sprite(txt, f, col, accent=None, acc_col=None, band=None, pal=None):
    """One line of text as an RGBA sprite; the accent word in its colour, or (our palette) ink over a yellow highlighter band."""
    asc, desc = f.getmetrics(); w = int(f.getlength(txt)) + 24; h = asc + desc + 16
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 12
    for wd in txt.split(" "):
        is_acc = accent and FX._n(wd) == FX._n(accent)
        ww = f.getlength(wd)
        if is_acc and band:
            d.rounded_rectangle([x - 8, 8 + asc * 0.42, x + ww + 8, 8 + asc + desc * 0.35], 8, fill=band + (255,))
        d.text((x, 8), wd, font=f, fill=((acc_col if is_acc and not band else col) + (255,)))
        x += ww + f.getlength(" ")
    return im


def _alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * c01(a)))); return im


def _paste_scaled(lay, spr, cx, cy, s, a=1.0):
    if s is None or s <= 0.01 or a <= 0: return
    sw, sh = max(1, int(spr.width * s)), max(1, int(spr.height * s))
    lay.alpha_composite(_alpha(spr.resize((sw, sh), Image.LANCZOS) if (sw, sh) != spr.size else spr, a), (int(cx - sw / 2), int(cy - sh / 2)))


def _dot(lay, x, y, col, r=8):
    ImageDraw.Draw(lay).ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))


def _glyph(kind, size, col, stroke=None):
    """Flat pictograms in his thin/solid style, code-drawn (no AI imagery)."""
    s = int(size); im = Image.new("RGBA", (s + 8, s + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = 4; lw = stroke or max(6, s // 9)
    if kind == "check":
        d.line([(o + s * 0.18, o + s * 0.52), (o + s * 0.42, o + s * 0.76), (o + s * 0.84, o + s * 0.26)], fill=col + (255,), width=lw, joint="curve")
    elif kind == "cross":
        d.line([(o + s * .2, o + s * .2), (o + s * .8, o + s * .8)], fill=col + (255,), width=lw); d.line([(o + s * .8, o + s * .2), (o + s * .2, o + s * .8)], fill=col + (255,), width=lw)
    elif kind == "person":   # his grey pictogram person: round head, rounded body
        d.ellipse([o + s * .34, o, o + s * .66, o + s * .32], fill=col + (255,))
        d.rounded_rectangle([o + s * .2, o + s * .38, o + s * .8, o + s], int(s * .2), fill=col + (255,))
    elif kind == "circle":
        d.ellipse([o, o, o + s, o + s], fill=col + (255,))
    elif kind == "ring":
        d.ellipse([o, o, o + s, o + s], outline=col + (255,), width=lw)
    elif kind == "camera":
        d.rounded_rectangle([o, o + s * .25, o + s, o + s * .9], int(s * .12), fill=col + (255,))
        d.rectangle([o + s * .3, o + s * .12, o + s * .62, o + s * .3], fill=col + (255,))
        d.ellipse([o + s * .32, o + s * .38, o + s * .68, o + s * .78], fill=(255, 255, 255, 255))
    elif kind == "plate":
        d.ellipse([o, o + s * .3, o + s, o + s * .9], fill=col + (255,)); d.ellipse([o + s * .15, o + s * .38, o + s * .85, o + s * .82], fill=(255, 255, 255, 90))
    else:
        d.ellipse([o, o, o + s, o + s], fill=col + (255,))
    return im


# ---------- item kinds ----------
# Each returns nothing and draws onto `lay` for scene-local time; T = the item's resolved times; P = palette.
def _col(P, name, default="ink"): return P.get(name or default, P[default]) if isinstance(name, str) or name is None else tuple(name)


def _k_text(lay, it, t, T, P, pal, cache):
    """Title, label or aside. enter rise (titles, labels), type (titles, legends), fade (asides)."""
    ti = t - T["t0"]
    if ti < 0: return None
    size = it.get("size", 80 if it.get("role") == "title" else 44)
    f = font("label", size, it.get("weight", "Bold" if it.get("role") != "aside" else "Medium"), pal)
    col = _col(P, it.get("color"), "ink")
    if T.get("dim_on") and t >= T["dim_on"]: col = mix(col, P["dim"], (t - T["dim_on"]) / 0.3)
    band = P["a"] if (pal == "ob" and it.get("accent") and it.get("accent_style", "band") == "band") else None
    acc = _col(P, it.get("accent_color"), "a")
    txt = it["text"]; enter = it.get("enter", "rise" if it.get("role") == "title" else "fade")
    if enter == "type":   # 14 chars/s, 2 characters every 2 frames, centred lines grow both ways
        n = min(len(txt), max(1, int(ti * it.get("cps", 14) / 2 + 1) * 2))
        if n < len(txt): txt = txt[:n]
    key = ("txt", txt, size, col, it.get("accent"), band)
    if key not in cache: cache[key] = _text_sprite(txt, f, col, it.get("accent"), acc, band)
    spr = cache[key]; x, y = it.get("x", 540), it.get("y", 400); anchor = it.get("align", "c")
    px = x - spr.width / 2 if anchor == "c" else x - 12 if anchor == "l" else x - spr.width + 12
    if enter == "rise":   # through a mask from the baseline: the line rises 16 px inside its own box
        u = bezier(ti / 0.22); dy = int(round(16 * (1 - u)))
        if dy > 0: spr = spr.crop((0, 0, spr.width, spr.height - dy))
        lay.alpha_composite(_alpha(spr, min(1, ti / 0.08)), (int(px), int(y - spr.height / 2 + dy)))
    elif enter == "snap":
        u = min(1.0, ti * FPS / 2); s2 = 0.9 + 0.1 * u
        _paste_scaled(lay, spr, px + spr.width / 2, y, s2, 0.6 + 0.4 * u)
    else:
        a = min(1.0, ti / 0.3) if enter == "fade" else 1.0
        lay.alpha_composite(_alpha(spr, a), (int(px), int(y - spr.height / 2)))
    return (px, y - spr.height / 2, px + spr.width, y + spr.height / 2)


def _k_hero(lay, it, t, T, P, pal, cache, scene_t):
    """A big number: optional 2% ghost from the scene's start, then a bottom-up fill in 0.4 s ease-in-out on its word;
    dims to #94979A when the next number lands (dim_on); a small unit after it, a label under it (rise)."""
    size = it.get("size", 250); f = font("hero", size, "Black", pal); col = _col(P, it.get("color"), "ink")
    txt = str(it["value"]); ti = t - T["t0"]
    if T.get("dim_on") and t >= T["dim_on"]: col = mix(col, P["dim"], (t - T["dim_on"]) / 0.3)
    if T.get("recolor_on") and t >= T["recolor_on"]: col = mix(col, _col(P, it.get("to"), "a"), (t - T["recolor_on"]) / 0.5)
    key = ("hero", txt, size, col, it.get("unit"), pal)
    if key not in cache:
        asc, desc = f.getmetrics(); fu = font("hero" if pal == "ob" else "label", int(size * 0.42), "Black" if pal == "ob" else "Bold", pal)
        w = int(f.getlength(txt) + (fu.getlength(it["unit"]) + 10 if it.get("unit") else 0)) + 20
        im = Image.new("RGBA", (w, asc + desc + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.text((10, 5), txt, font=f, fill=col + (255,))
        if it.get("unit"): d.text((10 + f.getlength(txt) + 10, 5 + asc - fu.getmetrics()[0]), it["unit"], font=fu, fill=col + (255,))
        bb = im.getbbox(); cache[key] = im.crop((0, max(0, bb[1] - 4), im.width, min(im.height, bb[3] + 4)))
    spr = cache[key]; x, y = it.get("x", 540), it.get("y", 700); box = (x - spr.width / 2, y - spr.height / 2, x + spr.width / 2, y + spr.height / 2)
    if it.get("ghost") and t >= scene_t + 0.05 and ti < 0.6:   # vector era: the number's ghost (ink at 2%) is up before it fills
        gk = key + ("ghost",)
        if gk not in cache: cache[gk] = _alpha(spr, 0.04)
        lay.alpha_composite(cache[gk], (int(box[0]), int(box[1])))
    if ti < 0: return box
    r = e_inout(ti / it.get("fill_dur", 0.4)) if it.get("enter", "fill") == "fill" else 1.0
    cut = int(spr.height * (1 - r))
    if cut < spr.height: lay.alpha_composite(spr.crop((0, cut, spr.width, spr.height)), (int(box[0]), int(box[1] + cut)))
    if it.get("label"):
        L = dict(text=it["label"], x=x, y=y + spr.height / 2 + it.get("label_gap", 46), size=it.get("label_size", 44), weight="Bold",
                 color=it.get("label_color", "mid"), enter="rise", accent=it.get("accent"))
        _k_text(lay, L, t, {"t0": T["t0"] + 0.12}, P, pal, cache)
    return box


def _k_icon(lay, it, t, T, P, pal, cache, alive):
    """A pictogram, product cut-out or photo head: pops from a dot (or slides in from an edge)."""
    ti = t - T["t0"]; x, y = it.get("x", 540), it.get("y", 700)
    if ti < -2 / FPS: return None
    col = _col(P, it.get("color"), "mid")
    if T.get("dim_on") and t >= T["dim_on"]: col = mix(col, P["light"], (t - T["dim_on"]) / 0.3)
    if T.get("recolor_on") and t >= T["recolor_on"]: col = mix(col, _col(P, it.get("to"), "a"), (t - T["recolor_on"]) / 0.4)
    if it.get("path"):
        key = ("img", it["path"], it.get("size", 220))
        if key not in cache:
            im = FX.load(it["path"]); s = it.get("size", 220) / max(im.width, im.height); cache[key] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    else:
        key = ("glyph", it.get("glyph", "circle"), it.get("size", 130), col)
        if key not in cache: cache[key] = _glyph(it.get("glyph", "circle"), it.get("size", 130), col)
    spr = cache[key]
    if it.get("micro", True) and ti > 0.3: y += 2.0 * math.sin((t + alive) * 2 * math.pi / 2.4)   # alive between beats
    enter = it.get("enter", "pop")
    if enter == "slide":
        u = e_expo(ti / 0.7); side = it.get("from", "left"); dx = {"left": -W, "right": W}.get(side, 0); dy = H * 0.6 if side == "bottom" else 0
        if ti >= 0: lay.alpha_composite(spr, (int(x - spr.width / 2 + dx * (1 - u)), int(y - spr.height / 2 + dy * (1 - u))))
    elif enter == "draw" and it.get("glyph") in ("check", "cross"):   # a check draws in 0.2 s, easing out
        if ti >= 0:
            u = e_out(ti / 0.2); m = Image.new("L", spr.size, 0); ImageDraw.Draw(m).rectangle([0, 0, int(spr.width * u), spr.height], fill=255)
            s2 = spr.copy(); s2.putalpha(Image.composite(spr.getchannel("A"), Image.new("L", spr.size, 0), m)); lay.alpha_composite(s2, (int(x - spr.width / 2), int(y - spr.height / 2)))
    elif enter == "snap":   # Karan (11b_gfx-pop, 13 a minute): on in 1-3 frames, no overshoot, nothing after
        if ti < 0: return None
        u = min(1.0, ti * FPS / 2); _paste_scaled(lay, spr, x, y, 0.9 + 0.1 * u, 0.6 + 0.4 * u)
    else:   # pop from a dot seed
        if ti < 0: _dot(lay, x, y, col, 9); return (x - 9, y - 9, x + 9, y + 9)
        _paste_scaled(lay, spr, x, y, pop_scale(ti))
    if it.get("label"):
        _k_text(lay, dict(text=it["label"], x=x, y=y + spr.height / 2 + it.get("label_gap", 40), size=it.get("label_size", 40), color=it.get("label_color", "ink"),
                          enter="fade", accent=it.get("accent"), weight="SemiBold"), t, {"t0": T["t0"] + 0.15}, P, pal, cache)
    return (x - spr.width / 2, y - spr.height / 2, x + spr.width / 2, y + spr.height / 2)


def _k_seq3d(lay, it, t, T, P, pal, cache):
    """OB's upgrade: a Blender clip (board3d.py, RGBA with its contact shadow) on the board, popping in like his sprites,
    playing from its word and holding (or looping) its last frames."""
    ti = t - T["t0"]
    if ti < -2 / FPS: return None
    k = ("seqfiles", it["dir"])
    if k not in cache: cache[k] = sorted(os.path.join(it["dir"], f) for f in os.listdir(it["dir"]) if f.startswith("f_") and f.endswith(".png")) if os.path.isdir(it["dir"]) else []
    fs = cache[k]; n = len(fs)
    if not n: return None   # not rendered yet
    fi = int(max(0, ti) * it.get("fps", FPS))
    fi = (fi % n) if it.get("loop") else min(n - 1, fi)
    fr = Image.open(fs[fi]).convert("RGBA"); cx, cy, w = it.get("box", (540, 960, 1080))
    fr.putalpha(fr.getchannel("A").point(lambda v: 0 if v < 6 else int((v - 6) * 255 / 249)))
    if fr.width != w: fr = fr.resize((int(w), round(fr.height * w / fr.width)), Image.LANCZOS)
    if it.get("enter", "none") == "pop":
        if ti < 0: _dot(lay, cx, cy, P["mid"], 9); return None
        _paste_scaled(lay, fr, cx, cy, pop_scale(ti))
    elif ti >= 0:
        lay.alpha_composite(_alpha(fr, min(1, ti / 0.1) if it.get("enter") == "fade" else 1), (int(cx - fr.width / 2), int(cy - fr.height / 2)))
    return (cx - fr.width / 2, cy - fr.height / 2, cx + fr.width / 2, cy + fr.height / 2)


def _k_axis(lay, it, t, T, P, pal, cache):
    """Axes: both arms grow together from the corner, 0.75 s ease-in-out."""
    ti = t - T["t0"]
    if ti < 0: return None
    x0, y0, x1, y1 = it["box"]; u = e_inout(ti / it.get("dur", 0.75)); d = ImageDraw.Draw(lay); col = _col(P, it.get("color"), "ink"); lw = it.get("width", 6)
    d.line([(x0, y1), (x0 + (x1 - x0) * u, y1)], fill=col + (255,), width=lw)
    if not it.get("x_only"): d.line([(x0, y1), (x0, y1 - (y1 - y0) * u)], fill=col + (255,), width=lw)
    return (x0, y0, x1, y1)


def _k_bars(lay, it, t, T, P, pal, cache):
    """Bars growing from the baseline: 0.9 s ease-in-out each, staggered (or each on its own word via "ons"); value labels
    fade in after the settle (+0.5 s)."""
    x0, y0, x1, y1 = it["box"]; vals = it["values"]; n = len(vals); mx = it.get("max", max(vals)); gap = it.get("gap", 0.35)
    bw = (x1 - x0) / (n + (n - 1) * gap); d = ImageDraw.Draw(lay); cols = it.get("colors", ["a"] * n); bb = None
    for i, v in enumerate(vals):
        ts = (T.get("ons") or [None] * n)[i] if T.get("ons") and T["ons"][i] is not None else T["t0"] + i * it.get("stagger", 0.12)
        ti = t - ts
        if ti < 0: continue
        u = e_inout(ti / it.get("dur", 0.9)); bx = x0 + i * bw * (1 + gap); top = y1 - (y1 - y0) * (v / mx) * u
        col = _col(P, cols[i % len(cols)], "a")
        if T.get("dim_on") and t >= T["dim_on"] and i in it.get("dim_idx", []): col = mix(col, P["light"], (t - T["dim_on"]) / 0.3)
        d.rounded_rectangle([bx, top, bx + bw, y1], min(it.get("radius", 10), max(1, (y1 - top) / 2)), fill=col + (255,))
        if it.get("labels"):
            _k_text(lay, dict(text=it["labels"][i], x=bx + bw / 2, y=y1 + 40, size=it.get("label_size", 36), color="mid", enter="fade", weight="SemiBold"), t, {"t0": ts}, P, pal, cache)
        if it.get("value_labels") and ti > it.get("dur", 0.9) + 0.3:
            _k_text(lay, dict(text=it["value_labels"][i], x=bx + bw / 2, y=top - 36, size=it.get("value_size", 40), color="ink", enter="fade", weight="Bold"),
                    t, {"t0": ts + it.get("dur", 0.9) + 0.3}, P, pal, cache)
        bb = (x0, y0, x1, y1)
    return bb


def _k_line(lay, it, t, T, P, pal, cache):
    """A connector, leader or level line drawing along its points (0.3 s ease-out; "dur" for longer), solid or dashed."""
    ti = t - T["t0"]
    if ti < 0: return None
    pts = it["pts"]; u = (e_inout if it.get("ease") == "inout" else e_out)(ti / it.get("dur", 0.3))
    L = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; tot = sum(L) * u; out = [pts[0]]
    for i, l in enumerate(L):
        if tot <= 0: break
        f = min(1.0, tot / l) if l else 1.0; p0, p1 = pts[i], pts[i + 1]; out.append((lerp(p0[0], p1[0], f), lerp(p0[1], p1[1], f))); tot -= l
    col = _col(P, it.get("color"), "ink"); d = ImageDraw.Draw(lay); lw = it.get("width", 6)
    if it.get("dash"):
        seg, gap = it.get("dash", [22, 14]) if isinstance(it.get("dash"), list) else (22, 14)
        for (ax, ay), (bx, by) in zip(out, out[1:]):
            ln = math.dist((ax, ay), (bx, by)); s = 0.0
            while s < ln:
                e = min(ln, s + seg); d.line([(lerp(ax, bx, s / ln), lerp(ay, by, s / ln)), (lerp(ax, bx, e / ln), lerp(ay, by, e / ln))], fill=col + (255,), width=lw); s += seg + gap
    else:
        d.line(out, fill=col + (255,), width=lw, joint="curve")
    if it.get("label") and u >= 0.999:
        lx, ly = it.get("label_xy", (pts[-1][0], pts[-1][1] - 40))
        _k_text(lay, dict(text=it["label"], x=lx, y=ly, size=it.get("label_size", 38), color=it.get("label_color", it.get("color", "ink")), enter="rise",
                          weight="Bold", align=it.get("label_align", "c"), accent=it.get("accent")), t, {"t0": T["t0"] + it.get("dur", 0.3)}, P, pal, cache)
    return None


def _k_gauge(lay, it, t, T, P, pal, cache):
    """A fill gauge (tube or battery): the outline pops in, then the level fills (1.0 s ease-in-out) on fill_on; colour by
    level (green high, orange, red low) unless "color" is set."""
    ti = t - T["t0"]; x, y, w, h = it.get("x", 540), it.get("y", 800), it.get("w", 150), it.get("h", 460)
    if ti < 0: return None
    s = pop_scale(ti); d = ImageDraw.Draw(lay); ink = _col(P, it.get("outline"), "ink"); r = w / 2 if it.get("kind", "tube") == "tube" else 22
    lvl0, lvl1 = it.get("from", 0.0), it.get("level", 0.7); tf = T.get("fill_on", T["t0"] + 0.3)
    lv = lerp(lvl0, lvl1, e_inout((t - tf) / it.get("dur", 1.0))) if t >= tf else lvl0
    col = _col(P, it["color"]) if it.get("color") else (P["green"] if lv > 0.6 else P["orange"] if lv > 0.3 else P["red"])
    tile = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0)); td = ImageDraw.Draw(tile)
    m = Image.new("L", tile.size, 0); ImageDraw.Draw(m).rounded_rectangle([8, 8, 8 + w, 8 + h], r, fill=255)
    fill = Image.new("RGBA", tile.size, (0, 0, 0, 0)); ImageDraw.Draw(fill).rectangle([8, 8 + h * (1 - lv), 8 + w, 8 + h], fill=col + (255,))
    tile.alpha_composite(Image.composite(fill, Image.new("RGBA", tile.size, (0, 0, 0, 0)), m))
    td.rounded_rectangle([8, 8, 8 + w, 8 + h], r, outline=ink + (255,), width=it.get("width", 7))
    _paste_scaled(lay, tile, x, y, s)
    if it.get("kind") == "battery" and s >= 0.99: d.rounded_rectangle([x - w * 0.18, y - h / 2 - 22, x + w * 0.18, y - h / 2 - 4], 6, fill=ink + (255,))
    if it.get("label"):
        _k_text(lay, dict(text=it["label"], x=x, y=y + h / 2 + 50, size=it.get("label_size", 42), color="ink", enter="rise", weight="Bold", accent=it.get("accent")),
                t, {"t0": T["t0"] + 0.15}, P, pal, cache)
    if it.get("value") and t >= tf + it.get("dur", 1.0) * 0.6:
        _k_text(lay, dict(text=it["value"], x=x, y=y - h / 2 - 50, size=it.get("value_size", 52), color="ink", enter="fade", weight="ExtraBold"), t,
                {"t0": tf + it.get("dur", 1.0) * 0.6}, P, pal, cache)
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _k_waffle(lay, it, t, T, P, pal, cache):
    """An n x m grid of identical dots or people filling top-down, a row every 0.3 s; a share recolours (0.4 s sweep) on recolor_on."""
    ti = t - T["t0"]
    if ti < 0: return None
    n, m = it.get("cols", 10), it.get("rows", 10); x0, y0, st = it.get("x", 200), it.get("y", 600), it.get("step", 66); r = it.get("r", 24)
    col = _col(P, it.get("color"), "light"); share = it.get("share", 0); to = _col(P, it.get("to"), "a")
    for j in range(m):
        rt = j * it.get("row_dt", 0.3)
        if ti < rt: break
        for i in range(n):
            k = j * n + i; c = col
            if T.get("recolor_on") and k < share and t >= T["recolor_on"]: c = mix(col, to, (t - T["recolor_on"] - k * 0.004) / 0.4)
            cx, cy = x0 + i * st, y0 + j * st
            if it.get("glyph") == "person":
                gk = ("wp", r * 2, c)
                if gk not in cache: cache[gk] = _glyph("person", r * 2, c)
                g = cache[gk]; lay.alpha_composite(g, (int(cx - g.width / 2), int(cy - g.height / 2)))
            else: ImageDraw.Draw(lay).ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))
    return (x0 - r, y0 - r, x0 + (n - 1) * st + r, y0 + (m - 1) * st + r)


def _k_scale(lay, it, t, T, P, pal, cache):
    """A number line growing both ways from a dot (0.7 s ease-in-out), ticks fading in, markers dropping from above (0.4 s
    ease-out) with a pointer, each on its own word ("marks": [{"value", "on", "label", "color"}])."""
    ti = t - T["t0"]
    if ti < -2 / FPS: return None
    x0, x1, y = it.get("x0", 200), it.get("x1", 880), it.get("y", 900); lo, hi = it.get("min", 0), it.get("max", 100)
    col = _col(P, it.get("color"), "ink"); d = ImageDraw.Draw(lay); cx = (x0 + x1) / 2
    if ti < 0: _dot(lay, cx, y, col, 9); return None
    u = e_inout(ti / 0.7); d.line([(cx - (cx - x0) * u, y), (cx + (x1 - cx) * u, y)], fill=col + (255,), width=it.get("width", 7))
    X = lambda v: x0 + (x1 - x0) * (v - lo) / (hi - lo)
    if ti > 0.5:
        for v in it.get("ticks", []):
            a = c01((ti - 0.5) / 0.3); d.line([(X(v), y - 14), (X(v), y + 14)], fill=col + (int(255 * a),), width=5)
            _k_text(lay, dict(text=f"{v}{it.get('unit', '')}", x=X(v), y=y + 56, size=34, color="mid", enter="fade", weight="SemiBold"), t, {"t0": T["t0"] + 0.5}, P, pal, cache)
    marks = it.get("marks", []); key = ("tbmarks", id(it))
    if key not in cache:
        cache[key] = [None] * len(marks)
    for i, mk in enumerate(marks):
        tm = T.get("ons", [None] * len(marks))[i] if T.get("ons") else None
        if tm is None or t < tm: continue
        u = e_out((t - tm) / 0.4); mx = X(mk["value"]); my = y - 30 - 60 * (1 - u); mc = _col(P, mk.get("color"), "ink")
        d.polygon([(mx - 20, my - 34), (mx + 20, my - 34), (mx, my)], fill=mc + (int(255 * min(1, u * 2)),))
        if mk.get("label"):
            _k_text(lay, dict(text=mk["label"], x=mx, y=my - 76 - mk.get("lift", 0), size=mk.get("size", 46), color=mk.get("label_color", "ink"), enter="rise", weight="ExtraBold",
                              accent=mk.get("accent")), t, {"t0": tm + 0.1}, P, pal, cache)
    return (x0, y - 120, x1, y + 80)


def _k_row(lay, it, t, T, P, pal, cache):
    """A row of small labels at given x positions (day initials under 3D bars), fading in left to right ("stagger" s apart)."""
    if t < T["t0"]: return None
    for i, (tx, x) in enumerate(zip(it["texts"], it["xs"])):
        _k_text(lay, dict(text=tx, x=x, y=it.get("y", 1200), size=it.get("size", 38), color=it.get("color", "mid"), enter="fade", weight=it.get("weight", "SemiBold")),
                t, {"t0": T["t0"] + i * it.get("stagger", 0.06)}, P, pal, cache)
    return None


def _k_header(lay, it, t, T, P, pal, cache):
    """A header bar: a 1 px line grows to full width (0.6 s ease-out), then its text fades in (0.2 s)."""
    ti = t - T["t0"]
    if ti < 0: return None
    x0, x1, y, h = it.get("x0", 160), it.get("x1", 920), it.get("y", 380), it.get("h", 112); u = e_out(ti / 0.6); cx = (x0 + x1) / 2
    hh = max(2, h * c01((ti - 0.15) / 0.3)) if ti > 0.15 else 2
    ImageDraw.Draw(lay).rounded_rectangle([cx - (cx - x0) * u, y - hh / 2, cx + (x1 - cx) * u, y + hh / 2], min(16, hh / 2), fill=_col(P, it.get("color"), "tile") + (255,))
    if ti > 0.45:
        _k_text(lay, dict(text=it["text"], x=cx, y=y, size=it.get("size", 56), color=it.get("text_color", "white"), enter="fade", weight="ExtraBold"), t, {"t0": T["t0"] + 0.45}, P, pal, cache)
    return (x0, y - h / 2, x1, y + h / 2)


def _k_tiles(lay, it, t, T, P, pal, cache):
    """His numbered cover tiles (12/30 reels): dark tiles over each point; on its word a tile slides up out (0.45 s ease-in)
    and the point under it fades in (0.2 s)."""
    xs = it["xs"]; y, sz = it.get("y", 900), it.get("size", 300); d = ImageDraw.Draw(lay); ons = T.get("ons") or [None] * len(xs)
    if t < T["t0"]: return None
    for i, x in enumerate(xs):
        tr = ons[i]; u = e_in((t - tr) / 0.45) if tr is not None and t >= tr else 0.0
        if tr is not None and t >= tr + 0.1 and it.get("under"):
            U = dict(it["under"][i]); U.setdefault("x", x); U.setdefault("y", y)
            fn = _k_hero if U.get("kind") == "hero" else _k_text
            fn(lay, U, t, {"t0": tr + 0.1}, P, pal, cache, *([T["t0"]] if fn is _k_hero else []))
        if u < 1:
            yy = y - (y + sz) * u; tc = _col(P, it.get("color"), "tile")
            d.rounded_rectangle([x - sz / 2, yy - sz / 2, x + sz / 2, yy + sz / 2], 15, fill=tc + (255,))
            f = font("hero", int(sz * 0.5), "Black", pal); d.text((x, yy), str(i + 1), font=f, fill=(P["a"] if pal == "ob" else P["white"]) + (255,), anchor="mm")
    return None


def _k_progress(lay, it, t, T, P, pal, cache):
    ti = t - T["t0"]
    if ti < 0: return None
    x, y, w, h = it.get("x", 200), it.get("y", 900), it.get("w", 680), it.get("h", 44); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + w, y + h], h / 2, fill=P["bar"] + (255,))
    u = e_inout(ti / it.get("dur", 0.8)) * it.get("to", 0.7)
    if u > 0.01: d.rounded_rectangle([x, y, x + max(h, w * u), y + h], h / 2, fill=_col(P, it.get("color"), "a") + (255,))
    return (x, y, x + w, y + h)


def _k_strike(lay, it, t, T, P, pal, cache, boxes):
    """A red line across another item's box in 0.2 s (linear); the replacement types on under it."""
    ti = t - T["t0"]; bb = boxes.get(it["target"])
    if ti < 0 or not bb: return None
    u = c01(ti / 0.2); y = (bb[1] + bb[3]) / 2 + it.get("dy", 0)
    ImageDraw.Draw(lay).line([(bb[0] + 6, y), (bb[0] + 6 + (bb[2] - bb[0] - 12) * u, y)], fill=P["red"] + (255,), width=it.get("width", 9))
    if it.get("replace") and ti > 0.25:
        R = dict(it["replace"]); R.setdefault("x", (bb[0] + bb[2]) / 2); R.setdefault("y", bb[3] + 60); R.setdefault("enter", "type")
        _k_text(lay, R, t, {"t0": T["t0"] + 0.25}, P, pal, cache)
    return None


def _draw_item(lay, it, t, T, P, pal, cache, scene_t, boxes, idx):
    k = it.get("kind", "text"); alive = idx * 0.37
    if T.get("out_on") and t >= T["out_on"]:
        a = 1 - c01((t - T["out_on"]) / 0.2)
        if a <= 0: return
        sub = Image.new("RGBA", lay.size, (0, 0, 0, 0)); _draw_item(sub, dict(it, out_on=None), t, dict(T, out_on=None), P, pal, cache, scene_t, boxes, idx)
        lay.alpha_composite(_alpha(sub, a)); return
    fn = {"text": _k_text, "axis": _k_axis, "bars": _k_bars, "line": _k_line, "gauge": _k_gauge, "waffle": _k_waffle, "scale": _k_scale,
          "header": _k_header, "row": _k_row, "tiles": _k_tiles, "progress": _k_progress, "seq3d": _k_seq3d}.get(k)
    if k == "hero": bb = _k_hero(lay, it, t, T, P, pal, cache, scene_t)
    elif k in ("icon", "image"): bb = _k_icon(lay, it, t, T, P, pal, cache, alive)
    elif k == "strike": bb = _k_strike(lay, it, t, T, P, pal, cache, boxes)
    else: bb = fn(lay, it, t, T, P, pal, cache)
    if bb and it.get("id"): boxes[it["id"]] = bb


def _scene_layer(sc, S, t, P, pal, cache, only=None, skip=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); boxes = {}
    for idx, it in enumerate(sc["items"]):
        iid = it.get("id", f"i{idx}")
        if only is not None and iid != only: continue
        if skip is not None and iid == skip: continue
        _draw_item(lay, it, t, S["items"][iid], P, pal, cache, S["t"], boxes, idx)
    return lay, boxes


def _xform(lay, s, ox, oy, tx, ty):
    """Scale the layer by s about (ox, oy) and move that point to (tx, ty)."""
    if abs(s - 1) < 1e-3 and abs(tx - ox) < 0.5 and abs(ty - oy) < 0.5: return lay
    a = 1 / s; return lay.transform(lay.size, Image.AFFINE, (a, 0, ox - a * tx, 0, a, oy - a * ty), Image.BICUBIC)


def _carry(img, el, scenes, i, t, P, pal, cache):
    """Scene i's way out, from its start until forever: a promoted item travelling to (and then sitting in) the title row
    while the rest fade; or the whole scene shrinking onto the left edge as a rail."""
    sc, S = el["scenes"][i], scenes[i]; out = sc.get("out", "clear"); tn = scenes[i + 1]["t"]
    if out == "promote" and sc.get("keep"):
        t_go = tn - 0.3; u = e_inout((t - t_go) / sc.get("promote_dur", 1.0))
        if t < tn:
            rest, _ = _scene_layer(sc, S, t_go, P, pal, cache, skip=sc["keep"]); img.alpha_composite(_alpha(rest, 1 - c01((t - t_go) / 0.3)))
        lay, bx = _scene_layer(sc, S, t_go, P, pal, cache, only=sc["keep"]); b = bx.get(sc["keep"])
        if b:
            ox, oy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; tx, ty, ts = sc.get("promote_to", (540, 330, 0.5))
            img.alpha_composite(_xform(lay, lerp(1, ts, u), ox, oy, lerp(ox, tx, u), lerp(oy, ty, u)))
    elif out == "dock":
        t_go = tn - 0.4; u = e_inout((t - t_go) / 1.1); lay, _ = _scene_layer(sc, S, t_go, P, pal, cache)
        img.alpha_composite(_xform(lay, lerp(1, sc.get("dock_scale", 0.42), u), 540, 960, lerp(540, sc.get("dock_x", 150), u), 960))


def draw_tb(img, el, t, ctx):
    if el.get("only") and ctx.get("line") not in el["only"]: return
    scenes = _plan(el, ctx); pal = el.get("palette", "ob"); P = PAL[pal]; cache = ctx["cache"].setdefault("tbc", {})
    if el.get("fill", True): img.paste(P["board"] + (255,), (0, 0, W, H))   # "fill": false = items only, over any look
    cur = max([i for i, S in enumerate(scenes) if S["t"] <= t] or [0])
    for i in range(cur):   # what earlier scenes leave on the board (a promoted title, a docked rail)
        if el["scenes"][i].get("out") in ("promote", "dock"): _carry(img, el, scenes, i, t, P, pal, cache)
    sc, S = el["scenes"][cur], scenes[cur]; out = sc.get("out", "clear"); last = cur + 1 >= len(scenes); tn = S["t_end"]
    if not last and out in ("promote", "dock") and t >= tn - (0.3 if out == "promote" else 0.4):
        _carry(img, el, scenes, cur, t, P, pal, cache); return
    if not last and out == "clear" and t >= tn - 0.43:   # all fade 0.33 s, then ~3 blank frames before the next scene's first beat
        a = 1 - c01((t - (tn - 0.43)) / 0.33)
        if a > 0:
            lay, _ = _scene_layer(sc, S, tn - 0.43, P, pal, cache); img.alpha_composite(_alpha(lay, a))
        return
    lay, _ = _scene_layer(sc, S, t, P, pal, cache); img.alpha_composite(lay)


FX.DRAW["tb"] = draw_tb
