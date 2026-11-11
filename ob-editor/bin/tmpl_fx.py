#!/usr/bin/env python3
"""tmpl_fx: the brand-styled graphic elements every editor template shares (built 2026-11-04 for the template catalog,
~/ob-editor/styles/TEMPLATE-CATALOG.md; OB 11-04: "doesnt matter just do all of them").

Every element is drawn with PIL onto a 1080x1920 RGBA frame: draw(img, el, t, ctx). `t` is edit time in seconds; `ctx` holds
"words" ([{w, s, e}] on the edit clock) so an element can land ON the word that names it ("on": "calories"), "face" (his face
box [x0, y0, x1, y1] on this frame, so text stays clear of it) and "cache". Brand: Big Shoulders (Black headlines, ExtraBold
labels), #FFD400 on the one word or number that matters, white, a soft shadow, NO boxes behind text (brand.json "boxes": false).
Motion: closed-form springs (no stock easing), elements land ~0.15 s before their word (Kallaway/Karan measured), a blink in
2-frame states (single-frame blinks fail the QC gate as flash frames).

Elements (el["type"]):
  title     centred 1-2 line title, words rise in, "accent": [words] in yellow, optional "underline"           (T06 T09 T18 T19)
  text      any text at (x, y): "typeon" letter by letter, "track" letter-spacing, "size", "weight", "color"     (labels, lower thirds, keywords)
  count     odometer roll to "value" over "dur", "label" above (letter-spaced), "unit"; "glass": frosted card     (T04 T15 T17 T19)
  bar       one bar grows from "from" to "to" (%) on its word, big label + value                                  (T15)
  icons     10x10 dot array, "fill": [[n, word], ...] fills dots in yellow as each word lands                    (T15 T06)
  line      line chart that draws: "pts" [[x, y], ...] in 0-1 units, "labels" on leader dots                     (T06 T15 T17)
  image     screenshot or photo card: "path", "box" [cx, cy, w], spring in, "border" yellow|white glow, "tag"     (T04 T09 T15 T18 T19)
            "highlight": [[x0, y0, x1, y1, on_word, off_word], ...] in image px: a yellow marker sweeps behind the text
            "outline": [[x0, y0, x1, y1, on_word], ...] a rounded outline draws on around a phrase
  marks     arrows, curves, an X, a circle, a dashed line over footage: "items" [{kind, pts, color, on}]           (T16 T15)
  step      "STEP n" header + a 2-3 line checklist that ticks on each item's word                                 (T14 T06)
  burst     photos at 0.6 s each in a box, on an even beat                                                          (T04)
  seq       a rendered RGBA frame sequence (a Blender insert) from its trigger, with a soft contact shadow           (T17)
  slide     Megann's one item device: a drawn screen whose slide hard-swaps on each item's number word          (T08)
  map       Kallaway's returning framework map: every step shown from the start, future steps blurred, the next one
            1.15x, the active step blinks (2-frame states) then unblurs with a yellow tab, done steps dim with a tick  (T06 T08)
            "rows": [[label, detail, on_word], ...] (a row goes active on its word), "title", "y"
  T20 split list (Nate Herk study 11-04, T7 .../kallaway/extra-DfVEGmvgIm_/DECODE.md):
  tease     the list's items as BLURRED numbered tiles under a title, arrow from the caption up; pops in reading order,
            a sheen sweeps it; "returns": [[n, word]] brings it back for "flash" s on each step word (tile n blinks, unblurs) (T20)
  badge     "#n" in yellow on the step word + the item's name typing under it, bottom of the top panel                 (T20 T08)
  cta       the keyword device: "mode" comment | dm (box, keyword types, cursor clicks send, his reply drops in) | follow
            (profile row, cursor clicks FOLLOW, it turns FOLLOWING); "avatar" his face crop                            (T20 T13)
  scan      a glowing line sweeping down a box on "scan"/"check", lighting what it passes                              (T20 T19 T14)
  tint      a colour wash over the panel on the bad thing ("on" .. "off" word)                                         (T20 T16)
  check     a yellow square pops on a screen's corner and a tick draws inside                                           (T20 T14)
  T22 Hormozi whiteboard framework (study 11-06, T7 OB-EDITS/2026-11-06-hormozi-study/; reel DfaGTlsoI7m measured):
  pill      the red stepped title pill over the hook, white heavy italic caps ("font": "brand" = Big Shoulders slanted)   (T22)
  board     the whole framework on one ruled sheet, whips in from the right behind the pill, one column circled        (T22)
  paper     a paper card rising over his chest: marker heading + hand-lettered list, a yellow highlighter on each item
            as he SAYS it ("hl": [[index, word]]), hard exit on the next card                                           (T22)
  label     '#n' + a white strip with the step in marker caps, hard swap on each step word                               (T22)
  quote     an example line in a comic bubble ("as": "caption" = OB's no-bubble version: italic line in quotes)       (T22)
  lower3    the name card on a near-black bar, mid-video at the re-hook                                                (T22)
  ctabar    'COMMENT "WORD"' on a near-black bar for the whole CTA tag                                                   (T22)
  (T22 captions: tmpl.py "captions": {"style": "clean"} -> FX.clean_captions; elements above set the caption band's block.)
  T23 Hormozi step tracker (DfVRSAYoFPf measured 11-06):
  (OB 11-06 "it doesn't have to be purple": every T23 element defaults to "theme": "brand" (his studio frosted, #FFD400, Big
   Shoulders, no boxes); "theme": "purple" is Hormozi's look.)
  tracker   progress panel, numbered circles, the line out of the active step fills over the step, future names blurred (T23)
  steptag   'STEP #n' red tag over a purple name tag on each step word, ~2 s                                            (T23)
  takeover  the full-frame purple summary card (title, numbered rows with emoji); "mode": "chest" = OB's face-on version (T23)
  checks    a checklist that appears row by row and ticks each box 0.45 s after its word                               (T23)
  (pill "font": "poppins", ctabar "style": "text", captions {"font": "poppins", "bold": [phrases]} are the T23 looks.)
  T24 Hormozi stickers + labelled frames (DfXyDVPopFX, OB's second reel, measured 11-06):
  sticker   a line-drawn sticker (money, runner, calendar, doc with highlighted lines, video, dumbbell, plate, scale, steps,
            clock, or an emoji) popping onto the table on its word                                                   (T24)
  tag       a sharp dark-red X tag or dark-green emoji tag in condensed caps                                         (T24)
  minis     the opener: two small grey copies of his frame on the table, each tagged                                 (T24)
  framein   the push-in: his frame as a white-bordered inset over its own blurred zoom (list it first)               (T24)
  (captions "prefix": {"budget": "#1"} puts a number before a word, his "#1 budget".)
  Hormozi upgrade pass (DfXZyinIVtU "6 sales fixes", 11-06): live diagrams on the table
  days      a row of day boxes that fill (white, then yellow) on words, the rest dimming, marker notes above ("5 -> 7", "72 HOURS")
  slot      a dashed outline at the old size + a bar that shrinks to the new one on its word, its value inside, a label above
  sticker   + "enter": "draw" (draws on in 0.35 s) and sparkle strokes on every pop; kinds + browser ("text") and player
  steptag   + "scale" (0.62 = his small FIX #n tags); ctabar + "style": "pill"; captions + "bold_numbers": true
Helpers: font, spring, ease, blink, trigger, shadow_text, rounded_mask, frosted(img), drop_in(t) / slide_up(t) (the measured
Dylan Page panel curves), captions(img, t, words, y) (OB's locked captions: 3 words, live word yellow).

Self-test (no footage): python3 -I tmpl_fx.py selftest OUT_DIR  -> one sheet of every element mid-animation and settled.
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BRAND = json.load(open(os.path.expanduser("~/ob-editor/brand/brand.json")))
FONT = os.path.expanduser(BRAND["font"])
W, H, FPS = 1080, 1920, 30000 / 1001
YEL = tuple(int(BRAND["accent"][i:i + 2], 16) for i in (1, 3, 5))
WHITE, RED, GREEN, GREY = (255, 255, 255), (230, 40, 46), (60, 200, 90), (150, 150, 150)
COLORS = {"yellow": YEL, "white": WHITE, "red": RED, "green": GREEN, "grey": GREY, "blue": (40, 120, 255), "pink": (240, 189, 182)}
SAFE_TOP, SAFE_BOT = BRAND["ig_top_px"], H - BRAND["ig_bottom_px"]
_F, _IMG = {}, {}


# ---------- basics ----------
def font(size, weight="ExtraBold"):
    k = (int(size), weight)
    if k not in _F:
        f = ImageFont.truetype(FONT, int(size))
        try: f.set_variation_by_name(weight)
        except Exception: pass
        _F[k] = f
    return _F[k]


def spring(t, freq=3.2, damp=0.55):
    """0 -> 1 damped spring (POP family): small overshoot, settles in ~0.45 s."""
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; wd = w * math.sqrt(1 - damp ** 2)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))


def ease(t, d):
    x = min(1.0, max(0.0, t / d)) if d > 0 else 1.0
    return x * x * (3 - 2 * x)


def ease_out(t, d):
    x = min(1.0, max(0.0, t / d)) if d > 0 else 1.0
    return 1 - (1 - x) ** 3


def blink(t, t0, n=3):
    """'this one': n flashes at 2 frames on / 2 frames off from t0 (a 1-frame blink is a flash frame to the gate), then steady on."""
    if t < t0: return False
    k = int((t - t0) * FPS)
    return True if k >= 4 * n else (k % 4) < 2


def trigger(el, words, key="on", default=0.0):
    """An element's start: "at" seconds, or the start of the first word matching el[key] (after "after" s), minus "lead" s."""
    if el.get("at") is not None: return float(el["at"])
    w = _n(el.get(key) or "")
    if w:
        after = el.get("after", -1.0)
        for x in words:
            if x["s"] >= after and _n(x["w"]).startswith(w): return x["s"] - el.get("lead", 0.0)   # 11-10: on the word (Karan, Squat U, Hormozi measured 0 to +0.18 s); was 0.15 s early. Set "lead" per element to go early
        return el.get("fallback", 1e9 if default == 0.0 else default)   # its word wasn't heard: stay hidden, never fire at 0 s
    return el.get("fallback", default)


def _n(s):
    """A word for matching: lower case, letters and digits only ("2,467." -> "2467", "she's" -> "shes")."""
    return "".join(c for c in s.lower() if c.isalnum())


def word_end(name, words, after=-1.0):
    for x in words:
        if x["s"] >= after and _n(x["w"]).startswith(_n(name)): return x["e"]
    return None


def load(path, mode="RGBA"):
    k = (path, mode)
    if k not in _IMG: _IMG[k] = Image.open(os.path.expanduser(path)).convert(mode)
    return _IMG[k]


def rounded_mask(w, h, r, bottom_open=False):
    m = Image.new("L", (int(w), int(h)), 0); d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, int(w) - 1, int(h) - 1 + (r if bottom_open else 0)], int(r), fill=255)
    return m


def shadow_text(img, xy, txt, f, fill, anchor="la", alpha=255, track=0, scale=1.0):
    """Text with the brand's soft shadow (y 0.5% W, blur 2.2% W, 60%), no box. track = extra px between letters.
    scale grows/shrinks the whole text about its anchor point (for pops)."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if track:
        widths = [f.getlength(c) for c in txt]; tw = sum(widths) + track * (len(txt) - 1)
        x = xy[0] - (tw / 2 if anchor[0] == "m" else tw if anchor[0] == "r" else 0); y = xy[1]
        for c, wd in zip(txt, widths):
            d.text((x, y), c, font=f, fill=fill + (alpha,) if len(fill) == 3 else fill, anchor="l" + anchor[1]); x += wd + track
    else:
        d.text(xy, txt, font=f, fill=fill + (alpha,) if len(fill) == 3 else fill, anchor=anchor)
    if scale != 1.0:
        bb = lay.getbbox()
        if bb:
            crop = lay.crop(bb); cw, ch = max(1, int(crop.width * scale)), max(1, int(crop.height * scale))
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); lay.alpha_composite(crop.resize((cw, ch), Image.LANCZOS), (int(cx - cw / 2), int(cy - ch / 2)))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); a = lay.split()[3].point(lambda v: int(v * BRAND["shadow"]["alpha"]))
    sh.putalpha(a); sh = sh.filter(ImageFilter.GaussianBlur(W * BRAND["shadow"]["blur_of_width"] / 2))
    img.alpha_composite(sh, (0, int(W * BRAND["shadow"]["y_of_width"]))); img.alpha_composite(lay)


def frosted(src, lift=0.0, gain=0.62, blur=40):
    """A background made from a picture itself (Saraev): heavy blur, a little warmth, darker (or lighter with lift) so text reads."""
    s = src.convert("RGB").resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(blur / 8))
    a = np.asarray(s, np.float32) * gain + lift * 255; a[..., 0] *= 1.04; a[..., 2] *= 0.95
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).convert("RGBA")


def fit_cover(im, w, h):
    s = max(w / im.width, h / im.height); r = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x, y = (r.width - w) // 2, (r.height - h) // 2
    return r.crop((x, y, x + w, y + h))


# Dylan Page's measured panel moves. Slide up (DfQDZtxMo50, 10 fps): 0.30 s accelerating. Drop in (DfVXmUnBInZ, 30 fps, seam
# measured every frame on 3 drop-ins, DfQDZtxMo50's settle agrees): the panel's edge wipes down from the top on an exponential
# ease-out, the gap to rest shrinking to 0.78 of itself every frame (first frame 12% down, 90% by 0.3 s, settled by 0.6 s).
# His zoom-out and the title card's rise use the same curve family. Both return the panel's bottom edge as a fraction (1 = in place).
def expo_out(t, r=0.78): return 0.0 if t < 0 else 1.0 - r ** (t * 30 + 0.5)
def slide_up(t, d=0.30): return 1.0 - ease(t, d) ** 2 if t >= 0 else 1.0
def drop_in(t, d=None): return expo_out(t)


# Dylan Page's zoom-out (DfVXmUnBInZ x4 + DfQDZtxMo50 x2, registered against the settled frame, 11-04): every HARD cut to him full
# frame (an item's number, after a clip with its own sound, the closer) lands 1.21-1.24x zoomed in, centred on the frame, and eases
# out with the gap shrinking to 0.80 a frame (<1% left by 0.45 s); the first 3-4 frames are motion-blurred. Nothing pushes in after
# it settles, and his jump cuts inside the split never zoom (16 checked: 1.000).
def zoom_out(t, start=1.22, r=0.80): return 1.0 + (start - 1.0) * (r ** (max(0.0, t) * 30))


# ---------- captions ----------
def captions(img, t, words, y=1180, n=3, size=64, face=None):
    """OB's locked captions: n words at a time, upper case, live word #FFD400, centred at y, never on his face (moves under it)."""
    cur = [w for w in words if w["s"] - 0.1 <= t]   # 0.1 s early: a line that starts on frame 0 has its caption on frame 0 (no 1-frame flash)
    if not cur or t > cur[-1]["e"] + 0.45: return
    k = len(cur) - 1; grp = cur[k - (k % n):k + 1]
    f = font(size, "ExtraBold"); parts = [w["w"].upper().strip(",.!?") for w in grp]; txt = " ".join(parts)
    if face and face[1] - 40 < y < face[3] + 60: y = face[3] + 70          # clear of the chin
    x = W / 2 - f.getlength(txt) / 2
    for i, p in enumerate(parts):
        shadow_text(img, (x, y), p, f, YEL if i == len(parts) - 1 else WHITE, anchor="lm"); x += f.getlength(p + " ")


# ---------- elements ----------
def draw_title(img, el, t, ctx):
    """Title lines. "sizes"/"colors" per line ([r,g,b] or a COLORS name), "y" = the top of line 1, or the block's centre with
    "y_mode": "center" (T25: Michael Read's block sits at y 1070-1290), "enter": "hard" = all words on from its first frame
    (his title is up at frame 0, no animation), "box": true = his thin rounded outline round the block."""
    words = ctx["words"]; t0 = trigger(el, words); lines = el["lines"] if "lines" in el else [el["words"]]
    acc = {a.upper() for a in el.get("accent", [])}; size0 = el.get("size", 112); y = el.get("y", 300); gap = el.get("gap", 0.14)
    if el.get("until") is not None and t > el["until"]: return
    sizes = []
    for li, line in enumerate(lines):
        sz = (el.get("sizes") or [size0] * len(lines))[li]
        while sz > 56 and font(sz, "Black").getlength(" ".join(line)) > W - 160: sz -= 4
        sizes.append(sz)
    if el.get("y_mode") == "center": y = y - sum(sz * 1.05 for sz in sizes) / 2
    hard = el.get("enter") == "hard"; k = 0; yy = y; tws = []
    for li, line in enumerate(lines):
        size = sizes[li]; f = font(size, "Black"); tw = f.getlength(" ".join(line)); tws.append(tw); x = W / 2 - tw / 2
        lc = el.get("colors", [None] * len(lines))[li]; lc = COLORS.get(lc, WHITE) if isinstance(lc, str) else tuple(lc) if lc else None
        for wd in line:
            ti = t - (t0 + (0 if hard else k * gap)); k += 1
            if ti < 0: x += f.getlength(wd + " "); continue
            p = 1.0 if hard else spring(ti); a = 255 if hard else int(255 * min(1, ti / 0.1))
            shadow_text(img, (x, yy + (1 - p) * 48), wd, f, lc or (YEL if wd.upper().strip(",.") in acc else WHITE), alpha=a)
            x += f.getlength(wd + " ")
        yy += size * 1.05
    if el.get("box") and t >= t0:
        bw = max(tws) + 70; ImageDraw.Draw(img).rounded_rectangle([W / 2 - bw / 2, y - 24, W / 2 + bw / 2, yy + 6], 18, outline=tuple(el.get("box_color", (240, 189, 182))) + (255,), width=4)
    if el.get("underline"):
        tu = t - (t0 + k * gap); tw = tws[-1]; yl = yy - sizes[-1] * 1.05 + sizes[-1] * 1.1
        if tu > 0: ImageDraw.Draw(img).rounded_rectangle([W / 2 - tw / 2, yl, W / 2 - tw / 2 + tw * ease(tu, 0.35), yl + 12], 6, fill=YEL + (255,))


def draw_text(img, el, t, ctx):
    t0 = trigger(el, ctx["words"]); ti = t - t0
    if ti < 0 or (el.get("until") is not None and t > el["until"]): return
    f = font(el.get("size", 72), el.get("weight", "ExtraBold")); s = el["text"]
    if el.get("typeon"): s = s[:max(1, int(len(s) * min(1.0, ti / el.get("type_dur", 0.4))))]
    p = 1.0 if el.get("typeon") else spring(ti); a = int(255 * min(1, ti / 0.1))
    col = COLORS.get(el.get("color", "white"), WHITE)
    shadow_text(img, (el.get("x", W / 2), el.get("y", 400) + (1 - p) * 30), s, f, col, anchor=el.get("anchor", "mm"), alpha=a, track=el.get("track", 0))


def odometer(value, frac):
    """The number shown when an odometer rolling to value is frac (0..1) of the way: low digits spin faster, lands exactly."""
    if frac >= 1: return value
    return int(value * (1 - (1 - frac) ** 3))


