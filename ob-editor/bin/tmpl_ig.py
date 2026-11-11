#!/usr/bin/env python3
"""tmpl_ig: Instagram-native text for ads (OB 11-10, workshop ads: "dont put the bubble text like you also do, make it instagram
native text and just do overlay"). What IG's own text tool gives when the background is off: white sentence-case words straight on
the picture, a soft shadow so it reads on a busy photo, no box, no pill, no karaoke colour, on and off with a hard cut.
Inter (OFL) stands in for Instagram Sans, which is Meta's brand font and not licensed for ad overlays.

Registers tmpl_fx element "igtext":
  {"type": "igtext", "lines": ["Women on a GLP:", "smaller, not softer"], "at": 0.0 | "on": WORD, "until": T | "off": WORD,
   "y": 290 (top of the block) | "y_mode": "center", "size": 64, "sizes": [..], "weight": "SemiBold", "colors": [None, "yellow"],
   "x": 540 (centre), "align": "c" | "l", "gap": 1.18 (line height in sizes)}

Also: study_card(...) writes the paper citation card the "image" element shows (real trial names, journals and years only, numbers
from the stats registry; never a made-up page).
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import tmpl_fx as FX

W, H = FX.W, FX.H
COL = {None: (255, 255, 255), "white": (255, 255, 255), "yellow": (255, 212, 0), "red": (255, 77, 77), "ink": (26, 26, 26)}


def _font(size, weight="SemiBold"):
    return FX.inter(size, weight)


def _shadowed(img, lay, blur=6, alpha=0.6, dy=3):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh.putalpha(lay.split()[3].point(lambda v: int(v * alpha)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (0, dy)); img.alpha_composite(lay)


def draw_igtext(img, el, t, ctx):
    words = ctx["words"]; t0 = FX.trigger(el, words)
    if t < t0: return
    if el.get("until") is not None and t > el["until"]: return
    if el.get("off"):
        te = FX.trigger({"on": el["off"], "after": t0 + 0.05}, words, default=1e9)
        if t >= te: return
    lines = el["lines"]; size0 = el.get("size", 64); gap = el.get("gap", 1.18); wt = el.get("weight", "SemiBold")
    sizes = list(el.get("sizes") or [size0] * len(lines))
    for i, ln in enumerate(lines):
        while sizes[i] > 36 and _font(sizes[i], wt).getlength(ln) > W - 120: sizes[i] -= 2
    hgt = sum(s * gap for s in sizes); y = el.get("y", 290)
    if el.get("y_mode") == "center": y -= hgt / 2
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x = el.get("x", W / 2)
    cols = el.get("colors") or [None] * len(lines)
    for ln, s, c in zip(lines, sizes, cols):
        f = _font(s, wt); col = COL.get(c, c) if not isinstance(c, (list, tuple)) else tuple(c)
        if el.get("align", "c") == "l": d.text((x, y + s * gap / 2), ln, font=f, fill=col + (255,), anchor="lm")
        else: d.text((x, y + s * gap / 2), ln, font=f, fill=col + (255,), anchor="mm")
        y += s * gap
    _shadowed(img, lay)
    if el.get("hide_caps"): FX._block(ctx, y - hgt, hide=True)   # 11-11 (2x2 reviewer): a CTA that owns the chest hides the captions under it (no "Live workshop" stacked on "live workshop")


FX.DRAW["igtext"] = draw_igtext


def study_card(out, panels, header=None, w=1000, h=400):
    """A clean paper card with one panel per trial: [{"trial": "STEP 1", "cite": "NEJM 2021", "drug": "Semaglutide",
    "big": "~45%", "line": "of the weight lost was lean mass", "foot": "DXA subset, Wilding et al."}, ...].
    Returns the highlight rectangles of each "big" figure (card pixels) so the marker can sweep them on a word."""
    S = 2; im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=22 * S, fill=(250, 248, 243, 255))
    y0 = 26 * S
    if header:
        d.text((w * S / 2, y0 + 20 * S), header, font=_font(30 * S, "Bold"), fill=(26, 26, 26), anchor="mm"); y0 += 58 * S
        d.line([40 * S, y0, (w - 40) * S, y0], fill=(220, 214, 200), width=2 * S); y0 += 14 * S
    n = len(panels); pw = w * S / n; marks = []
    for i, p in enumerate(panels):
        cx = pw * i + pw / 2; y = y0 + 10 * S
        if i: d.line([pw * i, y0 + 10 * S, pw * i, h * S - 30 * S], fill=(220, 214, 200), width=2 * S)
        d.text((cx, y + 16 * S), f"{p['trial']}  ·  {p['cite']}", font=_font(26 * S, "SemiBold"), fill=(110, 104, 94), anchor="mm"); y += 46 * S
        d.text((cx, y + 18 * S), p["drug"], font=_font(30 * S, "Bold"), fill=(26, 26, 26), anchor="mm"); y += 50 * S
        fb = _font(92 * S, "Black"); bw = fb.getlength(p["big"])
        marks.append([int((cx - bw / 2 - 12 * S) / S), int((y + 8 * S) / S), int((cx + bw / 2 + 12 * S) / S), int((y + 100 * S) / S)])
        d.text((cx, y + 54 * S), p["big"], font=fb, fill=(26, 26, 26), anchor="mm"); y += 108 * S
        d.text((cx, y + 16 * S), p["line"], font=_font(26 * S, "Medium"), fill=(26, 26, 26), anchor="mm"); y += 40 * S
        d.text((cx, y + 14 * S), p["foot"], font=_font(20 * S, "Medium"), fill=(130, 124, 114), anchor="mm")
    im.resize((w, h), Image.LANCZOS).save(out)
    return marks


def study_chart(out, rows, header, legend, w=900, h=300, trial_fs=19, label_w=318):
    """A bar chart on a paper card (11-11, reviewer: a number card reads as text; OB's rule: a chart, not a text card).
    rows: [{"drug": "Semaglutide", "trial": "STEP 1 · NEJM 2021", "pct": 45}, ...]: one stacked bar per trial, the lean share
    in yellow with its % on it, the rest light grey ("fat"). Returns the highlight rectangle of each % label (card pixels)."""
    S = 2; im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=22 * S, fill=(250, 248, 243, 255))
    d.text((w * S / 2, 30 * S), header, font=_font(28 * S, "Bold"), fill=(26, 26, 26), anchor="mm")
    lx, bx0, bx1 = 28 * S, label_w * S, (w - 28) * S; bh = 62 * S; marks = []   # 11-11: the label column fits "SURMOUNT-1 · NEJM 2022" (stills check: clipped at 270)
    for i, r in enumerate(rows):
        yc = (92 + i * 92) * S; room = bx0 - lx - 14 * S
        d.text((lx, yc - 13 * S), r["drug"], font=_font(28 * S, "Bold"), fill=(26, 26, 26), anchor="lm")
        fs = trial_fs   # 11-11: the 2x2 card runs 26 (reviewer: the trial names read tiny at phone width)
        while fs > 13 and _font(fs * S, "SemiBold").getlength(r["trial"]) > room: fs -= 1
        d.text((lx, yc + 17 * S), r["trial"], font=_font(fs * S, "SemiBold"), fill=(110, 104, 94), anchor="lm")
        y0, y1 = yc - bh / 2, yc + bh / 2; xm = bx0 + (bx1 - bx0) * r["pct"] / 100.0
        d.rounded_rectangle([bx0, y0, bx1, y1], radius=10 * S, fill=(214, 210, 200, 255))
        d.rounded_rectangle([bx0, y0, xm, y1], radius=10 * S, fill=(255, 212, 0, 255))
        d.rectangle([xm - 10 * S, y0, xm, y1], fill=(255, 212, 0, 255))
        fb = _font(40 * S, "Black"); lab = f"{r['pct']}%"; lw = fb.getlength(lab)
        d.text((bx0 + 16 * S, yc), lab, font=fb, fill=(26, 26, 26), anchor="lm")
        if r.get("unit"): d.text((bx0 + 24 * S + lw, yc + 3 * S), r["unit"], font=_font(26 * S, "Bold"), fill=(26, 26, 26), anchor="lm")   # 11-11: "45% lean" (stills check: "45% ... fat" could read as 45% fat)
        marks.append([int((bx0 + 6 * S) / S), int(y0 / S) + 4, int((bx0 + 26 * S + lw) / S), int(y1 / S) - 4])
        d.text((bx1 - 16 * S, yc), r.get("rest", "fat"), font=_font(24 * S, "SemiBold"), fill=(90, 86, 78), anchor="rm")
    if legend: d.text((w * S / 2, (h - 24) * S), legend, font=_font(18 * S, "Medium"), fill=(110, 104, 94), anchor="mm")
    im.resize((w, h), Image.LANCZOS).save(out)
    return marks


# ---------- video cards and video grid cells (OB 11-10: "Can you find videos as well, to get it more engaging") ----------
import hashlib, json as _json, subprocess as _sp
CLIPCACHE = os.path.expanduser("~/ob-scratch/tmpl/clipcache")


def _probe(src):
    o = _sp.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                 "-of", "json", src], capture_output=True, text=True).stdout
    j = _json.loads(o); s = j["streams"][0]; a, b = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(a) / float(b), float(j["format"]["duration"])


def clip_frames(src, w, h, start=0.0, dur=8.0, focus=(0.5, 0.5)):
    """A stock clip as a JPG sequence at w x h (cover crop at focus), conformed to 29.97 fps the editor-rule way: a 24/25 fps source is
    sped up so every output frame is a new source frame (no repeated-frame stutter), 50/60 fps drops frames. Never upscales more than
    the source allows: w/h are capped to the source's own cropped size. Returns (dir, n, w, h)."""
    sw, sh, fps, total = _probe(src)
    sc = max(w / sw, h / sh)
    if sc > 1.1: w, h = int(w / sc * 1.1) // 2 * 2, int(h / sc * 1.1) // 2 * 2   # cap the upscale at 1.1x
    key = hashlib.md5(f"v6|{src}|{w}|{h}|{start}|{dur}|{focus}".encode()).hexdigest()[:16]; d = os.path.join(CLIPCACHE, key)   # v2: frame-number conform
    if os.path.exists(os.path.join(d, "done")):
        return d, len([f for f in os.listdir(d) if f.endswith(".jpg")]), w, h
    os.makedirs(d, exist_ok=True); fx, fy = focus
    speed = 29.97 / fps if fps < 29 else 1.0
    # 11-10 fix: setpts=PTS/speed + fps re-timed 24/25 fps sources with rounding jitter (5-15 repeated frames per clip on the
    # frame-diff scan). Re-time by frame number instead: source frame N plays at N/29.97 s, exactly one output frame each.
    vf = ("settb=1001/30000,setpts=N,fps=30000/1001," if speed != 1.0 else "fps=30000/1001,") + \
         f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}:(iw-{w})*{fx}:(ih-{h})*{fy}"
    src_dur = min(dur * speed, max(0.5, total - start))
    _sp.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{src_dur:.3f}", "-i", src, "-an", "-vf", vf,
             "-fps_mode", "passthrough", "-q:v", "3", os.path.join(d, "%05d.jpg")], check=True)   # passthrough: write every frame (no 25 fps resample)
    open(os.path.join(d, "done"), "w").write(src)
    return d, len([f for f in os.listdir(d) if f.endswith(".jpg")]), w, h