def draw_count(img, el, t, ctx):
    t0 = trigger(el, ctx["words"]); tc = t - t0
    if tc < 0: return
    if el.get("mode") == "linear":   # Drew bulk 11-07: big counts tick up evenly over 2.0 s (start it ~1 s before the word: "lead": 1.0), no pop
        v = int(el["value"] * min(1.0, tc / el.get("dur", 2.0))); p = 1.0
    else: v = odometer(el["value"], tc / el.get("dur", 1.0)); p = spring(tc)
    cx, cy = el.get("x", W / 2), el.get("y", 520)
    if el.get("glass"):   # Saraev's frosted number card (no text box: the card is the graphic, the number sits on it)
        cw, ch = el.get("card", (660, 360)); s = 0.9 + 0.1 * p
        base = img.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).filter(ImageFilter.GaussianBlur(16))
        tint = Image.new("RGBA", base.size, (18, 18, 20, 170)); card = Image.alpha_composite(base, tint)
        card = card.resize((int(cw * s), int(ch * s)), Image.LANCZOS); m = rounded_mask(card.width, card.height, 36)
        m = m.point(lambda v: int(v * min(1, tc / 0.12))); img.paste(card, (int(cx - card.width / 2), int(cy - card.height / 2)), m)
    s = f"{v:,}{el.get('suffix', '')}"; f = font(el.get("size", 200), "Black")
    shadow_text(img, (cx, cy + (1 - p) * 40), s, f, YEL, anchor="mm", scale=0.92 + 0.08 * p)
    if el.get("label"): shadow_text(img, (cx, cy - el.get("size", 200) * 0.62), el["label"].upper(), font(46, "ExtraBold"), WHITE, anchor="mm", track=10)
    if el.get("unit"): shadow_text(img, (cx, cy + el.get("size", 200) * 0.6), el["unit"].upper(), font(58, "ExtraBold"), WHITE, anchor="mm")


def draw_bar(img, el, t, ctx):
    t0 = trigger(el, ctx["words"]); tb = t - t0
    if tb < -0.4: return
    x, y0, bw, bh = el.get("x", 700), el.get("y", 820), el.get("w", 120), el.get("h", 460)   # y0 = the bar's base line
    a = min(1.0, (tb + 0.4) / 0.2); d = ImageDraw.Draw(img)
    frm, to = el.get("from", 0.0), el.get("to", 0.5); g = frm + (to - frm) * spring(max(0, tb), 2.6, 0.7)
    col = COLORS.get(el.get("color", "red"), RED)
    d.rectangle([x, y0 - bh * frm, x + bw, y0], fill=tuple(int(c * 0.55) for c in col) + (int(255 * a),))
    if g > frm: d.rectangle([x, y0 - bh * g, x + bw, y0 - bh * frm], fill=col + (int(255 * a),))
    if el.get("value") and tb >= 0: shadow_text(img, (x + bw / 2, y0 - bh * g - 60), el["value"], font(92, "Black"), YEL if el.get("color") != "yellow" else WHITE, anchor="mm", alpha=int(255 * min(1, tb / 0.1)))
    if el.get("label"): shadow_text(img, (x - 40, y0 - 60), el["label"].upper(), font(70, "Black"), WHITE, anchor="rm", alpha=int(255 * a))


def draw_icons(img, el, t, ctx):
    words = ctx["words"]; t0 = trigger(el, words)
    if t < t0: return
    x0, y0, step, r = el.get("x", 240), el.get("y", 260), el.get("step", 62), el.get("r", 20); a = min(1.0, (t - t0) / 0.2)
    filled = 0
    for n, w in el.get("fill", []):
        ts = trigger({"on": w, "lead": 0.0}, words, default=1e9)
        if t >= ts: filled = n
    newest = filled; d = ImageDraw.Draw(img)
    for i in range(100):
        cx, cy = x0 + (i % 10) * step, y0 + (i // 10) * step
        on = i < filled
        col = YEL if on else (210, 208, 222)
        if on and i == newest - 1 and not blink(t, max(trigger({"on": el["fill"][-1][1], "lead": 0.0}, words, 1e9) if el.get("fill") else 0, 0)): col = (255, 240, 150)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (int(255 * a),))
    if el.get("label") and filled:
        shadow_text(img, (x0 + 4.5 * step, y0 + 10 * step + 30), el["label"].format(n=filled), font(78, "Black"), WHITE, anchor="mm")


def draw_line(img, el, t, ctx):
    t0 = trigger(el, ctx["words"]); tl = t - t0
    if tl < 0: return
    bx, by, bw, bh = el.get("box", (140, 300, 800, 560)); d = ImageDraw.Draw(img); a = int(255 * min(1, tl / 0.25))
    d.line([bx, by + bh, bx + bw, by + bh], fill=(255, 255, 255, a), width=4); d.line([bx, by, bx, by + bh], fill=(255, 255, 255, a), width=4)
    pts = [(bx + px * bw, by + bh - py * bh) for px, py in el["pts"]]; prog = ease(tl - 0.25, el.get("dur", 0.9))
    if prog > 0:
        seg = [(pts[0][0] + (pts[-1][0] - pts[0][0]) * prog)]
        drawn = [p for p in pts if p[0] <= seg[0]]
        if len(drawn) < len(pts):
            i = len(drawn); p0, p1 = pts[i - 1], pts[i]; u = (seg[0] - p0[0]) / max(1e-6, p1[0] - p0[0])
            drawn = drawn + [(p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)]
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).line(drawn, fill=YEL + (160,), width=22, joint="curve")
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10))); ImageDraw.Draw(img).line(drawn, fill=YEL + (255,), width=9, joint="curve")
        for (px, py), lab in zip(pts, el.get("labels", [None] * len(pts))):
            if lab and px <= seg[0]: d.ellipse([px - 13, py - 13, px + 13, py + 13], fill=WHITE + (255,)); shadow_text(img, (px, py - 50), lab, font(52, "ExtraBold"), WHITE, anchor="mm")


def _card_of(el):
    im = load(el["path"], "RGBA"); cx, cy, w = el.get("box", (W / 2, 640, 860))
    h = round(im.height * w / im.width)
    return im.resize((int(w), int(h)), Image.LANCZOS), cx, cy, w, h


def draw_image(img, el, t, ctx):
    words = ctx["words"]; t0 = trigger(el, words); ti = t - t0
    if ti < 0 or (el.get("until") is not None and t > el["until"]): return
    cache = ctx.setdefault("cache", {}); key = ("card", el["path"], tuple(el.get("box", ())))
    if key not in cache: cache[key] = _card_of(el)
    card, cx, cy, w, h = cache[key]; card = card.copy(); scale = w / load(el["path"]).width
    dc = ImageDraw.Draw(card)
    for x0, y0, x1, y1, on, *off in el.get("highlight", []):   # a yellow marker sweeps behind the words as he reads them
        hs = trigger({"on": on, "lead": 0.05}, words, default=1e9); he = word_end(off[0], words) if off else None
        he = he if he and he > hs else hs + 0.6
        if t >= hs:
            u = ease(t - hs, he - hs); x0s, x1s = x0 * scale, x1 * scale
            mark = Image.new("RGBA", card.size, (0, 0, 0, 0)); ImageDraw.Draw(mark).rectangle([x0s, y0 * scale, x0s + (x1s - x0s) * u, y1 * scale], fill=YEL + (255,))
            card = Image.composite(Image.fromarray(np.minimum(np.asarray(card), np.asarray(mark.convert("RGBA")) + (np.asarray(mark)[..., 3:4] == 0) * 255).astype(np.uint8)), card, mark.split()[3])
    for x0, y0, x1, y1, on in el.get("outline", []):           # a rounded outline draws on around the phrase he names
        os_ = trigger({"on": on, "lead": 0.1}, words, default=1e9)
        if t >= os_: _draw_outline(card, [x0 * scale - 8, y0 * scale - 6, x1 * scale + 8, y1 * scale + 6], ease(t - os_, 0.3), el.get("outline_color", "red"))
    if el.get("enter") == "rise":   # T26 Drew: opacity 0->1 ease-out cubic over 0.40 s, y +70 -> 0, blur 8 -> 0 over 0.3 s, no scale pop
        u = 1 - (1 - min(1.0, ti / 0.40)) ** 3; cy = cy + 70 * (1 - u); bl = 8 * max(0.0, 1 - ti / 0.3)
        if bl > 0.3: card = card.filter(ImageFilter.GaussianBlur(bl))
        if u < 1: card.putalpha(card.split()[3].point(lambda v: int(v * u)))
    p = spring(ti); s = 0.86 + 0.14 * p if el.get("pop", True) and el.get("enter") != "rise" else 1.0
    z = 1.0 + el.get("push", 0.012) * max(0.0, ti)                    # a slow push: a held card is never still
    cw, ch = max(1, int(w * s * z)), max(1, int(h * s * z)); c2 = card.resize((cw, ch), Image.LANCZOS)
    m = rounded_mask(cw, ch, el.get("radius", 18)).point(lambda v: int(v * (1.0 if el.get("snap") else min(1, ti / 0.1))))   # snap: a hard swap from the card before it (11-10: the 0.1 s ramp ghosted back-to-back cards)
    if el.get("enter") == "rise": m = m.point(lambda v: int(v * (1 - (1 - min(1.0, ti / 0.40)) ** 3)))
    if el.get("border"):
        col = COLORS.get(el["border"], YEL); gl = Image.new("RGBA", (cw + 60, ch + 60), (0, 0, 0, 0))
        ImageDraw.Draw(gl).rounded_rectangle([30, 30, 30 + cw, 30 + ch], el.get("radius", 18) + 4, outline=col + (220,), width=10)
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(8)), (int(cx - cw / 2 - 30), int(cy - ch / 2 - 30)))
    if el.get("cutout"):   # Karan's board pictures: a clean cut-out (the PNG's own alpha), no card, no border
        c2.putalpha(Image.fromarray(np.minimum(np.asarray(c2.split()[3]), np.asarray(m)))); img.alpha_composite(c2, (int(cx - cw / 2), int(cy - ch / 2)))
    else: img.paste(c2, (int(cx - cw / 2), int(cy - ch / 2)), m)
    if el.get("border"):
        ImageDraw.Draw(img).rounded_rectangle([cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2], el.get("radius", 18), outline=COLORS.get(el["border"], YEL) + (255,), width=5)
    if el.get("tag"): shadow_text(img, (cx + cw / 2 - 10, cy - ch / 2 - 34), el["tag"], font(38, "ExtraBold"), WHITE, anchor="rm")


def _draw_outline(im, box, u, color):
    """A rounded rectangle outline drawn on clockwise from the top-left, u = 0..1."""
    x0, y0, x1, y1 = box; col = COLORS.get(color, RED); per = 2 * ((x1 - x0) + (y1 - y0)); L = per * u
    path = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]; d = ImageDraw.Draw(im); done = 0.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        seg = math.hypot(bx - ax, by - ay)
        if done >= L: break
        f = min(1.0, (L - done) / seg); d.line([ax, ay, ax + (bx - ax) * f, ay + (by - ay) * f], fill=col + (255,), width=7); done += seg


def draw_marks(img, el, t, ctx):
    """Marks on footage, in Squat University's grammar: red = the fault, green = the fix, yellow = force or the key word."""
    words = ctx["words"]; pop = el.get("pop")   # T16 bulk 11-07: Squat U's marks pop on in one frame and hold 1-3 s ("pop": true)
    for it in el["items"]:
        t0 = trigger(it, words); ti = t - t0; hold = it.get("hold", 2.0 if pop else None)
        if ti < 0 or (hold and ti > hold): continue
        c = it.get("color", "red"); col = tuple(c) if isinstance(c, (list, tuple)) else COLORS.get(c, RED)
        u = ease(ti, it.get("dur", 0.03 if pop else 0.22)); kind = it["kind"]; wdt = it.get("width", 12)
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        if kind in ("arrow", "line", "dash"):
            (ax, ay), (bx, by) = it["pts"][:2]; ex, ey = ax + (bx - ax) * u, ay + (by - ay) * u
            if kind == "dash":
                n = int(math.hypot(ex - ax, ey - ay) // 34)
                for k in range(n): f0, f1 = k / max(1, n) , (k + 0.55) / max(1, n); d.line([ax + (ex - ax) * f0, ay + (ey - ay) * f0, ax + (ex - ax) * f1, ay + (ey - ay) * f1], fill=col + (255,), width=wdt)
            else: d.line([ax, ay, ex, ey], fill=col + (255,), width=wdt)
            if kind == "arrow" and u > 0.6:
                ang = math.atan2(ey - ay, ex - ax); hl = it.get("head", 54)
                d.polygon([(ex + 8 * math.cos(ang), ey + 8 * math.sin(ang)), (ex - hl * math.cos(ang - 0.45), ey - hl * math.sin(ang - 0.45)), (ex - hl * math.cos(ang + 0.45), ey - hl * math.sin(ang + 0.45))], fill=col + (255,))
        elif kind == "curve":
            (ax, ay), (qx, qy), (bx, by) = it["pts"][:3]; n = max(2, int(40 * u))
            pts = [((1 - s) ** 2 * ax + 2 * (1 - s) * s * qx + s * s * bx, (1 - s) ** 2 * ay + 2 * (1 - s) * s * qy + s * s * by) for s in [u * k / n for k in range(n + 1)]]
            d.line(pts, fill=col + (255,), width=wdt, joint="curve")
            if u > 0.95:
                (px, py), (ex, ey) = pts[-2], pts[-1]; ang = math.atan2(ey - py, ex - px); hl = it.get("head", 50)
                d.polygon([(ex, ey), (ex - hl * math.cos(ang - 0.45), ey - hl * math.sin(ang - 0.45)), (ex - hl * math.cos(ang + 0.45), ey - hl * math.sin(ang + 0.45))], fill=col + (255,))
        elif kind == "circle":
            (cx, cy), (rx, ry) = it["pts"][:2]; d.arc([cx - rx, cy - ry, cx + rx, cy + ry], -100, -100 + 360 * u, fill=col + (255,), width=wdt)
        elif kind == "x":
            (cx, cy), r = it["pts"][0], it.get("r", 60); s1 = min(1, u * 2); s2 = max(0, u * 2 - 1)
            d.line([cx - r, cy - r, cx - r + 2 * r * s1, cy - r + 2 * r * s1], fill=col + (255,), width=wdt + 6)
            if s2 > 0: d.line([cx + r, cy - r, cx + r - 2 * r * s2, cy - r + 2 * r * s2], fill=col + (255,), width=wdt + 6)
        if it.get("label") and u >= 1: shadow_text(lay, tuple(it.get("label_at", it["pts"][-1])), it["label"].upper(), font(58, "Black"), col, anchor="mm")
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh.putalpha(lay.split()[3].point(lambda v: int(v * 0.45)))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (0, 4)); img.alpha_composite(lay)


def draw_step(img, el, t, ctx):
    words = ctx["words"]; t0 = trigger(el, words); ts = t - t0
    if ts < 0 or (el.get("until") is not None and t > el["until"]): return
    y = el.get("y", 290); p = spring(ts)
    shadow_text(img, (W / 2, y + (1 - p) * 40), f"STEP {el['n']}", font(64, "ExtraBold"), YEL, anchor="mm", track=8, alpha=int(255 * min(1, ts / 0.1)))
    shadow_text(img, (W / 2, y + 92 + (1 - p) * 40), el["title"].upper(), font(98, "Black"), WHITE, anchor="mm", alpha=int(255 * min(1, ts / 0.1)))
    for i, (txt, on) in enumerate(el.get("checks", [])):
        tc = t - trigger({"on": on, "lead": 0.1}, words, default=1e9); yy = y + 210 + i * 76
        if tc < 0: continue
        f = font(56, "ExtraBold"); x = W / 2 - (f.getlength(txt) + 70) / 2
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); u = ease(tc, 0.18)
        d.line([(x, yy - 4), (x + 22 * min(1, u * 2), yy - 4 + 22 * min(1, u * 2))], fill=YEL + (255,), width=12)
        if u > 0.5: d.line([(x + 22, yy + 18), (x + 22 + 40 * (u - 0.5) * 2, yy + 18 - 52 * (u - 0.5) * 2)], fill=YEL + (255,), width=12)
        img.alpha_composite(lay); shadow_text(img, (x + 70, yy + 4), txt.upper(), f, WHITE, anchor="lm", alpha=int(255 * min(1, tc / 0.12)))


def draw_burst(img, el, t, ctx):
    t0 = trigger(el, ctx["words"]); tb = t - t0; each = el.get("each", 0.6)
    if tb < 0 or tb >= each * len(el["paths"]): return
    i = int(tb // each); cx, cy, w, h = el.get("box", (W / 2, 438, W, 876))
    ph = fit_cover(load(el["paths"][i], "RGB"), int(w), int(h)); img.paste(ph, (int(cx - w / 2), int(cy - h / 2)))


def draw_seq(img, el, t, ctx):
    """A rendered RGBA frame sequence (a Blender insert) playing from its trigger, held on its last frame: "dir" of PNGs,
    "box" [cx, cy, w], optional soft contact "shadow" [cx, cy, rx, ry] drawn under it."""
    t0 = trigger(el, ctx["words"]); ts = t - t0
    if ts < 0 or (el.get("until") is not None and t > el["until"]): return
    cache = ctx.setdefault("cache", {}); k = ("seq", el["dir"])
    if k not in cache: cache[k] = sorted(os.path.join(el["dir"], f) for f in os.listdir(el["dir"]) if f.endswith(".png") and not f.startswith("._"))
    fs = cache[k]; i = min(len(fs) - 1, int(ts * el.get("fps", FPS)))
    cx, cy, w = el.get("box", (W / 2, 640, 1000)); fr = load(fs[i], "RGBA"); h = round(fr.height * w / fr.width)
    if el.get("shadow"):
        sx, sy, rx, ry = el["shadow"]; sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([sx - rx, sy - ry, sx + rx, sy + ry], fill=(0, 0, 0, int(150 * min(1.0, ts / 0.3))))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)))
    img.alpha_composite(fr.resize((int(w), h), Image.LANCZOS), (int(cx - w / 2), int(cy - h / 2)))
    _IMG.pop((fs[i], "RGBA"), None)   # frames are used once: don't keep them all in memory


def draw_map(img, el, t, ctx):
    """Kallaway's returning map (decode §3 E2, 7 of 8 reels, back 3-6 times a reel): the whole framework from frame one with the
    steps not covered yet blurred, an open loop the viewer can see. Rows are thin outlines, part of the drawing (no text boxes)."""
    words = ctx["words"]; t0 = trigger(el, words, default=0.0)
    if t < t0 or (el.get("until") is not None and t > el["until"]): return
    rows = el["rows"]; ons = [trigger({"on": r[2], "lead": 0.0}, words, default=1e9) for r in rows]
    act = max((i for i, s in enumerate(ons) if t >= s), default=-1)
    y0, rh, gap = el.get("y", 420), el.get("row_h", 118), el.get("gap", 22); x0, x1 = 120, W - 120
    if el.get("title"): shadow_text(img, (W / 2, y0 - 120), el["title"].upper(), font(92, "Black"), WHITE, anchor="mm")
    fa, fb = font(68, "Black"), font(46, "ExtraBold")
    for i, (label, detail, _) in enumerate(rows):
        state = "done" if i < act else "active" if i == act else "next" if i == act + 1 else "future"
        s = 1.15 if state == "next" else 1.0
        if state == "active":
            ta = t - ons[i]; s = 1.0 + 0.15 * (1 - ease(ta, 0.2))   # settles from the pre-enlarged size as it goes live
        w, h = (x1 - x0) * s, rh * s; cx, cy = W / 2, y0 + i * (rh + gap) + rh / 2
        lay = Image.new("RGBA", (int(w) + 40, int(h) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); bx = (20, 20, 20 + w, 20 + h)
        on = state != "active" or blink(t, ons[i], n=3)
        col = WHITE if state in ("active", "next") else (150, 150, 150)
        d.rounded_rectangle(bx, 20, outline=(YEL if state == "active" and on else (70, 70, 70)) + (255,), width=3)
        if state == "active": d.rounded_rectangle((20, 20, 34, 20 + h), 6, fill=YEL + (255,))
        d.text((60, 20 + h / 2), f"{i + 1:02d}", font=fb, anchor="lm", fill=(GREY if state != "active" else YEL) + (255,))
        d.text((150, 20 + h / 2), label.upper(), font=fa, anchor="lm", fill=col + (255,))
        if detail: d.text((20 + w - 30, 20 + h / 2), detail.upper(), font=fb, anchor="rm", fill=(YEL if state == "active" else col) + (255,))
        if state == "done":
            tx = 20 + w - 40 - (fb.getlength(detail.upper()) if detail else 0) - 60
            d.line([(tx, 20 + h / 2), (tx + 12, 20 + h / 2 + 14), (tx + 36, 20 + h / 2 - 16)], fill=YEL + (255,), width=8)
        if state in ("future", "next"): lay = lay.filter(ImageFilter.GaussianBlur(11))
        elif state == "active" and t - ons[i] < 0.44:   # blink first, then the label unblurs over 0.2 s
            r = 11 * (1 - ease(t - ons[i] - 0.24, 0.2)); lay = lay.filter(ImageFilter.GaussianBlur(r)) if r > 0.5 else lay
        if state == "done": lay.putalpha(lay.split()[3].point(lambda v: int(v * 0.55)))
        img.alpha_composite(lay, (int(cx - w / 2 - 20), int(cy - h / 2 - 20)))


def draw_slide(img, el, t, ctx):
    """Megann's one item device (her #1 reel: a laptop slide on screen 71-95% of the runtime): a drawn screen whose slide hard-swaps
    on each item's spoken number word, item number in #FFD400, the rule in white caps (Big Shoulders, not her serif + lime).
    "items": [[on_word, "the rule"], ...], "box": [cx, cy, w, h]. A device, not a text box: the screen is the graphic."""
    words = ctx["words"]; ons = [trigger({"on": it[0], "lead": 0.0}, words, default=1e9) for it in el["items"]]
    k = max((i for i, s in enumerate(ons) if t >= s), default=-1)
    if k < 0 and el.get("at") is None: return
    cx, cy, w, h = el.get("box", (W / 2, 520, 860, 470)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - w / 2 - 14, cy - h / 2 - 14, cx + w / 2 + 14, cy + h / 2 + 14], 26, fill=(28, 28, 30, 255))   # bezel
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 14, fill=(16, 22, 20, 255))                       # screen
    if k < 0: return
    num, rule = f"{k + 1:02d}", el["items"][k][1].upper()
    d.text((cx - w / 2 + 40, cy - h / 2 + 30), num, font=font(130, "Black"), fill=YEL + (255,))
    f = font(84, "Black"); lines, cur = [], ""
    for wd in rule.split():
        if f.getlength((cur + " " + wd).strip()) > w - 80: lines.append(cur); cur = wd
        else: cur = (cur + " " + wd).strip()
    lines.append(cur)
    for i, ln in enumerate(lines[:3]): d.text((cx - w / 2 + 40, cy - h / 2 + 190 + i * 88), ln, font=f, fill=WHITE + (255,))


# ---------- T20 split list (Nate Herk study, 11-04: kallaway/extra-DfVEGmvgIm_/DECODE.md) ----------
_PANEL = {}
def _panel_bg(w, h):
    """The warm dark board (tmpl.board's look: never pure black, M38) cut to w x h, with the faint 16 px dot grid."""
    k = (int(w), int(h))
    if k not in _PANEL:
        g = Image.linear_gradient("L").resize(k); a = np.dstack([np.asarray(g, np.float32) * f + c for f, c in ((0.10, 30), (0.08, 24), (0.06, 20))])
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(im)
        for y in range(8, k[1], 16):
            for x in range(8, k[0], 16): d.point((x, y), fill=(255, 255, 255, 14))
        _PANEL[k] = im
    return _PANEL[k]


def _cursor(img, x, y, s=1.0, press=False):
    """A plain arrow pointer (white, dark outline), tip at (x, y); press = the 3-frame click squish."""
    k = 0.86 if press else 1.0
    pts = [(0, 0), (0, 46), (12, 35), (21, 55), (30, 51), (21, 32), (36, 32)]
    pts = [(x + px * s * k, y + py * s * k) for px, py in pts]
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(px + 3, py + 4) for px, py in pts], fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4))); d = ImageDraw.Draw(img)
    d.polygon(pts, fill=WHITE + (255,), outline=(20, 20, 20, 255)); d.line(pts + [pts[0]], fill=(20, 20, 20, 255), width=3)


def _avatar(path, size):
    """A round avatar from a picture (his face crop); a plain yellow disc with 'OB' when there's no picture."""
    m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    if path:
        a = fit_cover(load(path, "RGB"), size, size).convert("RGBA")
    else:
        a = Image.new("RGBA", (size, size), YEL + (255,)); ImageDraw.Draw(a).text((size / 2, size / 2), "OB", font=font(int(size * 0.46), "Black"), anchor="mm", fill=(20, 20, 20, 255))
    a.putalpha(m); return a


def draw_tease(img, el, t, ctx):
    """Nate Herk's opener and close (3 of his 4 outliers): the list's items shown from frame one as a grid of BLURRED tiles, each
    labelled #1..#n, under a title ('4 Plugins'), an arrow from the caption up to it. Tiles pop in reading order 0.1 s apart, a
    sheen sweeps them; the same frame comes back at the CTA so the end loops into the start. OB's upgrade (Kallaway's returning
    map, 7 of 8 Kallaway reels): "returns": [[n, word], ...] brings the grid back for "flash" s on each step word, tile n blinks
    (2-frame states) and unblurs, done tiles stay sharp. Tiles are his real receipts (the meal, the label, the app), blurred.
    "tiles": [paths], "title": [[words]], "accent": [words], "box": [x0, y0, x1, y1] (the grid area), "cols": 2, "panel": [0, 0, W, seam]."""
    words = ctx["words"]; t0 = trigger(el, words, default=0.0); until = el.get("until", 1e9)
    rets = [(int(n), trigger({"on": w, "lead": 0.0}, words, default=1e9)) for n, w in el.get("returns", [])]
    flash = el.get("flash", 0.75); show = t0 <= t <= until; act = None
    if el.get("base_lines") is not None and ctx.get("line") not in el["base_lines"]: show = False   # the full grid only on its own lines; returns anywhere
    for n, tw in rets:
        if tw <= t < tw + flash: show, act = True, (n, t - tw)
    if not show: return
    revealed = {n for n, tw in rets if t >= tw + flash}
    if el.get("reveal_all_after") is not None and t >= el["reveal_all_after"]: revealed = set(range(1, len(el["tiles"]) + 1))
    px0, py0, px1, py1 = el.get("panel", (0, 0, W, 876))
    img.alpha_composite(_panel_bg(px1 - px0, py1 - py0), (px0, py0))
    ti = t - t0 if act is None else 9.0                         # a return shows the grid already built (Kallaway: hard cut, drawn)
    x0, y0, x1, y1 = el.get("box", (120, 420, 960, 760)); tiles = el["tiles"]; cols = el.get("cols", 2); gap = el.get("gap", 26)
    rows = (len(tiles) + cols - 1) // cols; tw_ = (x1 - x0 - gap * (cols - 1)) / cols; th = (y1 - y0 - gap * (rows - 1)) / rows
    cache = ctx.setdefault("cache", {}); fl = font(int(th * 0.42), "Black")
    for i, p in enumerate(tiles):
        n = i + 1; r, c = divmod(i, cols); in_row = min(cols, len(tiles) - r * cols)
        tx = x0 + (x1 - x0 - (in_row * tw_ + (in_row - 1) * gap)) / 2 + c * (tw_ + gap); ty = y0 + r * (th + gap)
        tp = ti - 0.1 * i
        if tp < 0: continue
        state = "live" if act and act[0] == n else "done" if n in revealed else "blur"
        kb = ("tease", p, int(tw_), int(th))
        if kb not in cache:
            sharp = fit_cover(load(p, "RGB"), int(tw_), int(th)); a = np.asarray(sharp.filter(ImageFilter.GaussianBlur(int(th * 0.09))), np.float32) * 0.62
            cache[kb] = (sharp.convert("RGBA"), Image.fromarray(a.astype(np.uint8)).convert("RGBA"))
        sharp, blur = cache[kb]
        if state == "live":
            u = ease(act[1] - 0.4, 0.2)   # 3 blinks (0.4 s), then the unblur over 0.2 s
            tile = Image.blend(blur, sharp, u) if u > 0 else blur.copy()
            on = blink(t, t - act[1], n=3)
        else:
            tile = sharp.copy() if state == "done" else blur.copy(); on = True
        sc = 0.86 + 0.14 * spring(tp); cw, ch = max(1, int(tw_ * sc)), max(1, int(th * sc))
        tile = tile.resize((cw, ch), Image.LANCZOS); m = rounded_mask(cw, ch, 18).point(lambda v: int(v * min(1, tp / 0.1)))
        if state == "blur":   # the sheen: a soft white band sweeping across every blurred tile, every 2.4 s
            sp = ((ti - 0.35) % 2.4) / 0.6
            if 0 <= sp <= 1:
                band = Image.new("L", (cw, ch), 0); bx = -0.4 * cw + sp * 1.8 * cw + (tx - x0) * 0.25
                ImageDraw.Draw(band).polygon([(bx, 0), (bx + cw * 0.22, 0), (bx + cw * 0.12, ch), (bx - cw * 0.10, ch)], fill=110)
                tile.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (cw, ch), 255)] * 3, band.filter(ImageFilter.GaussianBlur(14)))))
        X, Y = int(tx + (tw_ - cw) / 2), int(ty + (th - ch) / 2)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([X + 4, Y + 10, X + cw + 4, Y + ch + 10], 18, fill=(0, 0, 0, 120))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); img.paste(tile, (X, Y), m)
        ol = Image.new("RGBA", img.size, (0, 0, 0, 0))   # on its own layer: a translucent outline drawn straight onto the frame would punch its alpha
        ImageDraw.Draw(ol).rounded_rectangle([X, Y, X + cw - 1, Y + ch - 1], 18, width=4 if state == "live" else 2,
                                             outline=((YEL if on else (90, 90, 90)) + (255,)) if state == "live" else (255, 255, 255, 60))
        img.alpha_composite(ol)
        lab = f"#{n}"
        if state == "done" or (state == "live" and act[1] >= 0.45):   # revealed: the label moves to the corner so the receipt reads
            shadow_text(img, (X + 18, Y + 12), lab, font(int(th * 0.26), "Black"), YEL, anchor="lt")
        else:
            shadow_text(img, (X + cw / 2, Y + ch / 2), lab, fl, YEL if state == "live" and on else WHITE, anchor="mm", alpha=int(255 * min(1, tp / 0.1)))
    if el.get("title"):
        acc = {a.upper() for a in el.get("accent", [])}; f = font(el.get("title_size", 96), "Black"); yy = el.get("title_y", 300)
        for li, line in enumerate(el["title"]):
            tl = t - (t0 + el.get("title_gap", 0.25) * li) if act is None else 9.0
            if tl < 0: continue
            txt = " ".join(line).upper(); x = W / 2 - f.getlength(txt) / 2
            for wd in line:
                shadow_text(img, (x, yy + li * f.size * 1.02 + (1 - spring(tl)) * 30), wd.upper(), f, YEL if wd.upper() in acc else WHITE, alpha=int(255 * min(1, tl / 0.1)))
                x += f.getlength(wd.upper() + " ")
    if el.get("arrow", True) and act is None and ti >= 0.1:   # from the caption up to the grid (Nate: red, 0.1 s in); OB: #FFD400
        u = ease(ti - 0.1, 0.18); ax, ay0, ay1 = W / 2, el.get("arrow_from", py1 - 14), y1 + 26
        ey = ay0 - (ay0 - ay1) * u; d = ImageDraw.Draw(img)
        d.line([ax, ay0, ax, ey + 20], fill=YEL + (255,), width=12)
        if u > 0.5: d.polygon([(ax, ey - 6), (ax - 30, ey + 34), (ax + 30, ey + 34)], fill=YEL + (255,))


def draw_badge(img, el, t, ctx):
    """The item number on the step word (Nate: a big mint '#2' on the cut, -70 to +130 ms of 'Second', the item's name typed under
    it). OB: '#n' in Big Shoulders Black #FFD400, the name in white letter-spaced caps typing on 0.12 s later, at the bottom of the
    top panel (his captions keep the seam). "n", "name", "on", "delay" (s after the word, e.g. the tease return's flash), "y"."""
    t0 = trigger(el, ctx["words"]) + el.get("delay", 0.0); tb = t - t0
    if tb < 0 or (el.get("until") is not None and t > el["until"]): return
    y = el.get("y", 690); p = spring(tb, freq=3.6); a = int(255 * min(1, tb / 0.08))
    shadow_text(img, (W / 2, y), f"#{el['n']}", font(el.get("size", 150), "Black"), YEL, anchor="mm", alpha=a, scale=1.25 - 0.25 * p)
    if el.get("name"):
        tn = tb - 0.12
        if tn > 0:
            s = el["name"].upper(); s = s[:max(1, int(len(s) * min(1.0, tn / el.get("type_dur", 0.35))))]
            shadow_text(img, (W / 2, y + el.get("size", 150) * 0.66), s, font(62, "ExtraBold"), WHITE, anchor="mm", track=6)


def draw_itemno(img, el, t, ctx):
    """Dylan Page's list counter (DfVXmUnBInZ, "5 changes"): the item's number sits quietly at the bottom left of the top panel
    (x 105-188, y 732-840 at 1080x1920: ~108 px tall, 36 px above the seam), soft white-grey, from the item's ordinal word until the
    next item, at the same spot over a full-frame clip too. OB: Big Shoulders Black, white at 78%, brand shadow.
    "n", "on" (the ordinal word: "first", "second", "number"), "after", "until" (s) or "until_on" (the next item's word), "x", "y"."""
    el2 = dict(el); el2.setdefault("lead", 0.0); t0 = trigger(el2, ctx["words"])   # on the cut, never early over the last item
    if t < t0 or (el.get("until") is not None and t > el["until"]): return
    if el.get("until_on") and t >= trigger({"on": el["until_on"], "after": t0 + 0.3, "lead": el.get("lead", 0.0)}, ctx["words"], default=1e9): return
    shadow_text(img, (el.get("x", 105), el.get("y", 840)), str(el["n"]), font(el.get("size", 150), "Black"), WHITE, anchor="ls",
                alpha=int(200 * min(1.0, (t - t0) / 0.1)))


def title_card(lines, seam, bg, t):
    """Dylan Page's item title card (DfVXmUnBInZ: IRAN WAR, Possible Impeachment, NO BIG NEW TRUMP LAWS, VETO) in the top panel:
    the item named in 1-4 words, white heavy condensed, as big as fits (block 460-1030 px wide, 380-630 tall), centred a little
    below the panel's middle (y ~460 of 876), over the previous receipt blurred and darkened. It rises the last 28% of its height into
    place from behind its own bottom edge (same exponential as the drop-in, settled ~0.4 s), then grows 4% a second.
    OB: Big Shoulders Black, white, brand shadow. lines: ["IRAN", "WAR"]; bg: an RGB image (already fitted W x seam)."""
    k = ("tc", tuple(lines), seam)
    if k not in _IMG:
        size = 400
        while size > 60:
            f = font(size, "Black"); ws = [f.getlength(s) for s in lines]; lh = size * 0.86
            if max(ws) <= W * 0.86 and lh * len(lines) <= seam * 0.66: break
            size -= 8
        lay = Image.new("RGBA", (W, seam), (0, 0, 0, 0)); cy = seam * 0.525; y0 = cy - lh * len(lines) / 2
        for i, s in enumerate(lines): shadow_text(lay, (W / 2, y0 + lh * (i + 0.5)), s, f, WHITE, anchor="mm")
        _IMG[k] = (lay, lay.getbbox())
    lay, bb = _IMG[k]; out = bg.copy()
    if not bb: return out
    z = 1.0 + 0.04 * max(0.0, t); crop = lay.crop(bb); cw, ch = round(crop.width * z), round(crop.height * z)
    crop = crop.resize((cw, ch), Image.BICUBIC); cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    rise = 0.28 * ch * (1.0 - expo_out(t)); bottom = int(cy + ch / 2)
    txt = Image.new("RGBA", (W, seam), (0, 0, 0, 0)); txt.alpha_composite(crop, (int(cx - cw / 2), int(cy - ch / 2 + rise)))
    if rise > 0.5:
        a = np.asarray(txt.split()[3]).copy(); a[bottom:] = 0; txt.putalpha(Image.fromarray(a))
    out.alpha_composite(txt); return out


def draw_cta(img, el, t, ctx):
    """Nate Herk's CTA device (on all 3 of his outliers that end on a keyword): his avatar + a comment box where the keyword types
    letter by letter (done ~0.2 s before he says it), a cursor glides to send and clicks, then a DM notification ('Here you go!')
    drops in, over the opener's frame so the reel loops. Drawn UI in brand (no IG logo, no other app's look).
    "mode": "comment" | "dm" | "follow"; "keyword"; "avatar": PATH (his face crop); "name": "OB"; "reply": "here you go";
    "handle": "@ob_health.fit"; "on": the keyword word; "lead" (s the typing starts before it, default 0.6); "y" (box centre)."""
    words = ctx["words"]; el2 = dict(el); el2.setdefault("lead", 0.6); t0 = trigger(el2, words); tc = t - t0
    if tc < 0 or (el.get("until") is not None and t > el["until"]): return
    mode = el.get("mode", "comment"); y = el.get("y", 770); av = _avatar(el.get("avatar"), 96)
    if mode == "follow":
        bw, bh = 820, 140; x0 = W / 2 - bw / 2; a = min(1.0, tc / 0.12); click = 0.75
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle([x0, y - bh / 2, x0 + bw, y + bh / 2], 34, fill=(22, 22, 24, 235), outline=(255, 255, 255, 40), width=2)
        lay.alpha_composite(av, (int(x0 + 22), int(y - 48)))
        d.text((x0 + 140, y - 18), el.get("name", "OB HEALTH"), font=font(50, "Black"), fill=WHITE + (255,), anchor="lm")
        d.text((x0 + 140, y + 28), el.get("handle", "@ob_health.fit"), font=font(36, "Bold"), fill=GREY + (255,), anchor="lm")
        done = tc >= click; press = click <= tc < click + 0.1
        bx0, bx1 = x0 + bw - 250, x0 + bw - 24; k = 0.92 if press else 1.0; cxm, cym = (bx0 + bx1) / 2, y
        hw, hh = (bx1 - bx0) / 2 * k, 46 * k
        d.rounded_rectangle([cxm - hw, cym - hh, cxm + hw, cym + hh], 22, fill=((60, 60, 64) if done else YEL) + (255,))
        d.text((cxm, cym), "FOLLOWING" if done else "FOLLOW", font=font(44, "Black"), fill=(WHITE if done else (20, 20, 20)) + (255,), anchor="mm")
        lay.putalpha(lay.split()[3].point(lambda v: int(v * a))); img.alpha_composite(lay)
        cu = ease(tc - 0.25, 0.45)
        if tc < click + 0.5: _cursor(img, cxm + 120 * (1 - cu) + 10, cym + 150 * (1 - cu) + 6, 1.2, press)
        return
    type_dur = el.get("type_dur", 0.4); kw = el["keyword"].upper(); click = type_dur + 0.35; note = click + 0.15
    bw, bh = 760, 108; x0 = W / 2 - bw / 2 + 60
    if tc < note:   # the box: avatar + pill + send button, keyword typing on
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        lay.alpha_composite(av, (int(x0 - 120), int(y - 48)))
        d.rounded_rectangle([x0, y - bh / 2, x0 + bw, y + bh / 2], bh / 2, fill=(22, 22, 24, 235), outline=(255, 255, 255, 46), width=2)
        s = kw[:int(len(kw) * min(1.0, tc / type_dur))]
        d.text((x0 + 44, y), s if s else ("Add a comment..." if mode == "comment" else "Message..."), font=font(58, "ExtraBold"),
               fill=(WHITE if s else GREY) + (255,), anchor="lm")
        press = click <= tc < click + 0.1; r = 38 * (0.86 if press else 1.0); sx = x0 + bw - 58
        d.ellipse([sx - r, y - r, sx + r, y + r], fill=YEL + (255,))
        d.line([sx, y + r * 0.5, sx, y - r * 0.45], fill=(20, 20, 20, 255), width=8)
        d.polygon([(sx, y - r * 0.62), (sx - r * 0.42, y - r * 0.12), (sx + r * 0.42, y - r * 0.12)], fill=(20, 20, 20, 255))
        a = min(1.0, tc / 0.1) * (1.0 - ease(tc - click - 0.05, 0.1))
        lay.putalpha(lay.split()[3].point(lambda v: int(v * a))); img.alpha_composite(lay)
        cu = ease(tc - type_dur * 0.5, click - type_dur * 0.5)
        _cursor(img, sx + 6 + 120 * (1 - cu), y + 10 + 130 * (1 - cu), 1.2, press)
        return
    tn = tc - note; u = ease(tn, 0.25); nw, nh = 800, 132; nx = W / 2 - nw / 2; ny = y - nh / 2 - 40 * (1 - u)   # the reply drops in
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([nx, ny, nx + nw, ny + nh], 30, fill=(30, 28, 26, 240), outline=YEL + (150,), width=3)
    lay.alpha_composite(_avatar(el.get("avatar"), 84), (int(nx + 24), int(ny + 24)))
    d.text((nx + 130, ny + 44), el.get("name", "OB"), font=font(46, "Black"), fill=WHITE + (255,), anchor="lm")
    d.text((nx + 130, ny + 94), el.get("reply", "here you go").upper() if el.get("upper") else el.get("reply", "Here you go"), font=font(42, "Bold"), fill=(220, 220, 220, 255), anchor="lm")
    d.text((nx + nw - 30, ny + 44), "now", font=font(34, "Bold"), fill=GREY + (255,), anchor="rm")
    lay.putalpha(lay.split()[3].point(lambda v: int(v * min(1.0, tn / 0.12)))); img.alpha_composite(lay)