def clip_frame_at(src, w, h, tl, cache, start=0.0, dur=8.0, focus=(0.5, 0.5), loop=True):
    """The frame tl seconds into the clip (JPG off the sequence, resized to w x h if the cache was capped)."""
    k = ("clipseq", src, w, h, start, dur, tuple(focus))
    if k not in cache: cache[k] = clip_frames(src, w, h, start, dur, tuple(focus))
    d, n, cw, ch = cache[k]
    i = int(round(max(0.0, tl) * FX.FPS)); i = i % n if loop else min(i, n - 1)   # round: tl is whole frames, int() could floor 4.9999 to 4
    im = Image.open(os.path.join(d, f"{i + 1:05d}.jpg")).convert("RGBA")
    return im if (cw, ch) == (w, h) else im.resize((w, h), Image.LANCZOS)


def draw_vcard(img, el, t, ctx):
    """{"type": "vcard", "src": MP4, "box": [cx, cy, w], "aspect": 1.0 (h/w), "at"|"on", "until", "in": 0.0, "focus": [0.5, 0.5],
        "radius": 28, "enter": "rise"}  a stock clip playing in a rounded card over his frame (he stays on screen: OB 10-30 / 11-10)."""
    t0 = FX.trigger(el, ctx["words"]); ti = t - t0
    if ti < 0 or (el.get("until") is not None and t > el["until"]): return
    tg = ctx.get("t_grid"); tc = (round(tg * FX.FPS) - round(t0 * FX.FPS)) / FX.FPS if tg is not None else ti   # whole output frames since it landed
    cx, cy, w = el["box"]; h = int(round(w * el.get("aspect", 1.0))); w = int(w)
    cache = ctx.setdefault("cache", {})
    fr = clip_frame_at(el["src"], w * 2 if w <= 540 else w, h * 2 if w <= 540 else h, max(0.0, tc), cache, el.get("in", 0.0), el.get("dur", 8.0),
                       el.get("focus", (0.5, 0.5))).resize((w, h), Image.LANCZOS)
    if el.get("gamma"):   # lift a dim stock clip's shadows and mids by measurement (11-10: the omelet clip read dark); never on OB's own footage
        g = float(el["gamma"]); lut = [int(255 * (v / 255) ** g + 0.5) for v in range(256)]; fr = fr.point([x for bd in fr.getbands() for x in (range(256) if bd == "A" else lut)])
    a = 1.0; dy = 0.0
    if el.get("enter") == "rise":   # opacity 0->1 ease-out cubic over 0.40 s, y +70 -> 0, no scale (no-zoom rule)
        u = 1 - (1 - min(1.0, ti / 0.40)) ** 3; a = u; dy = 70 * (1 - u)
    m = FX.rounded_mask(w, h, el.get("radius", 28))
    if a < 1: m = m.point(lambda v: int(v * a))
    img.paste(fr, (int(cx - w / 2), int(cy - h / 2 + dy)), m)


FX.DRAW["vcard"] = draw_vcard