def draw_scan(img, el, t, ctx):
    """'This scans your entire codebase' (Nate, 27 s): a glowing line sweeps down the screen and lights what it passes. OB: down
    a label, a plate, an app screen as he says 'scan' / 'check'. "box" [x0, y0, x1, y1] (default the top panel), "dur" 0.9, "passes" 1."""
    t0 = trigger(el, ctx["words"]); ts = t - t0; dur = el.get("dur", 0.9); n = el.get("passes", 1)
    if ts < 0 or ts > dur * n + 0.15: return
    x0, y0, x1, y1 = el.get("box", (0, 0, W, 876)); u = ease(min(ts, dur * n) % dur if ts < dur * n else dur, dur) if ts < dur * n else 1.0
    a = 1.0 if ts <= dur * n else max(0.0, 1 - (ts - dur * n) / 0.15); yy = y0 + (y1 - y0) * u
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); col = COLORS.get(el.get("color", "yellow"), YEL)
    for k in range(70):   # the lit band trailing above the line
        d.line([x0, yy - k, x1, yy - k], fill=col + (int(70 * (1 - k / 70) ** 2 * a),))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    g.line([x0, yy, x1, yy], fill=col + (int(255 * a),), width=16); g.ellipse([W / 2 - 220, yy - 10, W / 2 + 220, yy + 10], fill=WHITE + (int(200 * a),))
    lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10))); d.line([x0, yy, x1, yy], fill=(255, 250, 220, int(255 * a)), width=4)
    img.alpha_composite(lay)


def draw_tint(img, el, t, ctx):
    """A colour wash over the panel on the bad thing (Nate, 6.5 s: the whole screen goes red on 'hit your usage limit').
    "color" red, "alpha" 0.38, "box" (default the top panel), "on", "off" (a word) or "until"; 0.12 s in, 0.2 s out."""
    words = ctx["words"]; t0 = trigger(el, words); te = word_end(el["off"], words, after=t0) if el.get("off") else el.get("until", t0 + el.get("dur", 1.0))
    if t < t0 or te is None or t > te + 0.2: return
    a = el.get("alpha", 0.38) * min(1.0, (t - t0) / 0.12) * (1.0 if t <= te else 1 - (t - te) / 0.2)
    x0, y0, x1, y1 = el.get("box", (0, 0, W, 876)); col = COLORS.get(el.get("color", "red"), RED)
    reg = img.crop((x0, y0, x1, y1)); arr = np.asarray(reg, np.float32); c = np.array(col, np.float32)
    arr[..., :3] = arr[..., :3] * (1 - a) + (arr[..., :3] * 0.55 + c * 0.45) * a   # a multiply-ish wash: the picture still reads
    img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (x0, y0))


def draw_check(img, el, t, ctx):
    """The 'done' tile (Nate 13.5 s, 24.5 s; Dem0B 31.5 s): a square pops on the corner of a screen and a tick draws inside it.
    OB: #FFD400 square, dark tick. "x", "y" (centre), "size" 120, "on", "until"."""
    t0 = trigger(el, ctx["words"]); tc = t - t0
    if tc < 0 or (el.get("until") is not None and t > el["until"]): return
    s = el.get("size", 120) * (0.4 + 0.6 * spring(tc, freq=4.0)); x, y = el.get("x", W / 2), el.get("y", 300)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x - s / 2 + 4, y - s / 2 + 8, x + s / 2 + 4, y + s / 2 + 8], s * 0.16, fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8))); d = ImageDraw.Draw(img)
    d.rounded_rectangle([x - s / 2, y - s / 2, x + s / 2, y + s / 2], s * 0.16, fill=YEL + (255,))
    u = ease(tc - 0.1, 0.16)
    if u > 0:
        p0, p1, p2 = (x - s * 0.26, y + s * 0.02), (x - s * 0.06, y + s * 0.22), (x + s * 0.28, y - s * 0.2)
        if u <= 0.4: d.line([p0, (p0[0] + (p1[0] - p0[0]) * u / 0.4, p0[1] + (p1[1] - p0[1]) * u / 0.4)], fill=(20, 20, 20, 255), width=int(s * 0.11))
        else:
            v = (u - 0.4) / 0.6; d.line([p0, p1, (p1[0] + (p2[0] - p1[0]) * v, p1[1] + (p2[1] - p1[1]) * v)], fill=(20, 20, 20, 255), width=int(s * 0.11), joint="curve")


# ---------- T22: Hormozi whiteboard framework (study 11-06: T7 OB-EDITS/2026-11-06-hormozi-study/, reel DfaGTlsoI7m) ----------
# Measured at 1080x1920 on his 5-part VSL framework reel: red title pill #FC0000 over the hook (0-2.3 s, y 928-1216), the whole
# framework on one board whipping in behind it (0.9-2.4 s), paper cards rising over his chest (cx 51%, top 52-63%, 36-46% wide), a
# yellow highlighter #FDFD6C on each item as he says it, '#n' step labels on white strips (694 x 149, y 1132-1281), comic bubbles for
# example lines (607 x 133, y 1074-1207), a name card mid-video (bar y ~1380-1545), a comment bar on the CTA tag (text y 1409-1475).
# Captions: 1-3 words, white mixed case, y ~1040, hidden while a card holds that band. Fonts are OFL: Patrick Hand (SC) for the
# marker writing, Inter for the pill, labels and captions (OB can switch the pill and captions to Big Shoulders: "font": "brand").
HAND_DIR = os.path.expanduser("~/ob-editor/fonts/PatrickHand")   # Patrick Hand + Patrick Hand SC, SIL OFL (OFL.txt beside them)
INTER_DIR = os.path.expanduser("~/ob-editor/fonts/Inter")        # Inter variable + italic, SIL OFL (OFL.txt beside it)
PILL_RED, HL_YEL, PAPER, INK, CIRCLE_GREEN = (252, 0, 0), (253, 253, 108), (253, 253, 253), (32, 25, 22), (70, 175, 95)
_HF = {}


def hand_font(size, caps=True):
    k = ("h", int(size), caps)
    if k not in _HF: _HF[k] = ImageFont.truetype(os.path.join(HAND_DIR, "PatrickHandSC-Regular.ttf" if caps else "PatrickHand-Regular.ttf"), int(size))
    return _HF[k]


def inter(size, weight="SemiBold", italic=False):
    k = ("i", int(size), weight, italic)
    if k not in _HF:
        f = ImageFont.truetype(os.path.join(INTER_DIR, "Inter-Italic-VF.ttf" if italic else "Inter-VF.ttf"), int(size))
        name = (("Italic" if weight == "Regular" else weight + " Italic") if italic else weight)
        try: f.set_variation_by_name(name)
        except Exception: pass
        _HF[k] = f
    return _HF[k]


def _block(ctx, top, hide=False):
    """Elements that hold the caption band tell the captions where their top is this frame. Measured on his reel: no caption over
    the pill, the board, a '#n' label or a bubble (hide=True); over a paper card the caption stays only if it fits above the card
    within a short shift, else it hides (his tall intro card: none; his shorter cards: the phrase sits just above them)."""
    c = ctx["cache"]; c["_block"] = top if c.get("_block") is None else min(c["_block"], top)
    if hide: c["_cap_hide"] = True


def _until(el, words, t0):
    """An element's end: "until" s, "until_on" a later word's start, "off" a word's end + "hold" (0.25 s), "dur" s; None = stays."""
    if el.get("until") is not None: return float(el["until"])
    if el.get("until_on"): return trigger({"on": el["until_on"], "after": t0 + 0.3, "lead": el.get("exit_lead", 0.0)}, words, default=1e9)
    if el.get("off"):
        e = word_end(el["off"], words, after=t0); return (e + el.get("hold", 0.25)) if e is not None else None
    if el.get("dur"): return t0 + float(el["dur"])
    return None


def _start(el, words):
    return trigger(el, words, default=0.0) if (el.get("on") or el.get("at") is not None) else 0.0


def _drop_shadow(lay, blur=16, alpha=0.38, dy=10):
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(lay.split()[3].point(lambda v: int(v * alpha)))
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (0, dy)); out.alpha_composite(lay)
    return out


def draw_pill(img, el, t, ctx):
    """The title pill: the video's promise in 1-2 lines of white heavy italic caps, each line on its own red (#FC0000) rounded bar,
    the bars stacked into one stepped shape, centred at y 1072 (56%), at most 81% of the frame wide. On from frame 0 over the spoken
    hook; it leaves on the cut to the first card (he holds it 2.3 s). "lines", "y", "size" (96), "accent" [words] in #FFD400,
    "font": "inter" (his look, Inter Black Italic) | "brand" (Big Shoulders Black, slanted 12 degrees), "box": false (no red bar: the
    title straight on the picture with the brand shadow, OB's no-box rule), "at"/"on", "until"/"dur" (bulk pass 11-07: ~4.0 s by default)."""
    words = ctx["words"]; t0 = _start(el, words); el = dict(el); el.setdefault("dur", 4.0) if not any(k in el for k in ("until", "until_on", "off")) else None; te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    lines = [s.upper() for s in el["lines"]]; size = el.get("size", 96); y = el.get("y", 1072); brand = el.get("font", "inter") == "brand"
    mk = (lambda s: font(int(s * 1.3), "Black")) if brand else ((lambda s: poppins(s, "BlackItalic")) if el.get("font") == "poppins" else (lambda s: inter(s, "Black", italic=True)))
    f = mk(size)
    while max(f.getlength(s) for s in lines) > W * 0.70 and size > 48: size -= 4; f = mk(size)
    k = ("pill", tuple(lines), size, y, brand, tuple(el.get("accent", [])), el.get("box", True), el.get("font"))
    if k not in _IMG:
        lh = size * 1.08; padx, pady = size * 0.40, size * 0.20; r = size * 0.30; n = len(lines); top = y - (n * lh + 2 * pady) / 2
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for i, s in enumerate(lines):
            if el.get("box") is False: break   # OB's no-box version: the title straight on the picture, brand shadow, yellow accent word
            tw = f.getlength(s); x0 = W / 2 - tw / 2 - padx; yy = top + pady + i * lh
            d.rounded_rectangle([x0, yy - (pady if i == 0 else 0), x0 + tw + 2 * padx, yy + lh + (pady if i == n - 1 else 2)], r, fill=PILL_RED + (255,))
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dt = ImageDraw.Draw(txt); acc = {a.upper() for a in el.get("accent", [])}
        for i, s in enumerate(lines):
            x = W / 2 - f.getlength(s) / 2; yy = top + pady + i * lh + lh / 2
            for wd in s.split(" "):
                dt.text((x, yy), wd, font=f, fill=(YEL if wd.strip(",.!?") in acc else WHITE) + (255,), anchor="lm"); x += f.getlength(wd + " ")
        if brand: txt = txt.transform(txt.size, Image.AFFINE, (1, 0.21, -0.21 * y, 0, 1, 0), Image.BICUBIC)   # a 12 degree slant
        if el.get("box") is False:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(txt.split()[3].point(lambda v: int(v * BRAND["shadow"]["alpha"])))
            lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(W * BRAND["shadow"]["blur_of_width"] / 2)), (0, int(W * BRAND["shadow"]["y_of_width"])))
        lay.alpha_composite(txt); _IMG[k] = (lay, top - pady)
    lay, top = _IMG[k]
    if el.get("pop"):   # optional: his is a hard cut-in; "pop" springs it from 92%
        p = spring(t - t0, freq=3.4); bb = lay.getbbox(); crop = lay.crop(bb); s = 0.92 + 0.08 * p
        lay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cw, ch = int(crop.width * s), int(crop.height * s)
        lay2.alpha_composite(crop.resize((cw, ch), Image.LANCZOS), (int(W / 2 - cw / 2), int((bb[1] + bb[3]) / 2 - ch / 2))); lay = lay2
    img.alpha_composite(lay); _block(ctx, top, hide=True)


def _sheet(w, h, radius=6):
    lay = Image.new("RGBA", (int(w) + 60, int(h) + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([30, 30, 30 + w, 30 + h], radius, fill=PAPER + (255,), outline=(212, 210, 206, 255), width=2)
    return lay


def _hl_bar(d, x0, yc, x1, size, ox, oy):
    """A highlighter stroke behind one line: a slightly uneven bar, a little taller than the lower-case letters."""
    a, b = yc - size * 0.40, yc + size * 0.38
    d.polygon([(ox + x0 - 8, oy + a + 3), (ox + x1 + 10, oy + a), (ox + x1 + 12, oy + b - 2), (ox + x0 - 10, oy + b)], fill=HL_YEL + (255,))


def draw_paper(img, el, t, ctx):
    """The paper card: a white sheet (#FDFDFD, soft shadow) with a marker heading (underlined) and a list in hand-lettered small caps
    (Patrick Hand SC thickened with a 2 px stroke to read as marker, ink #201916). It rises in from the bottom over 0.3 s just after the word that names it (he lands it ~0.4 s after
    'intro') and sits centred (cx 51%) over his chest and the table, top 52-63% of the frame, 36-46% wide, never above his chin. Each
    item gets a yellow (#FDFD6C) highlighter bar the moment he says it, in the order he says them, not the card's order. Hard exit
    on the cut or the next card. "title", "items" [text], "hl" [[item index, word], ...], "w" (430), "top" (1000), "cx" (552),
    "h" (minimum height: a heading-only card like CTA or PROOF is ~470), "size" (62), "on"/"at", "lead" (-0.3 = after the word),
    "until"/"until_on"/"off"/"dur"."""
    # bulk pass 11-07 (32 reels): the card fades in over 0.4-0.7 s rising 100-300 px, starting 0.15-0.4 s BEFORE its word, and leaves
    # by sinking and fading over 0.5-0.6 s; the highlighter (#FDFD6C) pops in one frame 0.08-0.18 s after the word
    words = ctx["words"]; el2 = dict(el); el2.setdefault("lead", 0.3); t0 = _start(el2, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    items = el.get("items", []); size = el.get("size", 62); ts = int(size * 1.18); w = el.get("w", 430); pad = 34
    pitch = size * 1.32; th = ts * 1.5 if el.get("title") else 0
    h = max(el.get("h", 0), pad + th + len(items) * pitch + pad * 0.8)
    top = el.get("top", 1000); cx = el.get("cx", 552)
    k = ("paper", el.get("title"), tuple(items), size, w, h)
    if k not in _IMG:
        lay = _sheet(w, h); d = ImageDraw.Draw(lay); ox, oy = 30, 30
        if el.get("title"):
            ft = hand_font(ts); tw = ft.getlength(el["title"])
            d.text((ox + w / 2, oy + pad + ts * 0.55), el["title"], font=ft, fill=INK + (255,), anchor="mm", stroke_width=2, stroke_fill=INK + (255,))
            uy = oy + pad + ts * 1.12; d.line([ox + w / 2 - tw / 2 - 8, uy, ox + w / 2 + tw / 2 + 8, uy + 2], fill=INK + (255,), width=6)
        _IMG[k] = lay
    base = _IMG[k].copy(); d = ImageDraw.Draw(base); ox, oy = 30, 30; fi = hand_font(size)
    lit = set()
    for idx, wd in el.get("hl", []):
        tw0 = trigger({"on": wd, "after": t0 - 0.5, "lead": el.get("hl_lead", -0.12)}, words, default=1e9)
        if t >= tw0: lit.add(int(idx))
    for i, s in enumerate(items):
        yc = oy + pad + th + pitch * (i + 0.5); x = ox + pad - 4
        if i in lit: _hl_bar(d, x, yc, x + fi.getlength(s), size, 0, 0)
        d.text((x, yc), s, font=fi, fill=INK + (255,), anchor="lm", stroke_width=2, stroke_fill=INK + (255,))
    card = _drop_shadow(base)
    ti = t - t0; u = ease_out(ti, el.get("rise", 0.55)); off = (1 - u) * el.get("rise_px", 200); a = u
    if te is not None and el.get("exit", "sink") == "sink":
        v = min(1.0, max(0.0, (t - (te - 0.55)) / 0.55)); off += v * 200; a *= (1 - v)
    if a < 1: card.putalpha(card.split()[3].point(lambda v: int(v * a)))
    img.alpha_composite(card, (int(cx - w / 2 - 30), int(top - 30 + off))); _block(ctx, top)


def draw_label(img, el, t, ctx):
    """The step label: '#n' in big white bold (Inter ExtraBold ~118, brand shadow) where the caption sits (y ~1040; the caption steps
    aside) over a white strip 64% wide x 150 px (centre y 1206) with the step in marker caps (Patrick Hand SC). Each step swaps in
    hard ON its word and holds until the next; the last holds "hold" s (0.9) after its word ends. "steps" [[n, text, word], ...],
    "y" (strip centre 1206), "w" (694), "after" (s), "until"."""
    words = ctx["words"]; steps = el["steps"]; prev = el.get("after", -1.0); starts = []
    for n, txt, wd in steps:
        s0 = trigger({"on": wd, "after": prev, "lead": el.get("lead", 0.05)}, words, default=1e9); starts.append(s0)
        if s0 < 1e8: prev = s0 + 0.05
    cur = None
    for i, s0 in enumerate(starts):
        if t >= s0: cur = i
    if cur is None: return
    end = el.get("until")
    if end is None:
        e = word_end(steps[-1][2], words, after=starts[-1] - 0.1) if starts[-1] < 1e8 else None
        end = (e + el.get("hold", 0.9)) if e is not None else 1e9
    if cur == len(steps) - 1 and t >= end: return
    n, txt, _ = steps[cur]; y = el.get("y", 1206); w = el.get("w", 694); sh = 150
    k = ("label", txt, w)
    if k not in _IMG:
        lay = _sheet(w, sh, radius=4); d = ImageDraw.Draw(lay); f = hand_font(66)
        while f.getlength(txt) > w - 60 and f.size > 36: f = hand_font(f.size - 4)
        d.text((30 + w / 2, 30 + sh / 2 + 2), txt, font=f, fill=INK + (255,), anchor="mm", stroke_width=2, stroke_fill=INK + (255,)); _IMG[k] = _drop_shadow(lay, 12, 0.32, 8)
    a = min(1.0, (t - starts[cur]) / 0.07)
    strip = _IMG[k]
    if a < 1: strip = strip.copy(); strip.putalpha(strip.split()[3].point(lambda v: int(v * a)))
    img.alpha_composite(strip, (int(W / 2 - w / 2 - 30), int(y - sh / 2 - 30)))
    ny = y - sh / 2 - 92
    shadow_text(img, (W / 2, ny), f"#{n}", inter(118, "ExtraBold"), WHITE, anchor="mm", alpha=int(255 * a))
    _block(ctx, ny - 70, hide=True)


def draw_quote(img, el, t, ctx):
    """The example-line bubble: the line a person would say ('how many square footage is your kitchen?'), in a white comic bubble with
    a thin black outline and a short tail, hand-lettered mixed case (Patrick Hand), about 56% wide x 133 px, centre y 1140 (59%),
    nudged right (cx 59%); on from its first word to its last word's end + 0.2 s, swapped hard by the next one. "text", "on", "off"
    (its last word), "cx" (640), "y" (1140), "size" (44). OB's rule of 10-28 (no rounded bubble cards in his own videos) is one
    switch away: "as": "caption" sets it as an italic line in quotes where the caption sits, no bubble."""
    words = ctx["words"]; el2 = dict(el); el2.setdefault("lead", 0.05); t0 = _start(el2, words)
    el3 = dict(el); el3.setdefault("hold", 0.2); te = _until(el3, words, t0)
    if t < t0 or (te is not None and t >= te): return
    if el.get("as") == "caption":
        f = inter(el.get("cap_size", 74), "SemiBold", italic=True); s = "“" + el["text"] + "”"
        while f.getlength(s) > W - 140 and f.size > 40: f = inter(f.size - 4, "SemiBold", italic=True)
        shadow_text(img, (W / 2, el.get("cap_y", 1040)), s, f, WHITE, anchor="mm"); _block(ctx, el.get("cap_y", 1040) - 60, hide=True); return
    size = el.get("size", 52); f = hand_font(size, caps=False); s = el["text"]
    k = ("quote", s, size)
    if k not in _IMG:
        tw = f.getlength(s); bw, bh = max(tw + 90, W * 0.5), size * 2.5
        lay = Image.new("RGBA", (int(bw) + 80, int(bh) + 90), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); ox, oy = 30, 30
        d.rounded_rectangle([ox, oy, ox + bw, oy + bh], int(bh * 0.42), fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=4)
        tx = ox + bw * 0.72   # the tail, down and to the right like his
        d.polygon([(tx - 18, oy + bh - 3), (tx + 14, oy + bh - 3), (tx + 34, oy + bh + 30)], fill=(255, 255, 255, 255))
        d.line([(tx - 18, oy + bh - 1), (tx + 34, oy + bh + 30), (tx + 14, oy + bh - 1)], fill=(20, 20, 20, 255), width=4, joint="curve")
        d.text((ox + bw / 2, oy + bh / 2 + 2), s, font=f, fill=(15, 15, 15, 255), anchor="mm"); _IMG[k] = (_drop_shadow(lay, 10, 0.25, 6), bw, bh)
    lay, bw, bh = _IMG[k]; p = spring(t - t0, freq=4.0); s_ = 0.9 + 0.1 * p; cx, y = el.get("cx", 640), el.get("y", 1140)
    if s_ < 0.999: lay = lay.resize((max(1, int(lay.width * s_)), max(1, int(lay.height * s_))), Image.LANCZOS)
    img.alpha_composite(lay, (int(cx - lay.width / 2), int(y - lay.height / 2 + 15))); _block(ctx, y - bh / 2, hide=True)


def draw_board(img, el, t, ctx):
    """The whole-framework board: every part on one white sheet (the title underlined, one column per part in a ruled table, the
    items under each heading, the part he goes deepest on circled in green) whips in from the right in ~0.18 s, holds, and whips out
    to the left, behind the title pill (list it before the pill). Sheet x 20-1060, top ~590. "title", "cols" [[heading, item, ...]],
    "circle" (column index), "top" (590), "on"/"at", "until"/"dur"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te + 0.16): return
    cols = el["cols"]; w = 1040; top = el.get("top", 590)
    if top == "auto":   # OB: never over his face, so the board sits just under his chin (his own board covers his face for 1.5 s)
        top = int(ctx["face"][3] + 30) if ctx.get("face") else 590
    k = ("board", el.get("title"), json.dumps(cols), el.get("circle"))
    if k not in _IMG:
        ft, fh, fi = hand_font(70), hand_font(40), hand_font(33); pad = 22; th = 120 if el.get("title") else 20
        rows = max(len(c) - 1 for c in cols); hh = 78; ih = 50; h = th + hh + rows * ih + pad * 2
        lay = _sheet(w, h, radius=4); d = ImageDraw.Draw(lay); ox, oy = 30, 30
        if el.get("title"):
            tw = ft.getlength(el["title"]); d.text((ox + w / 2, oy + 62), el["title"], font=ft, fill=INK + (255,), anchor="mm", stroke_width=2, stroke_fill=INK + (255,))
            d.line([ox + w / 2 - tw / 2 - 10, oy + 104, ox + w / 2 + tw / 2 + 10, oy + 106], fill=INK + (255,), width=6)
        x0, y0, x1, y1 = ox + pad, oy + th, ox + w - pad, oy + h - pad; cw = (x1 - x0) / len(cols)
        d.rectangle([x0, y0, x1, y1], outline=INK + (255,), width=3)
        for i, c in enumerate(cols):
            cx0 = x0 + i * cw
            if i: d.line([cx0, y0, cx0, y1], fill=INK + (255,), width=3)
            f = fh
            while f.getlength(c[0]) > cw - 24 and f.size > 22: f = hand_font(f.size - 2)
            hw = f.getlength(c[0]); d.text((cx0 + cw / 2, y0 + 38), c[0], font=f, fill=INK + (255,), anchor="mm", stroke_width=1, stroke_fill=INK + (255,))
            d.line([cx0 + cw / 2 - hw / 2 - 4, y0 + 62, cx0 + cw / 2 + hw / 2 + 4, y0 + 63], fill=INK + (255,), width=3)
            if el.get("circle") == i:
                d.ellipse([cx0 + cw / 2 - hw / 2 - 22, y0 + 10, cx0 + cw / 2 + hw / 2 + 22, y0 + 68], outline=CIRCLE_GREEN + (255,), width=5)
            for j, s in enumerate(c[1:]):
                g = fi
                while g.getlength(s) > cw - 20 and g.size > 18: g = hand_font(g.size - 2)
                d.text((cx0 + 12, y0 + hh + ih * (j + 0.5)), s, font=g, fill=INK + (255,), anchor="lm", stroke_width=1, stroke_fill=INK + (255,))
        _IMG[k] = _drop_shadow(lay, 18, 0.30, 10)
    lay = _IMG[k]; ti = t - t0; off = (1 - ease_out(ti, 0.18)) * W
    if te is not None and t > te: off = -ease(t - te, 0.16) * W
    img.alpha_composite(lay, (int(20 - 30 + off), int(top - 30))); _block(ctx, top, hide=True)


def _bar(img, box, a, mode=None):
    """The dark bar under the name card and the comment bar. His: near-black #0C090C at 85% ("bar": "dark", the default, faithful).
    OB's M38 (no near-black behind cards): "bar": "frosted" = the picture under it blurred and darkened to about half, so his studio
    still shows through."""
    x0, y0, x1, y1 = [int(v) for v in box]
    if mode == "frosted":
        reg = img.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(26)); arr = np.asarray(reg, np.float32)
        arr[..., :3] *= 0.52; reg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        m = Image.new("L", reg.size, int(255 * a)); img.paste(reg, (x0, y0), m); return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle([x0, y0, x1, y1], fill=(12, 9, 12, int(217 * a)))
    img.alpha_composite(lay)


def draw_lower3(img, el, t, ctx):
    """The name card, mid-video at the re-hook (he shows it ~10.5-14.5 s, not at the start): a near-black bar (#0C090C at 85%)
    from x 150 to ~880, y 1380-1545, the name in white heavy caps (~88 px tall caps at y 1405-1469) and a grey (#ABA6A7) line under
    it. Slides in from the left over 0.25 s, fades out over 0.2 s. "name", "sub", "on"/"at", "dur" (4.0) / "until", "y" (1320 for OB),
    "font": "inter" | "brand" (Big Shoulders Black for the name)."""
    words = ctx["words"]; t0 = _start(el, words); el2 = dict(el); el2.setdefault("dur", 4.0); te = _until(el2, words, t0)
    if t < t0 or t >= te + 0.2: return
    y = el.get("y", 1320); name = el["name"].upper(); sub = el.get("sub", "")   # his bar sits at 1380-1545; OB's stays above the IG band (1500)
    fn = font(118, "Black") if el.get("font") == "brand" else inter(86, "ExtraBold"); fs = inter(38, "Medium")
    bw = max(fn.getlength(name), fs.getlength(sub)) + 90; bh = 165
    u = ease_out(t - t0, 0.25); a = min(1.0, (t - t0) / 0.12) * (1.0 - (ease(t - te, 0.2) if t > te else 0.0))
    x0 = 150 - (1 - u) * 120
    _bar(img, (x0, y, x0 + bw, y + bh), a, el.get("bar"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((x0 + 45, y + 62), name, font=fn, fill=WHITE + (int(255 * a),), anchor="lm")
    if sub: d.text((x0 + 47, y + 126), sub, font=fs, fill=(171, 166, 167, int(255 * a)), anchor="lm")
    img.alpha_composite(lay)


def draw_ctabar(img, el, t, ctx):
    """The comment bar on the CTA tag: 'COMMENT "SALES"' in white caps (~88 px, text y 1409-1475) on a near-black bar across the
    frame (x 90-990, y 1380-1500), from the tag's first frame to the end. He films the tag separately (another shirt) and the bar runs
    under all of it. "keyword", "text" (default 'COMMENT "KEYWORD"'), "on"/"at", "until", "y" (1420), "font": "inter" | "brand"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    s = el.get("text") or f'COMMENT “{el["keyword"].upper()}”'; y = el.get("y", 1420)   # his text y 1409-1475; kept above the IG band
    if el.get("style") == "pill":   # DfXZ: 'COMMENT "SALES"' black bold italic in a white rounded box (OB's no-box rule: his call)
        s2 = el.get("text") or f'COMMENT “{el["keyword"].upper()}”'; f2 = poppins(el.get("size", 64), "ExtraBoldItalic"); tw2 = f2.getlength(s2); y2 = el.get("y", 1440)
        a2 = int(255 * min(1.0, (t - t0) / 0.1)); lay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d2 = ImageDraw.Draw(lay2)
        d2.rounded_rectangle([W / 2 - tw2 / 2 - 34, y2 - 52, W / 2 + tw2 / 2 + 34, y2 + 52], 18, fill=(255, 255, 255, a2))
        d2.text((W / 2, y2 + 2), s2, font=f2, fill=(10, 10, 10, a2), anchor="mm"); img.alpha_composite(_drop_shadow(lay2, 10, 0.3, 6)); return
    if el.get("style") == "text":   # T23: 'Comment "SALES"' in white bold italic straight on the picture, no bar (his y ~1528; OB's 1470)
        s2 = el.get("text") or f'Comment “{el["keyword"].upper()}”'; f2 = poppins(el.get("size", 78), "ExtraBoldItalic")
        shadow_text(img, (W / 2, el.get("y", 1470)), s2, f2, WHITE, anchor="mm", alpha=int(255 * min(1.0, (t - t0) / 0.1))); return
    f = font(112, "Black") if el.get("font") == "brand" else inter(84, "SemiBold")
    while f.getlength(s) > W - 220 and f.size > 40: f = (font(f.size - 4, "Black") if el.get("font") == "brand" else inter(f.size - 4, "SemiBold"))
    tw = f.getlength(s); a = min(1.0, (t - t0) / 0.1)
    _bar(img, (W / 2 - tw / 2 - 30, y - 60, W / 2 + tw / 2 + 30, y + 60), a, el.get("bar"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((W / 2, y), s, font=f, fill=WHITE + (int(255 * a),), anchor="mm"); img.alpha_composite(lay)


def _marks(words, cfg):
    """Per-word style for his captions: italic for lines he voices as someone else (cfg "italic" phrases), quote marks around named
    terms (cfg "quote" phrases: 'old way', 'them vs us', 'hidden problem')."""
    out = [dict(it=False, q0=False, q1=False, b=False) for _ in words]; norm = [_sn(w["w"]) for w in words]
    for key in ("italic", "quote", "bold"):
        for ph in cfg.get(key, []):
            p = [_sn(x) for x in ph.split()]
            for i in range(len(words) - len(p) + 1):
                if norm[i:i + len(p)] == p:
                    for j in range(i, i + len(p)):
                        if key == "italic": out[j]["it"] = True
                        if key == "bold": out[j]["b"] = True
                    if key == "quote": out[i]["q0"] = True; out[i + len(p) - 1]["q1"] = True
    return out


def clean_captions(img, t, words, cfg, face=None, seg_end=None, block=None, hide=False):
    """His captions: 1-3 words in white mixed case (Inter SemiBold 76 px: 'that someone has' measured ~705 px wide), a soft dark
    shadow, centred at y 1040 (54%, his chest), the whole phrase at once, swapped every phrase (split at punctuation or a 0.25 s pause),
    0.05 s early. Lines he voices as someone else ('now that sounds amazing', 'but people ask') go italic (cfg "italic"); named terms get
    quote marks (cfg "quote"). While a card, label, bubble or the pill holds the band (block = its top this frame) the caption moves up
    to sit over it if it stays under his chin, else it hides (he shows no caption over his cards). "font": "brand" = OB's locked style."""
    if not words or hide: return
    seg_end = seg_end if seg_end is not None else words[-1]["e"] + 0.45
    c2 = dict(cfg); c2.update(lower=False, emph=[], max_words=c2.get("n", 3), pause=c2.get("pause", 0.25), lead=c2.get("lead", 0.05))
    blocks = serif_blocks(words, c2, seg_end); j = next((i for i, b in enumerate(blocks) if b["t0"] <= t < b["t1"]), None)
    if j is None: return
    b = blocks[j]
    if t > b["ws"][-1]["e"] + 0.45: return
    size = cfg.get("size", 76); y = cfg.get("y", 1040)
    if face and face[1] - 40 < y < face[3] + 40: y = face[3] + 40 + size / 2
    if block is not None and block < y + size * 0.6:
        y2 = block - 40 - size / 2
        if y - y2 > cfg.get("max_shift", 90): return          # no room above the card: he shows no caption
        if face and y2 - size / 2 < face[3] + 15: return
        y = y2
    mk = _marks(words, cfg); idx = {id(w): i for i, w in enumerate(words)}
    parts = []
    for w in b["ws"]:
        m = mk[idx[id(w)]]; s = w["w"].strip()
        if cfg.get("strip_punct", True): s = s.rstrip(",.;:")
        pre = (cfg.get("prefix") or {}).get(_sn(w["w"]))
        if pre: s = pre + " " + s
        if m["q0"]: s = "“" + s
        if m["q1"]: s = s + "”"
        parts.append((s, (m["it"], m["b"] or bool(cfg.get("bold_numbers") and any(c.isdigit() for c in s)))))   # DfXZ: "to **7**", "**72 hours**"
    pop = cfg.get("font") == "poppins"   # T23: Poppins SemiBold, bold accent words in ExtraBold ("bold" phrases)
    def fnt(sz, st):
        it, b = st
        if pop: return poppins(sz, "ExtraBold" if b else ("MediumItalic" if it else "SemiBold"))
        return inter(sz, "ExtraBold" if b else "SemiBold", italic=it)
    fs = [fnt(size, st) for _, st in parts]; sp = fnt(size, (False, False)).getlength(" ")
    tw = sum(f.getlength(s) for (s, _), f in zip(parts, fs)) + sp * (len(parts) - 1)
    while tw > W - 120 and size > 40:
        size -= 4; fs = [fnt(size, st) for _, st in parts]; sp = fnt(size, (False, False)).getlength(" ")
        tw = sum(f.getlength(s) for (s, _), f in zip(parts, fs)) + sp * (len(parts) - 1)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x = W / 2 - tw / 2
    for (s, _), f in zip(parts, fs): d.text((x, y), s, font=f, fill=(255, 255, 255, 255), anchor="lm"); x += f.getlength(s) + sp
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh.putalpha(lay.split()[3].point(lambda v: int(v * 0.55)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)), (0, 4)); img.alpha_composite(lay)


# ---------- T23: Hormozi step tracker (DfVRSAYoFPf "5 steps to train a sales rep in 14 days", measured 11-06) ----------
# A purple (#7318FC) progress panel with numbered circles pinned at x 142-940, y 1376-1582 the whole video; a red (#F22817)
# "STEP #n" tag over a purple sub-tag on each step word (red 306 x 94 centred y 1195, sub 78 tall, ~2 s); full-screen purple
# summary cards for 1-3 s (title, numbered list with emoji, the tracker and captions stay on top); a checkbox list that ticks
# item by item; captions 2-4 words, white Poppins with bold accent words, y ~1250, just above the tracker. Fonts: Poppins and
# Noto Color Emoji (both OFL).
POPPINS_DIR = os.path.expanduser("~/ob-editor/fonts/Poppins")
EMOJI_FONT = os.path.expanduser("~/ob-editor/fonts/NotoEmoji/NotoColorEmoji-CBDT.ttf")   # Noto Color Emoji v2.047 (bitmap), OFL
PURPLE, STEP_RED, LAVENDER = (115, 24, 252), (242, 40, 23), (176, 140, 255)


def poppins(size, style="ExtraBold"):
    k = ("p", int(size), style)
    if k not in _HF: _HF[k] = ImageFont.truetype(os.path.join(POPPINS_DIR, f"Poppins-{style}.ttf"), int(size))
    return _HF[k]


def emoji_img(ch, size):
    k = ("emoji", ch, int(size))
    if k not in _IMG:
        f = ImageFont.truetype(EMOJI_FONT, 109); im = Image.new("RGBA", (300, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True); bb = im.getbbox()
        im = im.crop(bb) if bb else im; s = size / max(im.width, im.height)
        _IMG[k] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return _IMG[k]


def _starts(words, pairs, key=1, lead=0.05):
    out, prev = [], -1.0
    for p in pairs:
        s0 = trigger({"on": p[key], "after": prev, "lead": lead}, words, default=1e9); out.append(s0)
        if s0 < 1e8: prev = s0 + 0.05
    return out


def draw_tracker(img, el, t, ctx):
    """The step tracker: a purple rounded panel (#7318FC, x 142-940, y 1376-1582, r 34) with one numbered circle per step (56 px,
    white ring) joined by lines, the step name under each. Done and active circles fill white (purple number); the line out of the
    active step fills white over the step's duration; names of steps not reached yet are blurred (the viewer sees how many are left,
    not what). On from frame 0 to the CTA. "steps" [[label, word], ...], "box" [x0, y0, x1, y1], "theme": "purple" | "brand"
    (OB: his studio frosted under the panel, #FFD400 for done and active), "at", "until"/"until_on"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    brand = el.get("theme", "brand") == "brand"   # his panel is 1376-1582 (into the IG band); OB's sits above it
    steps = el["steps"]; n = len(steps); x0, y0, x1, y1 = el.get("box", (142, 1286, 940, 1492) if brand else (142, 1376, 940, 1582))
    starts = _starts(words, steps); k = max([i for i, s in enumerate(starts) if t >= s], default=-1)
    if brand: _bar(img, (x0, y0, x1, y1), 1.0, "frosted")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if not brand: d.rounded_rectangle([x0, y0, x1, y1], 34, fill=PURPLE + (255,))
    hot = YEL if brand else WHITE; ink = (20, 20, 20) if brand else PURPLE
    r = 28; cy = y0 + 60; xs = [x0 + 78 + i * (x1 - x0 - 156) / max(1, n - 1) for i in range(n)]
    for i in range(n - 1):
        a, b = xs[i] + r + 6, xs[i + 1] - r - 6
        d.line([a, cy, b, cy], fill=LAVENDER + (255,), width=4)
        if i < k: d.line([a, cy, b, cy], fill=hot + (255,), width=6)
        elif i == k and starts[i + 1] < 1e8:
            fr = min(1.0, max(0.0, (t - starts[i]) / max(0.3, starts[i + 1] - starts[i])))
            d.line([a, cy, a + (b - a) * fr, cy], fill=hot + (255,), width=6)
    fnum = font(40, "Black") if brand else poppins(30, "ExtraBoldItalic"); flab = font(30, "ExtraBold") if brand else poppins(22, "ExtraBold")
    blur = Image.new("RGBA", img.size, (0, 0, 0, 0)); db = ImageDraw.Draw(blur)
    for i, (lab, _) in enumerate(steps):
        on = i <= k; cx = xs[i]
        if on: d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=hot + (255,))
        else: d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=WHITE + (255,), width=4)
        d.text((cx, cy + 1), str(i + 1), font=fnum, fill=(ink if on else WHITE) + (255,), anchor="mm")
        (d if on else db).text((cx, y0 + 128), lab.upper(), font=flab, fill=WHITE + (255,), anchor="mm")
    lay.alpha_composite(blur.filter(ImageFilter.GaussianBlur(7)))
    img.alpha_composite(lay); _block(ctx, y0)


def draw_steptag(img, el, t, ctx):
    """The step tag on each step word: 'STEP #n' white bold italic caps on a red (#F22817) rounded tag (306 x 94, centre y 1195)
    over a purple sub-tag (78 tall, as wide as its text) with the step's name, popping in (spring from 85%) and holding ~2 s.
    No caption while it's up. "n", "name", "on", "dur" (2.0), "y" (1195), "theme": "brand" = yellow tag, dark text."""
    words = ctx["words"]; t0 = _start(el, words); el2 = dict(el); el2.setdefault("dur", 1.7); te = _until(el2, words, t0)   # bulk 11-07: hold median 1.7 s
    if t < t0 or t >= te: return
    brand = el.get("theme", "brand") == "brand"; y = el.get("y", 1110 if brand else 1195)
    k = ("steptag", el["n"], el.get("name", ""), y, brand, el.get("word", "STEP"))
    if k not in _IMG and brand:   # OB 11-06 "it doesn't have to be purple": his brand, no boxes: STEP #n in yellow, the name in white
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_text(lay, (W / 2, y), f"{el.get('word', 'STEP').upper()} #{el['n']}", font(118, "Black"), YEL, anchor="mm")
        if el.get("name"): shadow_text(lay, (W / 2, y + 100), el["name"].upper(), font(70, "ExtraBold"), WHITE, anchor="mm", track=3)
        _IMG[k] = lay
    if k not in _IMG:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        f1 = poppins(62, "BlackItalic"); s1 = f"{el.get('word', 'STEP').upper()} #{el['n']}"; w1 = f1.getlength(s1) + 56
        d.rounded_rectangle([W / 2 - w1 / 2, y - 47, W / 2 + w1 / 2, y + 47], 12, fill=(YEL if brand else STEP_RED) + (255,), outline=(255, 255, 255, 230), width=3)
        d.text((W / 2, y + 2), s1, font=f1, fill=((20, 20, 20) if brand else WHITE) + (255,), anchor="mm")
        if el.get("name"):
            f2 = poppins(40, "ExtraBoldItalic"); s2 = el["name"].upper(); w2 = f2.getlength(s2) + 50
            d.rounded_rectangle([W / 2 - w2 / 2, y + 49, W / 2 + w2 / 2, y + 127], 12, fill=((22, 20, 18) if brand else PURPLE) + (235,))
            d.text((W / 2, y + 88), s2, font=f2, fill=WHITE + (255,), anchor="mm")
        _IMG[k] = lay
    lay = _IMG[k]   # DfXZ: small "FIX #n" tags = scale 0.62
    p = spring(t - t0, freq=3.8) if el.get("enter") == "spring" else min(1.0, (t - t0) * FPS / 2)   # bulk 11-07: a 2-frame pop from 85%, no bounce
    s = (0.85 + 0.15 * p) * el.get("scale", 1.0)
    if abs(s - 1.0) > 0.001:
        bb = lay.getbbox(); crop = lay.crop(bb); cw, ch = int(crop.width * s), int(crop.height * s)
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); lay.alpha_composite(crop.resize((cw, ch), Image.LANCZOS), (int(W / 2 - cw / 2), int((bb[1] + bb[3]) / 2 - ch / 2)))
    img.alpha_composite(lay); _block(ctx, y - 47, hide=True)


def _card_layer(el, width=1080, brand=False):
    """The summary card's content on purple: title (Poppins ExtraBold 56), an italic subtitle, then numbered rows: a white circle
    with a purple italic number, the item in white caps (ExtraBold 38), an optional italic sub-line, an emoji at the right."""
    items = el.get("items", []); pitch = el.get("pitch", 118); top = 80; h = top + 90 + (40 if el.get("sub") else 0) + len(items) * pitch + 40
    lay = Image.new("RGBA", (width, int(h)), (0, 0, 0, 0) if brand else PURPLE + (255,)); d = ImageDraw.Draw(lay)
    ft = font(84, "Black") if brand else poppins(56, "ExtraBold")
    while ft.getlength(el["title"].upper()) > width - 120 and ft.size > 30: ft = font(ft.size - 4, "Black") if brand else poppins(ft.size - 2, "ExtraBold")
    d.text((width / 2, top), el["title"].upper(), font=ft, fill=WHITE + (255,), anchor="mm"); y = top + 70
    if el.get("sub"): d.text((width / 2, y), el["sub"], font=poppins(28, "MediumItalic"), fill=(225, 215, 255, 255), anchor="mm"); y += 50
    for i, it in enumerate(items):
        txt, sub, emo = (list(it) + ["", ""])[:3]; cy = y + pitch * i + pitch / 2
        d.ellipse([84, cy - 36, 156, cy + 36], fill=(YEL if brand else WHITE) + (255,))
        d.text((120, cy + 2), str(i + 1), font=font(50, "Black") if brand else poppins(40, "ExtraBoldItalic"), fill=((20, 20, 20) if brand else PURPLE) + (255,), anchor="mm")
        fi = font(56, "ExtraBold") if brand else poppins(38, "ExtraBold")
        while fi.getlength(txt.upper()) > width - 340 and fi.size > 22: fi = font(fi.size - 2, "ExtraBold") if brand else poppins(fi.size - 2, "ExtraBold")
        d.text((196, cy - (14 if sub else 0)), txt.upper(), font=fi, fill=WHITE + (255,), anchor="lm")
        if sub: d.text((196, cy + 26), sub, font=poppins(28, "Italic"), fill=(230, 222, 255, 255), anchor="lm")
        if emo: e = emoji_img(emo, 76); lay.alpha_composite(e, (int(width - 100 - e.width / 2), int(cy - e.height / 2)))
    return lay


def draw_takeover(img, el, t, ctx):
    """The summary card: the whole frame turns purple for 1-3 s with the step's detail as a numbered list (title, rows with emoji);
    the tracker and his captions stay on top (list the takeover BEFORE the tracker). "title", "sub", "items" [[text, sub, emoji]],
    "on"/"at", "dur"/"until"/"off", "mode": "full" (his) | "chest" (OB's M37, his face on screen every frame: the card shrinks to
    a rounded panel between his chin and the tracker, captions hidden)."""
    words = ctx["words"]; t0 = _start(el, words); el2 = dict(el); el2.setdefault("dur", 2.0); te = _until(el2, words, t0)
    if t < t0 or t >= te: return
    brand = el.get("theme", "brand") == "brand"
    k = ("takeover", el["title"], json.dumps(el.get("items", [])), el.get("sub"), brand)
    if k not in _IMG: _IMG[k] = _card_layer(el, brand=brand)
    card = _IMG[k]
    if el.get("mode", "chest" if brand else "full") == "full":   # OB (M37, face every frame): the chest card by default
        if brand:   # OB: his own frame behind it, blurred and at 45% (brand.json dm_flash background), never a flat colour
            bg = img.convert("RGB").resize((540, 960)).filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
            bg = Image.fromarray((np.asarray(bg, np.float32) * 0.45).astype(np.uint8)).convert("RGBA"); img.paste(bg, (0, 0))
        else: img.paste(PURPLE + (255,), (0, 0, W, H))
        y = el.get("y")
        if y is None: y = max(240, (240 + 1330) / 2 - card.height / 2)   # centred between the IG top band and the tracker
        img.alpha_composite(card, (0, int(y))); return
    face = ctx.get("face"); top = int(face[3] + 30) if face else 760; bottom = el.get("bottom", 1270 if brand else 1350)
    s = min(940 / card.width, (bottom - top) / card.height); cw, ch = int(card.width * s), int(card.height * s)
    m = rounded_mask(cw, ch, 36); sm = card.resize((cw, ch), Image.LANCZOS)
    if brand: _bar(img, (W / 2 - cw / 2, top, W / 2 + cw / 2, top + ch), 1.0, "frosted")
    else: sm.putalpha(m)
    img.alpha_composite(sm, (int(W / 2 - cw / 2), top)); _block(ctx, top, hide=True)


def draw_checks(img, el, t, ctx):
    """The checklist (DfVRS 44-48 s, 'so you check 3 boxes with one action'): rows at the left of his chest, a 52 px rounded box with
    a white border on purple, the item in white bold caps (Poppins ExtraBold 40, shadow). Each row appears on its word with an empty
    box and ticks "tick_after" (0.45 s) later. No caption while it's up. "items" [[text, word], ...], "x" (100), "y" (1110),
    "pitch" (80), "dur"/"until" after the last tick (default 1.2 s)."""
    words = ctx["words"]; items = el["items"]; starts = _starts(words, items, lead=el.get("lead", 0.05))
    if t < starts[0]: return
    end = el.get("until")
    if end is None: end = (starts[-1] + el.get("tick_after", 0.45) + el.get("hold", 1.2)) if starts[-1] < 1e8 else 1e9
    if t >= end: return
    x, y0, pitch, ta = el.get("x", 100), el.get("y", 1110), el.get("pitch", 80), el.get("tick_after", 0.45)
    brand = el.get("theme", "brand") == "brand"; tick = YEL if brand else WHITE
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = font(58, "ExtraBold") if brand else poppins(40, "ExtraBold")
    for i, (txt, _) in enumerate(items):
        if t < starts[i]: continue
        y = y0 + i * pitch; bx = x
        d.rounded_rectangle([bx, y - 26, bx + 52, y + 26], 9, fill=(0, 0, 0, 0) if brand else PURPLE + (255,), outline=WHITE + (255,), width=5)
        u = ease(t - starts[i] - ta, 0.14)
        if u > 0:
            p0, p1, p2 = (bx + 12, y + 1), (bx + 22, y + 13), (bx + 42, y - 13)
            if u < 0.4: d.line([p0, (p0[0] + (p1[0] - p0[0]) * u / 0.4, p0[1] + (p1[1] - p0[1]) * u / 0.4)], fill=tick + (255,), width=7)
            else: v = (u - 0.4) / 0.6; d.line([p0, p1, (p1[0] + (p2[0] - p1[0]) * v, p1[1] + (p2[1] - p1[1]) * v)], fill=tick + (255,), width=7, joint="curve")
        shadow_text(img, (bx + 78, y + 2), txt.upper(), f, WHITE, anchor="lm")
    img.alpha_composite(lay); _block(ctx, y0 - 30, hide=True)


# ---------- T24: Hormozi stickers + labelled frames (DfXyDVPopFX "2 reasons why no one is buying", OB's second reel, 11-06) ----------
# 0-2 s two small grey copies of his frame on the table, each tagged; 2-7 s a push-in: his frame as a white-bordered inset over the
# same frame zoomed and blurred, a red "X QUALIFICATION" / green "EDUCATION" tag on it; then white line-drawn stickers pop on the
# table one per spoken noun (money, a runner with a flag, a "90 DAYS" calendar, a document whose lines get highlighted, a video
# window), a red X / green check emoji on "disqualified" / "yes", numbered captions ("#1 budget"). Drawn here in PIL (no AI art).
TAG_RED, TAG_GREEN, OUT = (150, 16, 16), (36, 90, 0), (18, 18, 18)   # bulk pass: his green tag is #245A00


def _stroke(d, pts, w, close=False):
    """A line drawn as a sticker: a dark outline under a white stroke (4x scale drawing)."""
    p = list(pts) + ([pts[0]] if close else [])
    d.line(p, fill=OUT + (255,), width=int(w * 1.9), joint="curve")
    for q in (p[0], p[-1]):
        r = w * 0.95; d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=OUT + (255,))
    d.line(p, fill=WHITE + (255,), width=int(w), joint="curve")
    for q in (p[0], p[-1]):
        r = w * 0.5; d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=WHITE + (255,))


def _icon(kind, size, text="", hl=0.0):
    """One sticker, drawn at 4x and scaled down: money, runner, calendar, doc (hl = highlighted lines, fractional = sweeping),
    video, videos, dumbbell, plate, scale, steps, clock. White bodies, near-black outlines, like his."""
    S = 4 * size; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = int(S * 0.028)
    box = lambda x0, y0, x1, y1, r=0: d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], int(r * S), fill=WHITE + (255,), outline=OUT + (255,), width=o)
    if kind == "money":
        for i in range(3): box(0.12 + i * 0.03, 0.52 - i * 0.12, 0.84 + i * 0.03, 0.80 - i * 0.12, 0.03)
        d.ellipse([0.62 * S, 0.24 * S, 0.84 * S, 0.46 * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        d.text((0.73 * S, 0.35 * S), "$", font=font(int(S * 0.18), "Black"), fill=OUT + (255,), anchor="mm")
    elif kind == "runner":
        w = S * 0.045; c = lambda x, y: (x * S, y * S)
        d.ellipse([0.30 * S, 0.12 * S, 0.44 * S, 0.26 * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        _stroke(d, [c(0.36, 0.28), c(0.32, 0.52)], w); _stroke(d, [c(0.20, 0.36), c(0.30, 0.32), c(0.46, 0.40)], w)
        _stroke(d, [c(0.32, 0.52), c(0.44, 0.66), c(0.40, 0.84)], w); _stroke(d, [c(0.32, 0.52), c(0.20, 0.66), c(0.10, 0.66)], w)
        _stroke(d, [c(0.72, 0.10), c(0.72, 0.88)], w * 0.8); d.polygon([c(0.72, 0.10), c(0.92, 0.18), c(0.72, 0.26)], fill=WHITE + (255,), outline=OUT + (255,), width=o)
    elif kind == "calendar":
        box(0.12, 0.18, 0.88, 0.86, 0.06); d.line([0.12 * S, 0.34 * S, 0.88 * S, 0.34 * S], fill=OUT + (255,), width=o)
        for x in (0.32, 0.68): d.rounded_rectangle([(x - 0.03) * S, 0.10 * S, (x + 0.03) * S, 0.26 * S], int(0.02 * S), fill=WHITE + (255,), outline=OUT + (255,), width=o)
        t1, t2 = (text.split(" ", 1) + [""])[:2] if text else ("", "")
        d.text((0.5 * S, 0.55 * S), t1, font=font(int(S * 0.26), "Black"), fill=OUT + (255,), anchor="mm")
        if t2: d.text((0.5 * S, 0.75 * S), t2.upper(), font=font(int(S * 0.13), "ExtraBold"), fill=OUT + (255,), anchor="mm")
    elif kind == "doc":
        d.polygon([(0.20 * S, 0.08 * S), (0.64 * S, 0.08 * S), (0.80 * S, 0.24 * S), (0.80 * S, 0.92 * S), (0.20 * S, 0.92 * S)], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        d.line([(0.64 * S, 0.08 * S), (0.64 * S, 0.24 * S), (0.80 * S, 0.24 * S)], fill=OUT + (255,), width=o)
        for i in range(6):
            y = (0.34 + i * 0.09) * S; x1 = (0.70 if i % 3 != 2 else 0.56) * S
            f = min(1.0, max(0.0, hl - i))
            if f > 0: d.rectangle([0.28 * S, y - 0.03 * S, 0.28 * S + (x1 - 0.28 * S) * f, y + 0.03 * S], fill=YEL + (255,))
            d.line([0.30 * S, y, x1, y], fill=OUT + (255,), width=int(o * 0.8))
    elif kind in ("video", "videos"):
        if kind == "videos": box(0.06, 0.12, 0.70, 0.60, 0.04)
        x0, y0 = (0.26, 0.32) if kind == "videos" else (0.10, 0.18)
        box(x0, y0, x0 + 0.66 if kind == "videos" else 0.90, y0 + 0.50 if kind == "videos" else 0.80, 0.05)
        cx, cy = (x0 + 0.33, y0 + 0.22) if kind == "videos" else (0.50, 0.45); r = 0.09 if kind == "videos" else 0.12
        d.polygon([((cx - r * 0.6) * S, (cy - r) * S), ((cx + r) * S, cy * S), ((cx - r * 0.6) * S, (cy + r) * S)], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        by = (y0 + 0.42) if kind == "videos" else 0.70; bx0, bx1 = (x0 + 0.06, x0 + 0.60) if kind == "videos" else (0.18, 0.82)
        d.line([bx0 * S, by * S, bx1 * S, by * S], fill=OUT + (255,), width=o); d.ellipse([(bx0 + 0.12 - 0.025) * S, (by - 0.025) * S, (bx0 + 0.12 + 0.025) * S, (by + 0.025) * S], fill=OUT + (255,))
    elif kind == "dumbbell":
        box(0.30, 0.46, 0.70, 0.54, 0.02)
        for x in (0.14, 0.72): box(x, 0.28, x + 0.14, 0.72, 0.04)
        for x in (0.06, 0.86): box(x, 0.38, x + 0.08, 0.62, 0.03)
    elif kind == "plate":
        d.ellipse([0.16 * S, 0.16 * S, 0.84 * S, 0.84 * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        d.ellipse([0.28 * S, 0.28 * S, 0.72 * S, 0.72 * S], outline=OUT + (255,), width=int(o * 0.7))
        _stroke(d, [(0.06 * S, 0.20 * S), (0.06 * S, 0.80 * S)], S * 0.03); _stroke(d, [(0.94 * S, 0.20 * S), (0.94 * S, 0.80 * S)], S * 0.03)
    elif kind == "scale":
        box(0.14, 0.14, 0.86, 0.86, 0.12); box(0.32, 0.24, 0.68, 0.42, 0.04)
        d.text((0.5 * S, 0.33 * S), text or "", font=font(int(S * 0.12), "Black"), fill=OUT + (255,), anchor="mm")
    elif kind == "steps":
        for (x, y, r) in ((0.30, 0.60, 0), (0.62, 0.30, 1)):
            d.ellipse([(x - 0.11) * S, (y - 0.20) * S, (x + 0.11) * S, (y + 0.14) * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
            d.ellipse([(x - 0.08) * S, (y + 0.17) * S, (x + 0.08) * S, (y + 0.31) * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
    elif kind == "clock":
        d.ellipse([0.14 * S, 0.14 * S, 0.86 * S, 0.86 * S], fill=WHITE + (255,), outline=OUT + (255,), width=o)
        d.line([0.5 * S, 0.5 * S, 0.5 * S, 0.26 * S], fill=OUT + (255,), width=o); d.line([0.5 * S, 0.5 * S, 0.68 * S, 0.58 * S], fill=OUT + (255,), width=o)
    return im.resize((size, size), Image.LANCZOS)


def draw_sticker(img, el, t, ctx):
    """A line-drawn sticker popping onto the table on the word that names it (spring from 55%, a 6 degree wobble that settles), held
    until "until"/"until_on"/"off" or "dur" (2.0). "kind" money | runner | calendar ("text": "90 DAYS") | doc ("hl": [[n, word], ...]
    lines highlighted, each sweeping in 0.35 s) | video ("caption": "watch 3:02 to 4:40") | videos | dumbbell | plate | scale | steps |
    clock | emoji ("emoji": "✅"). "x" (540), "y" (1360, above the IG band; his sit lower), "size" (280)."""
    words = ctx["words"]; t0 = _start(el, words); el2 = dict(el); el2.setdefault("dur", 2.0); te = _until(el2, words, t0)
    if t < t0 or t >= te: return
    size = el.get("size", 370); kind = el.get("kind", "doc"); hl = 0.0   # bulk pass: 300-440 px wide, centred y ~1460
    for i, (n, wd) in enumerate(el.get("hl", [])):
        s0 = trigger({"on": wd, "after": t0 - 0.3, "lead": 0.0}, words, default=1e9)
        if t >= s0: hl = max(hl, (n - 1) + min(1.0, (t - s0) / 0.35))
    if kind == "emoji": ic = emoji_img(el["emoji"], int(size * 0.6))
    else:
        k = ("sticker", kind, size, el.get("text", ""), round(hl, 2))
        if k not in _IMG: _IMG[k] = _icon_extra(kind, size, el.get("text", "")) if kind in ("browser", "player") else _icon(kind, size, el.get("text", ""), hl)
        ic = _IMG[k]
    if el.get("enter", "pop") == "draw":   # DfXZ: the sticker draws on from its top-left corner in ~0.35 s, no bounce
        from PIL import ImageChops
        u = ease_out(t - t0, el.get("draw_dur", 0.35)); im = ic.copy()
        if u < 1:
            m = Image.new("L", im.size, 0); ImageDraw.Draw(m).polygon([(0, 0), (im.width * 2.2 * u, 0), (0, im.height * 2.2 * u)], fill=255)
            im.putalpha(ImageChops.multiply(im.split()[3], m))
    elif el.get("enter", "pop") == "spring":   # the 11-06 build (spring from 55% + wobble); his reels show none of it
        p = spring(t - t0, freq=3.4, damp=0.5); s = 0.55 + 0.45 * p; rot = 6 * (1 - p)
        im = ic.resize((max(1, int(ic.width * s)), max(1, int(ic.height * s))), Image.LANCZOS).rotate(rot, Image.BICUBIC, expand=True)
    else:   # bulk pass 11-07: a HARD one-frame pop on the noun, 0-0.12 s early; the next sticker replaces it on the same frame
        im = ic.copy()
    im = _drop_shadow(im, 8, 0.35, 6) if kind != "emoji" else im
    x, y = el.get("x", 540), el.get("y", 1460); img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    if el.get("sparkle", el.get("enter") == "draw") and kind != "emoji": _sparkle(img, x, y, size * 0.48, (t - t0 - 0.05) / 0.55, seed=len(kind))
    if kind == "video" and el.get("caption"):
        f = inter(26, "SemiBold"); tw = f.getlength(el["caption"]); by = y + size * 0.5 + 18
        ImageDraw.Draw(img).rounded_rectangle([x - tw / 2 - 18, by - 22, x + tw / 2 + 18, by + 22], 8, fill=(255, 255, 255, 235), outline=OUT + (255,), width=3)
        ImageDraw.Draw(img).text((x, by), el["caption"], font=f, fill=OUT + (255,), anchor="mm")


def _tag_img(text, kind="x", emoji=None, size=64):
    k = ("tag", text, kind, emoji, size)
    if k not in _IMG:
        f = font(size, "ExtraBold"); s = text.upper(); tw = f.getlength(s); icon = 0
        e = emoji_img(emoji, int(size * 0.8)) if emoji else None
        if kind == "x" or e: icon = int(size * 0.9)
        w, h = int(tw + icon + 44), int(size * 1.3); im = Image.new("RGBA", (w, h), (TAG_RED if kind == "x" else TAG_GREEN) + (255,)); d = ImageDraw.Draw(im)
        x = 20
        if kind == "x":
            c = (x + icon * 0.4, h / 2); r = size * 0.26
            d.line([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(255, 70, 70, 255), width=int(size * 0.13)); d.line([c[0] - r, c[1] + r, c[0] + r, c[1] - r], fill=(255, 70, 70, 255), width=int(size * 0.13))
            x += icon
        elif e: im.alpha_composite(e, (x, int(h / 2 - e.height / 2))); x += icon
        d.text((x, h / 2 + 2), s, font=f, fill=WHITE + (255,), anchor="lm"); _IMG[k] = im
    return _IMG[k]


def draw_tag(img, el, t, ctx):
    """His label tag: white condensed caps (Big Shoulders ExtraBold) on a sharp dark-red tag with a red X, or a dark-green tag with an
    emoji ('📚 EDUCATION'). It snaps in (2 frames) on its word. "text", "kind": "x" | "check", "emoji", "x", "y" (centre), "size" (64),
    "on"/"at", "until"/"until_on"/"dur"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    im = _tag_img(el["text"], el.get("kind", "x"), el.get("emoji"), el.get("size", 64)); a = min(1.0, (t - t0) / 0.07)
    if a < 1: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    img.alpha_composite(_drop_shadow(im, 8, 0.3, 4), (int(el.get("x", 540) - im.width / 2 - 0), int(el.get("y", 1200) - im.height / 2)))


def draw_minis(img, el, t, ctx):
    """The opener's two small copies of his own frame standing on the table (0-2 s), desaturated, each with its tag under it, so the
    two reasons are on screen from frame 0. "labels" [[text, kind, emoji], [..]], "w" (300), "y" (bottom 1480), "at", "until"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    w = el.get("w", 300); h = int(w * 16 / 9); bottom = el.get("y", 1480); src = img.convert("RGB").resize((w, h), Image.LANCZOS).convert("L").convert("RGBA")
    for i, lab in enumerate(el.get("labels", [])):
        cx = W / 2 + (-1 if i == 0 else 1) * (w / 2 + 24); x0 = int(cx - w / 2); y0 = int(bottom - h)
        fr = Image.new("RGBA", (w + 12, h + 12), (235, 235, 235, 255)); fr.alpha_composite(src, (6, 6))
        img.alpha_composite(_drop_shadow(fr, 14, 0.4, 10), (x0 - 6, y0 - 6))
        text, kind, emo = (list(lab) + ["x", None])[:3]; tg = _tag_img(text, kind, emo, 40)
        img.alpha_composite(tg, (int(cx - tg.width / 2), int(bottom - tg.height - 14)))
    _block(ctx, bottom - h, hide=True)


def draw_framein(img, el, t, ctx):
    """The push-in: his whole frame as a 9:16 inset with a 10 px white border (66% of the width, centre y 46%), over the same frame
    zoomed 1.5x and blurred, pushing from 0.92 to 1.0 in 0.3 s. List it FIRST so tags, stickers and captions draw on top.
    "scale" (0.66), "cy" (880), "on"/"at", "until"/"until_on"/"dur"."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    base = img.convert("RGB"); z = 1.5
    bg = base.crop((int(W * (1 - 1 / z) / 2), int(H * (1 - 1 / z) / 2), int(W * (1 + 1 / z) / 2), int(H * (1 + 1 / z) / 2))).resize((W, H)).filter(ImageFilter.GaussianBlur(22))
    sc = el.get("scale", 0.72) * (0.92 + 0.08 * ease_out(t - t0, el.get("push_dur", 0.17))); iw, ih = int(W * sc), int(H * sc); cy = el.get("cy", 880)
    inset = Image.new("RGB", (iw + 20, ih + 20), (255, 255, 255)); inset.paste(base.resize((iw, ih), Image.LANCZOS), (10, 10))
    out = bg.convert("RGBA"); out.alpha_composite(_drop_shadow(inset.convert("RGBA"), 18, 0.45, 10), (int(W / 2 - iw / 2 - 10), int(cy - ih / 2 - 10)))
    img.paste(out, (0, 0))


# ---------- Hormozi upgrade pass (DfXZyinIVtU "6 sales fixes to close more", 11-06): live diagrams on the table ----------
# His numbers are drawn, not said only: a row of 7 white day boxes on the table edge (y ~1400) whose last two fill as "5 -> 7"
# is written above in white marker, then "72 HOURS": the first 3 fill yellow and the rest dim; a dashed slot outline with a
# "SLOT LENGTH" tag and a "15 MIN" bar; stickers that DRAW ON (the outline is drawn in ~0.35 s) with sparkle strokes around
# them; a black play button; small FIX #n tags; number words bold in the captions; a white rounded comment box.


def _hand_note(img, x, y, txt, size=64, a=1.0):
    """White marker writing with a dark edge (Patrick Hand SC), like his '5 -> 7' and '72 HOURS'."""
    f = hand_font(size); lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((x, y), txt, font=f, fill=(255, 255, 255, int(255 * a)), anchor="mm", stroke_width=5, stroke_fill=(25, 22, 20, int(235 * a)))
    img.alpha_composite(lay)


def draw_days(img, el, t, ctx):
    """A row of day boxes on the table (his 7 white outlined squares, M T W T F S S under them). "steps": [{"on": word, "fill": [i...],
    "color": "white" | "yellow", "dim_rest": true}], each step adds its fill; "notes": [[text, word], ...] written above the row in
    white marker (the latest replaces the last; "a->b" draws the arrow); "labels" (7 letters), "y" (row centre 1390), "box" (92),
    "gap" (20), "on"/"at", "until"/"dur"/"until_on". OB: yellow for the days that count (his own week, his steps, his workouts)."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    labels = el.get("labels", list("MTWTFSS")); n = len(labels); b = el.get("box", 104); gap = el.get("gap", 18); y = el.get("y", 1380)   # his row spans ~85% of the width
    x0 = W / 2 - (n * b + (n - 1) * gap) / 2; filled = {}; dim = False; prev = t0 - 0.3
    for st in el.get("steps", []):
        s0 = trigger({"on": st["on"], "after": prev, "lead": st.get("lead", 0.0)}, words, default=1e9)
        if t >= s0:
            prev = s0
            for i in st.get("fill", []): filled[i] = (YEL if st.get("color", "yellow") == "yellow" else WHITE, s0)
            dim = dim or st.get("dim_rest", False)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); pa = min(1.0, (t - t0) / 0.15)
    for i in range(n):
        bx = x0 + i * (b + gap); on = i in filled; al = int(255 * pa * (0.35 if (dim and not on) else 1.0))
        if on:
            col, s0 = filled[i]; u = min(1.0, (t - s0) / 0.12)
            d.rectangle([bx, y - b / 2, bx + b, y + b / 2], fill=col + (int(255 * u * pa),))
        d.rectangle([bx, y - b / 2, bx + b, y + b / 2], outline=(25, 22, 20, int(al * 0.9)), width=14)
        d.rectangle([bx + 3, y - b / 2 + 3, bx + b - 3, y + b / 2 - 3], outline=(255, 255, 255, al), width=8)
        d.text((bx + b / 2, y + b / 2 + 40), labels[i], font=hand_font(54), fill=(255, 255, 255, al), anchor="mm", stroke_width=4, stroke_fill=(25, 22, 20, al))
    img.alpha_composite(lay)
    note, prev = None, t0 - 0.3
    for txt, wd in el.get("notes", []):
        s0 = trigger({"on": wd, "after": prev, "lead": 0.05}, words, default=1e9)
        if t >= s0: note, prev = (txt, s0), s0
    if note:
        txt = note[0].replace("->", "→"); _hand_note(img, W / 2 + el.get("note_dx", 0), y - b / 2 - 70, txt, el.get("note_size", 72), min(1.0, (t - note[1]) / 0.12))
    _block(ctx, y - b / 2 - 120)


def draw_slot(img, el, t, ctx):
    """His slot-length device: a dashed rounded outline at the old length, a tag above it ("SLOT LENGTH"), and a solid bar that
    shrinks (or grows) from "from" to "to" (fractions of "w") on its word, its value written inside ("15 MIN"). "x" (left, 120),
    "y" (bar centre 1400), "w" (560), "h" (86), "from" (1.0), "to" (0.5), "text", "label", "on" (appear), "change" (word that moves
    the bar), "until"/"dur". OB: yellow bar with dark text, the label in white caps with no box."""
    words = ctx["words"]; t0 = _start(el, words); te = _until(el, words, t0)
    if t < t0 or (te is not None and t >= te): return
    x, y, w, h = el.get("x", 120), el.get("y", 1400), el.get("w", 560), el.get("h", 86); brand = el.get("theme", "brand") == "brand"
    tc = trigger({"on": el["change"], "after": t0 - 0.1, "lead": 0.0}, words, default=1e9) if el.get("change") else 1e9
    fr = el.get("from", 1.0) + (el.get("to", 0.5) - el.get("from", 1.0)) * ease_out(t - tc, 0.45) if t >= tc else el.get("from", 1.0)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); a = min(1.0, (t - t0) / 0.15)
    top = y - h / 2 - 60
    for k in range(0, int(w), 26): d.line([x + k, top, x + min(w, k + 14), top], fill=(255, 255, 255, int(230 * a)), width=5)
    for k in range(0, int(h + 60), 26): d.line([x, top + k, x, top + min(h + 60, k + 14)], fill=(255, 255, 255, int(230 * a)), width=5); d.line([x + w, top + k, x + w, top + min(h + 60, k + 14)], fill=(255, 255, 255, int(230 * a)), width=5)
    bw = max(h, w * fr); col = YEL if brand else PURPLE
    d.rounded_rectangle([x, y - h / 2 + 30, x + bw, y + h / 2 + 30], 10, fill=col + (int(255 * a),))
    if el.get("text"):
        d.text((x + bw / 2, y + 32), el["text"].upper(), font=(font(64, "Black") if brand else poppins(44, "ExtraBoldItalic")), fill=(((20, 20, 20) if brand else WHITE) + (int(255 * a),)), anchor="mm")
    img.alpha_composite(lay)
    if el.get("label"):
        if brand: shadow_text(img, (x + w / 2, top - 44), el["label"].upper(), font(60, "ExtraBold"), WHITE, anchor="mm", alpha=int(255 * a), track=3)
        else:
            f = poppins(40, "ExtraBoldItalic"); s = el["label"].upper(); tw = f.getlength(s)
            ImageDraw.Draw(img).rounded_rectangle([x + w / 2 - tw / 2 - 20, top - 74, x + w / 2 + tw / 2 + 20, top - 14], 10, fill=(255, 255, 255, int(255 * a)))
            ImageDraw.Draw(img).text((x + w / 2, top - 44), s, font=f, fill=PURPLE + (int(255 * a),), anchor="mm")
    _block(ctx, top - 80)


def _sparkle(img, cx, cy, r, u, n=6, seed=0):
    """His pop sparkle: short white strokes radiating from the sticker, drawn out then fading (u = 0..1 over ~0.5 s)."""
    if u <= 0 or u >= 1: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); a = int(255 * (1 - max(0.0, (u - 0.5) / 0.5)))
    for k in range(n):
        ang = (k / n) * 2 * math.pi + 0.4 + seed; r0 = r * (1.0 + 0.15 * u); r1 = r0 + 46 * min(1.0, u / 0.4)
        p0 = (cx + r0 * math.cos(ang), cy + r0 * math.sin(ang) * 0.8); p1 = (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang) * 0.8)
        d.line([p0, p1], fill=(25, 22, 20, int(a * 0.8)), width=12); d.line([p0, p1], fill=(255, 255, 255, a), width=6)
    img.alpha_composite(lay)


def _icon_extra(kind, size, text=""):
    """The upgrade's stickers: browser (a window with dots and a line of text, his 'THANK YOU!' page) and player (his black play button)."""
    S = 4 * size; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = int(S * 0.028)
    if kind == "browser":
        d.rounded_rectangle([0.08 * S, 0.16 * S, 0.92 * S, 0.84 * S], int(0.04 * S), fill=(255, 255, 255, 40), outline=WHITE + (255,), width=int(o * 1.2))
        d.line([0.08 * S, 0.28 * S, 0.92 * S, 0.28 * S], fill=WHITE + (255,), width=int(o * 1.2))
        for i in range(3): d.ellipse([(0.13 + i * 0.05) * S, 0.20 * S, (0.16 + i * 0.05) * S, 0.24 * S], fill=WHITE + (255,))
        if text: d.text((0.5 * S, 0.48 * S), text.upper(), font=hand_font(int(S * 0.13)), fill=WHITE + (255,), anchor="mm", stroke_width=int(o * 0.5), stroke_fill=(25, 22, 20, 220))
        d.rounded_rectangle([0.38 * S, 0.60 * S, 0.62 * S, 0.76 * S], int(0.02 * S), outline=WHITE + (255,), width=o)
        d.polygon([(0.47 * S, 0.63 * S), (0.55 * S, 0.68 * S), (0.47 * S, 0.73 * S)], fill=WHITE + (255,))
    elif kind == "player":
        d.rounded_rectangle([0.06 * S, 0.22 * S, 0.94 * S, 0.78 * S], int(0.08 * S), fill=(8, 8, 8, 255), outline=WHITE + (255,), width=int(o * 1.2))
        d.polygon([(0.42 * S, 0.36 * S), (0.64 * S, 0.50 * S), (0.42 * S, 0.64 * S)], fill=WHITE + (255,))
    return im.resize((size, size), Image.LANCZOS)


DRAW = {"slide": draw_slide, "map": draw_map, "seq": draw_seq, "title": draw_title, "text": draw_text, "count": draw_count, "bar": draw_bar, "icons": draw_icons, "line": draw_line,
        "image": draw_image, "marks": draw_marks, "step": draw_step, "burst": draw_burst,
        "tease": draw_tease, "badge": draw_badge, "cta": draw_cta, "scan": draw_scan, "tint": draw_tint, "check": draw_check,
        "itemno": draw_itemno,
        "pill": draw_pill, "paper": draw_paper, "label": draw_label, "quote": draw_quote, "board": draw_board,
        "lower3": draw_lower3, "ctabar": draw_ctabar,
        "tracker": draw_tracker, "steptag": draw_steptag, "takeover": draw_takeover, "checks": draw_checks,
        "sticker": draw_sticker, "tag": draw_tag, "minis": draw_minis, "framein": draw_framein,
        "days": draw_days, "slot": draw_slot}


def draw_all(img, els, t, ctx, layer=None):
    for el in els:
        if layer is not None and el.get("z", "front") != layer: continue
        if el.get("only") and ctx.get("line") not in el["only"]: continue        # tied to the lines it proves (never over a full-frame line)
        DRAW[el["type"]](img, el, t, ctx)


# ---------- self-test ----------
def _selftest_assets(d):
    """A stand-in screenshot (drawn here, labelled as a test card, no real claims) for the image/highlight/outline elements."""
    os.makedirs(d, exist_ok=True); p = os.path.join(d, "test_page.png")
    im = Image.new("RGB", (1000, 560), (250, 250, 248)); dr = ImageDraw.Draw(im)
    dr.text((40, 34), "TEST CARD (not a real study)", font=font(46, "Black"), fill=(20, 20, 20))
    for i, line in enumerate(["Two groups ate the same calories.", "One group ate protein at every meal.", "That group kept more lean mass."]):
        dr.text((40, 140 + i * 110), line, font=font(52, "Medium"), fill=(30, 30, 30))
    im.save(p); return p


def selftest(out):
    os.makedirs(out, exist_ok=True); page = _selftest_assets(out)
    words = [{"w": w, "s": 0.4 + 0.35 * i, "e": 0.4 + 0.35 * i + 0.3} for i, w in enumerate(
        "calories protein two groups ate the same one group kept more lean mass six seven step weigh raw cook".split())]
    ctx = {"words": words, "cache": {}}
    tests = [
        ("title", [{"type": "title", "lines": [["THE", "PROTEIN"], ["MYTH"]], "accent": ["MYTH"], "underline": True, "at": 0.0}]),
        ("count glass", [{"type": "count", "value": 2450, "label": "calories", "unit": "per day", "glass": True, "at": 0.0, "y": 760}]),
        ("bar", [{"type": "bar", "from": 0.30, "to": 0.62, "value": "+18%", "label": "Risk", "at": 0.2, "x": 640, "y": 1100}]),
        ("icons", [{"type": "icons", "fill": [[6, "calories"], [7, "protein"]], "label": "{n} IN 100", "at": 0.0}]),
        ("line", [{"type": "line", "pts": [[0, 0.2], [0.3, 0.7], [0.6, 0.55], [1, 0.9]], "labels": [None, "4H", None, "12H"], "at": 0.0}]),
        ("image hl+outline", [{"type": "image", "path": page, "box": (W / 2, 700, 940), "border": "yellow", "tag": "via TEST",
                               "highlight": [[40, 245, 760, 305, "one", "meal"]], "outline": [[40, 355, 700, 415, "kept"]], "at": 0.0}]),
        ("marks", [{"type": "marks", "items": [{"kind": "arrow", "pts": [[200, 500], [600, 900]], "color": "red", "at": 0.0},
                                               {"kind": "curve", "pts": [[700, 500], [950, 700], [700, 1000]], "color": "green", "at": 0.2},
                                               {"kind": "circle", "pts": [[540, 1250], [220, 130]], "color": "yellow", "at": 0.3},
                                               {"kind": "x", "pts": [[300, 1400]], "color": "red", "at": 0.4},
                                               {"kind": "dash", "pts": [[100, 1600], [980, 1500]], "color": "red", "at": 0.5}]}]),
        ("map", [{"type": "map", "title": "The plan", "rows": [["Protein first", "30 g", "calories"], ["Fiber", "25 g", "two"],
                                                              ["Steps", "8k", "kept"], ["Sleep", "7 h", "zzz"]], "at": 0.0}]),
        ("slide", [{"type": "slide", "items": [["calories", "protein at every meal"], ["two", "walk after dinner"]], "at": 0.0}]),
        ("step", [{"type": "step", "n": 2, "title": "Weigh it raw", "checks": [["the scale on zero", "weigh"], ["before you cook", "cook"]], "at": 0.0}]),
        ("tease", [{"type": "tease", "tiles": [page, page, page, page], "title": [["4", "swaps"]], "accent": ["4"], "at": 0.0}]),
        ("tease return", [{"type": "tease", "tiles": [page, page, page], "title": [["3", "meals"]], "accent": ["3"], "until": 0.3,
                           "returns": [[1, "calories"], [2, "seven"]], "flash": 0.75}]),
        ("badge", [{"type": "badge", "n": 2, "name": "the lunch", "at": 0.0}]),
        ("cta comment", [{"type": "cta", "mode": "comment", "keyword": "plan", "at": 0.0}]),
        ("cta follow", [{"type": "cta", "mode": "follow", "at": 0.0}]),
        ("scan+check", [{"type": "image", "path": page, "box": (W / 2, 520, 940), "at": 0.0, "pop": False},
                        {"type": "scan", "box": (60, 240, 1020, 800), "at": 5.9, "dur": 0.9}, {"type": "check", "x": 940, "y": 290, "at": 0.0}]),
        ("tint", [{"type": "image", "path": page, "box": (W / 2, 520, 940), "at": 0.0, "pop": False}, {"type": "tint", "at": 0.0, "until": 9.0}]),
    ]
    tiles = []
    for name, els in tests:
        for tt in (0.25, 6.0):
            bg = Image.new("RGBA", (W, H), (40, 34, 30, 255)); g = ImageDraw.Draw(bg)
            for yy in range(0, H, 120): g.line([0, yy, W, yy], fill=(52, 46, 41, 255), width=2)
            draw_all(bg, els, tt, ctx); captions(bg, min(tt, words[-1]["e"]), words, y=1380)
            ImageDraw.Draw(bg).text((30, 30), f"{name} t={tt}", font=font(44, "Bold"), fill=(255, 120, 120))
            tiles.append(bg.convert("RGB").resize((270, 480), Image.LANCZOS))
    cols = 8; sheet = Image.new("RGB", (cols * 274, ((len(tiles) + cols - 1) // cols) * 484), (0, 0, 0))
    for i, tl in enumerate(tiles): sheet.paste(tl, ((i % cols) * 274, (i // cols) * 484))
    sheet.save(os.path.join(out, "tmpl_fx_selftest.jpg"), quality=90); print("wrote", os.path.join(out, "tmpl_fx_selftest.jpg"))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "selftest": selftest(a[1])
    else: print(__doc__); sys.exit(2)


# ---------- T21: Sarah Snow's serif captions (decode 2026-11-06, styles/sarah-snow-cinematic-essay.md B1) ----------
SERIF_DIR = os.path.expanduser("~/ob-editor/fonts/EBGaramond")   # EB Garamond variable, SIL OFL (OFL.txt beside it)
OFFWHITE = (252, 254, 247)
_SF = {}


def serif_font(size, weight=400, italic=False):
    k = (int(size), int(weight), bool(italic))
    if k not in _SF:
        f = ImageFont.truetype(os.path.join(SERIF_DIR, "EBGaramond-Italic-VF.ttf" if italic else "EBGaramond-VF.ttf"), int(size))
        try: f.set_variation_by_axes([int(weight)])
        except Exception: pass
        _SF[k] = f
    return _SF[k]


def _sn(s): return s.lower().strip(".,!?;:\"'“”‘’")


def serif_blocks(words, cfg, seg_end):
    """Her phrase blocks for one picture (a picture cut clears the block): 1 to cfg max_words (3) words, split at punctuation, at a
    pause over cfg pause (0.28 s), or at an emphasis word or phrase (cfg "emph"), which gets its own block. Each block appears whole
    cfg lead (0.20 s) before its first word is said and stays until the next block appears (hard, no fade)."""
    emph = [[_sn(x) for x in e.split()] for e in cfg.get("emph", [])]; blocks, cur, i = [], [], 0
    while i < len(words):
        hit = next((len(e) for e in emph if [_sn(w["w"]) for w in words[i:i + len(e)]] == e), 0)
        if hit:
            if cur: blocks.append(dict(ws=cur, emph=False)); cur = []
            blocks.append(dict(ws=words[i:i + hit], emph=True)); i += hit; continue
        w = words[i]; cur.append(w); nxt = words[i + 1] if i + 1 < len(words) else None
        nxt_emph = nxt is not None and any(_sn(nxt["w"]) == e[0] for e in emph)
        if (w["w"].rstrip()[-1:] in ".,!?;:" or (nxt and nxt["s"] - w["e"] > cfg.get("pause", 0.28)) or len(cur) >= cfg.get("max_words", 3)
                or nxt_emph):
            blocks.append(dict(ws=cur, emph=False)); cur = []
        i += 1
    if cur: blocks.append(dict(ws=cur, emph=False))
    lead = cfg.get("lead", 0.20)
    for j, b in enumerate(blocks):
        b["t0"] = b["ws"][0]["s"] - lead; b["t1"] = blocks[j + 1]["ws"][0]["s"] - lead if j + 1 < len(blocks) else seg_end
        b["text"] = " ".join(w["w"] for w in b["ws"]).strip()
        if cfg.get("lower", True): b["text"] = b["text"].lower().replace("'", "’").replace(" i ", " i ")
    return blocks


def _shadow_hue(img, box):
    """Her dark-text colour on a bright background: the shot's darkest 10% of pixels, median colour, lifted to luma about 85."""
    a = np.asarray(img.convert("RGB").resize((108, 192))).reshape(-1, 3).astype(float)
    lum = a @ [0.299, 0.587, 0.114]; d = a[lum <= np.percentile(lum, 10)]; c = np.median(d, axis=0) if len(d) else np.array([60.0, 70, 60])
    l = max(1.0, c @ [0.299, 0.587, 0.114]); c = np.clip(c * (85.0 / l), 0, 255); return tuple(int(v) for v in c)


def serif_captions(img, t, words, cfg, face=None, seg_end=None, y=None):
    """T21 captions on one picture: EB Garamond 400 at 74 px, lower case, line pitch 98, off-white #FCFEF7 with a soft white glow
    (sigma 6 px at 55% + sigma 14 px at 30%); emphasis on its own line, cfg emph_scale (2.2x) in italic 700 (or upright 600 with
    "emph_style": "upright"), blurring in over 0.25 s. On a bright background (mean luma under the text 185+) the text goes dark in
    the shot's shadow hue, no glow. Hook stack: blocks before cfg stack_until (s) build up to 3 ragged lines (+0, +140, +50 px).
    Text never sits on his face: it moves above (or below) the face box with a 60 px margin."""
    if not words: return
    seg_end = seg_end if seg_end is not None else words[-1]["e"] + 0.45
    blocks = serif_blocks(words, cfg, seg_end)
    j = next((i for i, b in enumerate(blocks) if b["t0"] <= t < b["t1"]), None)
    if j is None: return
    su = cfg.get("stack_until", 0.0)
    if t < su:
        k0 = j
        while k0 > 0 and blocks[k0 - 1]["t0"] < su and j - k0 < 2: k0 -= 1
        show = blocks[k0:j + 1]
    else: show = [blocks[j]]
    body = cfg.get("size", 74); pitch = cfg.get("pitch", 98); lines = []
    group = show
    if t < su:   # the stack's final height, so its place is fixed from its first line
        k1 = j
        while k1 + 1 < len(blocks) and blocks[k1 + 1]["t0"] < su and k1 + 1 - k0 < 3: k1 += 1
        group = blocks[k0:k1 + 1]
    for b in show:
        if b["emph"]:
            sz = int(body * cfg.get("emph_scale", 2.2)); up = cfg.get("emph_style", "italic") == "upright"
            f = serif_font(sz, 600 if up else 700, italic=not up); h = int(sz * 1.12)
        else: f = serif_font(body, cfg.get("weight", 420)); h = pitch
        while f.getlength(b["text"]) > W - 200 and f.size > 40:
            f = serif_font(f.size - 4, 700 if b["emph"] else cfg.get("weight", 420), italic=b["emph"] and cfg.get("emph_style", "italic") != "upright")
        lines.append((b, f, h))
    tot = sum(h for _, _, h in lines)
    gtot = sum(int(body * cfg.get("emph_scale", 2.2) * 1.12) if b["emph"] else pitch for b in group)
    yc = y if y is not None else cfg.get("y", 470); top = yc - gtot / 2
    if face:   # never on his head: the face box grown to his hair or cap (0.9 face heights up, a quarter width each side)
        fx0, fy0, fx1, fy1 = face; fw, fh = fx1 - fx0, fy1 - fy0
        hx0, hy0, hx1, hy1 = fx0 - 0.25 * fw, fy0 - 0.9 * fh, fx1 + 0.25 * fw, fy1 + 0.15 * fh
        if top < hy1 + 40 and top + gtot > hy0 - 40:
            top = hy0 - 40 - gtot if hy0 - 40 - gtot > 220 else hy1 + 40
    top = max(220, min(top, 1500 - gtot))
    stack = t < su and len(lines) > 1; offs = cfg.get("stack_offsets", [0, 140, 50])
    x0 = W / 2 - max(f.getlength(b["text"]) for b, f, _ in lines) / 2 - 40 if stack else None
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); yy = top; emph_alpha = 1.0; blur = 0.0
    boxes = []
    for i, (b, f, h) in enumerate(lines):
        x = (x0 + offs[min(i, len(offs) - 1)]) if stack else W / 2 - f.getlength(b["text"]) / 2
        a = 255
        if b["emph"]:
            ti = t - b["t0"]
            if ti < 0.25: a = int(255 * max(0.0, ti / 0.25)); blur = 12 * (1 - max(0.0, ti / 0.25))
        d.text((x, yy + h / 2), b["text"], font=f, fill=(255, 255, 255, a), anchor="lm")
        boxes.append((x, yy, x + f.getlength(b["text"]), yy + h)); yy += h
    bx = (int(max(0, min(b[0] for b in boxes) - 30)), int(max(0, top - 30)), int(min(W, max(b[2] for b in boxes) + 30)), int(min(H, yy + 30)))
    reg = img.convert("L").crop(bx); bright = np.asarray(reg).mean() >= cfg.get("bright", 185)
    alpha = lay.split()[3]
    if blur > 0.3: alpha = alpha.filter(ImageFilter.GaussianBlur(blur))
    if bright:   # dark text in the shot's own shadow colour, no glow
        txt = Image.new("RGBA", img.size, _shadow_hue(img, bx) + (0,)); txt.putalpha(alpha); img.alpha_composite(txt); return
    big = any(b["emph"] for b, _, _ in lines); g = 1.3 if big else 1.0
    for sigma, op in ((14, 0.30), (6, 0.55)):
        gl = Image.new("RGBA", img.size, (255, 255, 255, 0)); gl.putalpha(alpha.filter(ImageFilter.GaussianBlur(sigma)).point(lambda v, o=min(1.0, op * g): int(v * o)))
        img.alpha_composite(gl)
    txt = Image.new("RGBA", img.size, OFFWHITE + (0,)); txt.putalpha(alpha); img.alpha_composite(txt)


def quiet_band(img, need=300, y_lo=220, y_hi=1500, step=20):
    """T21 negative-space placer (B3): the centre y of the horizontal band, need px tall, with the fewest edges (sky, wall, floor),
    so her text sits in the empty part of the picture, not on him."""
    g = np.asarray(img.convert("L").resize((270, 480)).filter(ImageFilter.FIND_EDGES)).astype(float)
    sc = 480 / H; best, by = None, (y_lo + y_hi) / 2
    for y0 in range(y_lo, y_hi - need + 1, step):
        a, b = int(y0 * sc), int((y0 + need) * sc); v = g[a:b, 20:250].mean()
        if best is None or v < best: best, by = v, y0 + need / 2
    return by


# ---------- T26 Drew Canole split-hook explainer (deep pass 11-07, 30 reels: /Volumes/T7/OB-EDITS/2026-11-07-style-truth/drew/DECODE-V2.md) ----------
DREW_RED, DREW_AMBER = (232, 20, 27), (244, 178, 7)


def draw_banner(img, el, t, ctx):
    """Drew's hook banner: a 2-line title-case headline, each line in its own rounded box stacked with no gap, centred on the seam,
    on from frame 0 and gone with the split (use "only"). Measured: Montserrat-like bold 48 px, pad 18/8, radius 14, box #E8141B
    with white text (alt amber #F4B207 + #1E1E1E), max width 960. "style": "brand" = OB's no-box Big Shoulders on the picture."""
    if t < el.get("at", 0.0) or (el.get("until") is not None and t >= el["until"]): return
    lines = el["lines"]; y = el.get("y", 960)
    if el.get("style") == "brand":
        f = font(el.get("size", 84), "Black"); hh = el.get("size", 84) * 1.05
        for i, ln in enumerate(lines):
            shadow_text(img, (W / 2, y + (i - (len(lines) - 1) / 2) * hh), ln.upper(), f, YEL if i == len(lines) - 1 else WHITE, anchor="mm")
        return
    f = poppins(el.get("size", 48), "Bold"); px, py = el.get("pad", (18, 8)); box = tuple(el.get("box", DREW_AMBER if el.get("alt") else DREW_RED))
    tc = tuple(el.get("text", (30, 30, 30) if el.get("alt") else (255, 255, 255)))
    hs = [f.getbbox(ln) for ln in lines]; lh = max(b[3] - b[1] for b in hs) + 2 * py; top = y - lh * len(lines) / 2
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        tw = f.getlength(ln); x0 = W / 2 - tw / 2 - px; y0 = top + i * lh
        d.rounded_rectangle([x0, y0, W / 2 + tw / 2 + px, y0 + lh], el.get("radius", 14), fill=box + (255,))
        d.text((W / 2, y0 + lh / 2), ln, font=f, fill=tc + (255,), anchor="mm")
    img.alpha_composite(lay)


def draw_leak(img, el, t, ctx):
    """Drew's hook exit: a light leak over 9 frames with the cut under frame 5 (f5 = "on" word - 0.10 s). f1-3 an additive radial glow
    from a top corner (warm #FF8A1E or cool #CFF4FF) 0.25->0.6->0.85, radius 40%->90% of the diagonal; f4-5 a near-white bloom #FFF6E8
    at 0.9-1.0; f6-9 decays 0.7->0.35->0.1->0, drifting 80 px."""
    t5 = trigger({"on": el["on"], "after": el.get("after", -1.0), "lead": el.get("lead", 0.10)}, ctx["words"], default=None) if el.get("on") else el.get("at")
    if t5 is None: return
    k = int(round((t - t5) * 30)) + 5
    if not 1 <= k <= 9: return
    op = {1: .25, 2: .6, 3: .85, 4: .95, 5: 1.0, 6: .7, 7: .35, 8: .1, 9: 0.0}[k]
    if op <= 0: return
    diag = (W * W + H * H) ** 0.5; r = diag * (0.4 + 0.5 * min(1, (k - 1) / 4)); cx = (W if el.get("corner", "right") == "right" else 0) - (max(0, k - 5) * 20 * (1 if el.get("corner", "right") == "right" else -1)); cy = 0
    col = (255, 138, 30) if el.get("tone", "warm") == "warm" else (207, 244, 255)
    if k in (4, 5): col = (255, 246, 232)
    yy, xx = np.mgrid[0:H:4, 0:W:4]; dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    a = np.clip(1 - dist / r, 0, 1) ** 1.4 * op; a = Image.fromarray((a * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    base = np.asarray(img.convert("RGB"), np.float32); m = np.asarray(a, np.float32)[..., None] / 255
    scr = 255 - (255 - base) * (255 - np.array(col, np.float32)) / 255   # screen blend
    img.paste(Image.fromarray(np.clip(base * (1 - m) + scr * m, 0, 255).astype(np.uint8)).convert("RGBA"))


def box_captions(img, t, words, cfg, seg_end=None):
    """Drew's box karaoke: a solid box with the whole page of words (~3, max 7); spoken words full contrast, upcoming words at ~45%;
    a word flips on its onset; pages hard-cut. Geometric sans bold 56 px, box height 95, pad 25, radius 8, centre (540, y ~1074).
    "box": colour (default black @65%), "text": colour. One colour per reel."""
    n = cfg.get("n", 3); cur = [w for w in words if w["s"] - 0.05 <= t and (seg_end is None or w["s"] < seg_end)]
    if not cur or t > cur[-1]["e"] + 0.4: return
    k = len(cur) - 1; i0 = k - (k % n); page = [w for w in words if w["s"] >= words[0]["s"]][0:0]
    allw = [w for w in words if (seg_end is None or w["s"] < seg_end)]; j0 = allw.index(cur[i0]) if cur[i0] in allw else 0
    page = allw[j0:j0 + n]; f = poppins(cfg.get("size", 56), "Bold"); txts = [w["w"].strip(",.!?") for w in page]
    sp = f.getlength(" "); tw = sum(f.getlength(x) for x in txts) + sp * (len(txts) - 1); bh = cfg.get("h", 95); pad = cfg.get("pad", 25)
    y = cfg.get("y", 1074); x0 = W / 2 - tw / 2 - pad
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    bc = tuple(cfg.get("box", (0, 0, 0))); d.rounded_rectangle([x0, y - bh / 2, W / 2 + tw / 2 + pad, y + bh / 2], cfg.get("radius", 8), fill=bc + (int(255 * cfg.get("box_a", 0.65)),))
    tc = tuple(cfg.get("text", (255, 255, 255))); x = W / 2 - tw / 2
    for w, s in zip(page, txts):
        on = w["s"] - 0.05 <= t; d.text((x, y), s, font=f, fill=tc + (255 if on else 115,), anchor="lm"); x += f.getlength(s) + sp
    img.alpha_composite(lay)


DRAW.update({"banner": draw_banner, "leak": draw_leak})
