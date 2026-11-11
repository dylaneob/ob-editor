"""levelkit.engine: one frame of a level-kit video, from its plan.json (the GLP level test's compositor, made plan-driven).

World canvas at 1.15x (1242x2208) -> camera crop -> 1080x1920 -> captions, vignette, grain. Layers, back to front:
  background   his own full frame (cold open) or the 2x2 grid of moving cells (cascades, pops, outlines, rack focus)
  depth        elements drawn BEHIND his matte: the title lockup, a 3D object before it goes hero, a depth word (STRONG)
  OB           the BiRefNet cutout across the seam, soft shadow on the grid, layout springs between named layouts
  stage        elements in front of him (above his head): text pops, bars, item labels, 3D blocks, chips, checklists, cards
  screen       captions (his locked style: 3 words, live word #FFD400, under the face box, spring pop per word)
Motion is closed-form springs (fx.spring / fx.kick); camera pushes are linear; punch-ins are hard cuts on words.
Every time in the plan is a cue (see clock.py): a number, a cue name, or {"word", "line", "n", "at", "off"}.

Element types (plan.elements[], drawn in list order inside their layer): title, object3d, depth_word, text_pop, bar,
item_label, blocks3d, chips, checklist, keyword, card, lines. Their keys are documented on each draw_* function and in
../README.md."""
import json, math, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from levelkit.clock import Plan, nearest_existing
from levelkit.fx import spring, kick, lin, mix, font, text_sprite, paste, drop_shadow, _paste_clip, SS, WW, WH, YEL, WHITE, INK

P = None; CFG = {}
QUAD = {"TL": (0, 0), "TR": (540, 0), "BR": (540, 960), "BL": (0, 960)}
ORDER = ("TL", "TR", "BR", "BL")


def col(c):
    if isinstance(c, (list, tuple)): return tuple(c)
    c = {"yel": "#FFD400", "white": "#FFFFFF", "ink": "#111113", "grey": "#969696"}.get(c, c)
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def T(x):
    return P.resolve(x)


def init(path):
    """Load the plan once per process and pre-resolve every cue the elements use."""
    global P, CFG
    P = Plan(path); p = P.p; CFG = {}
    CFG["layouts"] = {k: tuple(v) for k, v in p["layouts"].items()}
    CFG["track"] = [(T(e[0]), e[1], tuple(e[2:4]) if len(e) > 2 else (2.1, 0.62)) for e in p["layout_track"]]
    cam = p["camera"]
    CFG["shots"] = sorted((T(s[0]), s[1], s[2], s[3] if len(s) > 3 else None) for s in cam["shots"])
    CFG["zoom_through"] = [(T(a), T(b), za, zb) for a, b, za, zb in cam.get("zoom_through", [])]
    CFG["kicks"] = [(T(k[0]), k[1], k[2], k[3], k[4] if len(k) > 4 else 0.0) for k in cam.get("kicks", [])]
    CFG["top_guard"] = [(T(a), T(b) if b is not None else 1e9, y) for a, b, y in cam.get("top_guard", [])]
    CFG["land_amp"] = cam.get("land_amp", 0.22)
    g = p["grid"]
    CFG["sched"] = [(e["set"], {q: T(e["at"][q]) for q in ORDER}, e.get("style", "cascade")) for e in g["schedule"]]
    CFG["base"] = {s: T(v) for s, v in g["frame_base"].items()}
    pops = []
    for e in g.get("pops", []):
        qs = list(ORDER) if e["q"] == "ALL" else ([e["q"]] if isinstance(e["q"], str) else e["q"])
        for i, q in enumerate(qs): pops.append((q, T(e["cue"]) + e.get("stagger", 0.0) * i, e["amp"]))
    CFG["pops"] = pops
    CFG["outlines"] = [(o["q"], o.get("set"), T(o["on"]), T(o["off_from"]), T(o["off_to"])) for o in g.get("outlines", [])]
    CFG["rack"] = [(T(r["in"]), T(r["out"]), r.get("blur", 11), r.get("dim", 0.26), tuple(r.get("spring_in", (2.4, 0.75)))) for r in g.get("rack", [])]
    CFG["top_grade"] = [(T(a), T(b), h, s) for a, b, h, s in g.get("top_grade", [])]
    CFG["seams_from"] = T(g.get("seams_from", 0))
    CFG["cold_until"] = T(p.get("cold_open_until", 0))
    CFG["face"] = p.get("face", {"eye_x": 0.51, "eye_y": 0.305, "chin_y": 0.39, "box_bottom": 0.45})
    CFG["elements"] = p.get("elements", [])
    CFG["captions"] = p.get("captions", {})
    CFG["caps"] = caption_groups()


# ---------------- OB: layout, face ----------------
def layout(t):
    cur = CFG["layouts"][CFG["track"][0][1]]
    for t0, name, (f, d) in CFG["track"][1:]:
        if t >= t0:
            u = spring(t - t0, f, d); cur = tuple(mix(c, l, u) for c, l in zip(cur, CFG["layouts"][name]))
    return cur


def face_pts(t):
    S, ox, oy = layout(t); F = CFG["face"]
    return (ox + F["eye_x"] * S * 1080, oy + F["eye_y"] * S * 1920), oy + F["chin_y"] * S * 1920


@lru_cache(maxsize=4)
def him(k):
    j = P.cam_frame(k)
    rgb = Image.open(nearest_existing(P.aroll_path, j)).convert("RGB")
    try: a = Image.open(nearest_existing(P.matte_path, j, 30)).convert("L")
    except FileNotFoundError:                                  # LK_PREVIEW=1 (stills only, never a render): any finished matte,
        if not os.environ.get("LK_PREVIEW"): raise              # to check graphics placement before the matte job gets there
        md = os.path.join(P.work, "matte"); done = sorted(int(f[2:8]) for f in os.listdir(md) if f.startswith("a_") and f.endswith(".png") and "part" not in f)
        a = Image.open(P.matte_path(min(done, key=lambda d: abs(d - j)))).convert("L"); rgb = Image.open(P.aroll_path(min(done, key=lambda d: abs(d - j)))).convert("RGB")
    a = a.point(lambda v: 0 if v < 10 else (255 if v > 245 else v))     # crush the matte's faint haze, keep its own edge
    return rgb, a


def him_layer(k, S):
    rgb, a = him(k); w, h = int(round(S * 1080 * SS)), int(round(S * 1920 * SS))
    return rgb.resize((w, h), Image.LANCZOS), a.resize((w, h), Image.BILINEAR)


# ---------------- camera ----------------
def camera(t):
    sh = CFG["shots"]; i = max(j for j, s in enumerate(sh) if t >= s[0]); t0, z0, z1, mode = sh[i]
    t1 = sh[i + 1][0] if i + 1 < len(sh) else P.end
    z = mix(z0, z1, lin(t, t0, t1)); blur = 0.0; hold = False
    for a, b, za, zb in CFG["zoom_through"]:                   # zoom through the old grid into a new section
        if a <= t < b: z = mix(za, zb, lin(t, a, b)); blur = lin(t, a, b)
        if a <= t < b + 0.4: hold = True
    if mode == "land":                                         # land the new section from 1.22x on a spring
        z = 1.0 + CFG["land_amp"] * (1 - spring(t - t0, 2.6, 0.78)); blur = max(0.0, 1 - (t - t0) / 0.10)
    z = max(z, 1.0)
    (fx_, fy_), _ = face_pts(t)
    cx, cy = (fx_, fy_ + 40) if (mode == "face" or (mode is None and z > 1.02)) else (540.0, 960.0)
    if hold: cx, cy = fx_, fy_
    for tk, amp, f, d, za in CFG["kicks"]:                     # micro impacts (landings, sub hits)
        kk = kick(t - tk, f, d); cy += amp * kk
        if za: z = max(z, 1.0 + za * max(0.0, kk))
    for a, b, y in CFG["top_guard"]:                           # a punch-in never pushes a top graphic into the IG band
        if a <= t < b:
            if z > 1.001: cy = min(cy, y + (960 - 232) / z)
            break
    hw, hh = 540 / z, 960 / z
    return z, min(max(cx, hw), 1080 - hw), min(max(cy, hh), 1920 - hh), blur


# ---------------- grid ----------------
@lru_cache(maxsize=1)
def wall():
    k = int(T(P.p["grid"].get("wall_at", CFG["sched"][0][1]["TL"])) * P.fps) + 1
    im = Image.open(nearest_existing(P.aroll_path, P.cam_frame(k))).convert("RGB")
    return im.crop((0, 0, 1440, 64)).resize((WW, WH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(4))


@lru_cache(maxsize=64)
def cell_img(name, k):
    d = os.path.join(P.work, "cells", name); n = len([f for f in os.listdir(d) if f.endswith(".jpg")]); k = min(max(k, 0), n - 1)
    return Image.open(f"{d}/c_{k + 1:04d}.jpg").convert("RGB")


def cell_set_at(t, q):
    cur = (None, None, None)
    for s, at, style in CFG["sched"]:
        if t >= at[q]: cur = (s, at[q], style)
    return cur


def draw_cell(bg, s, q, t, scale=1.0, lift=0.0, outline=0.0):
    img = cell_img(P.p["grid"]["sets"][s][q], int((t - CFG["base"][s]) * P.fps))
    cw, ch = int(540 * SS * scale), int(960 * SS * scale)
    im = img.resize((cw, ch), Image.BILINEAR)
    if lift > 0.004: im = Image.blend(im, Image.new("RGB", im.size, (255, 246, 225)), lift)
    cx, cy = (QUAD[q][0] + 270) * SS, (QUAD[q][1] + 480) * SS; x0, y0 = int(cx - cw / 2), int(cy - ch / 2)
    if scale > 1.004:                                          # a lifted card throws a soft shadow on its neighbours
        sh = Image.new("RGBA", (cw + 120, ch + 120), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([60, 60, cw + 60, ch + 60], fill=(0, 0, 0, int(150 * min(1, (scale - 1) / 0.08))))
        sh = sh.filter(ImageFilter.GaussianBlur(26)); bg.paste(sh, (x0 - 60 + 8, y0 - 60 + 18), sh)
    bg.paste(im, (x0, y0))
    if outline > 0.01:
        w8 = 9 * SS; ox0, oy0 = max(x0, 0) + w8 / 2, max(y0, 0) + w8 / 2; ox1, oy1 = min(x0 + cw, WW) - w8 / 2, min(y0 + ch, WH) - w8 / 2
        ov = Image.new("RGBA", bg.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rectangle([ox0, oy0, ox1, oy1], outline=YEL + (int(255 * outline),), width=int(w8))
        bg.paste(ov, (0, 0), ov)


def grid_bg(t):
    bg = wall().copy(); state = {q: cell_set_at(t, q) for q in ORDER}
    for q in sorted(ORDER, key=lambda q: state[q][1] or 0):    # the one that landed last goes on top
        s, landed, style = state[q]
        if s is None: continue
        tl = t - landed; scale, lift = 1.0, 0.0
        if style == "cascade":                                 # snaps from 1.10 on a stiff spring, warm flash decays
            scale = 1.0 + 0.10 * (1 - spring(tl, 3.6, 0.62)); lift = 0.30 * max(0.0, 1 - tl / 0.13)
        for pq, pt, amp in CFG["pops"]:
            if pq == q: scale += amp * kick(t - pt, 2.6, 0.30)
        outline = 0.0
        for oq, oset, on, off0, off1 in CFG["outlines"]:
            if oq == q and (oset is None or oset == s) and t >= on: outline = max(outline, spring(t - on, 3.0, 0.7) * (1 - lin(t, off0, off1)))
        draw_cell(bg, s, q, t, scale, lift, outline)
    if t >= CFG["seams_from"]:                                 # hairline seams give the 2x2 its edges
        d = ImageDraw.Draw(bg, "RGBA")
        d.rectangle([540 * SS - 1.5, 0, 540 * SS + 1.5, WH], fill=(0, 0, 0, 90)); d.rectangle([0, 960 * SS - 1.5, WW, 960 * SS + 1.5], fill=(0, 0, 0, 90))
    return bg


def rack(t):
    """Background defocus windows (stage beats): 0 -> 1 -> 0 on springs; blur and dim come from the latest window."""
    u, blur, dim = 0.0, 11, 0.26
    for a, b, bl, dm, (f, d) in CFG["rack"]:
        if t >= a:
            u += spring(t - a, f, d) - (spring(t - b, 2.6, 0.75) if t >= b else 0); blur, dim = bl, dm
    return min(max(u, 0.0), 1.2), blur, dim


# ---------------- elements ----------------
def lockup(el, t):
    """(scale, anchor y, lift) of a title lockup: cold -> docked over the grid -> lifted out."""
    u = spring(t - T(el["dock"]["cue"]), *el["dock"].get("spring", (2.2, 0.62))) if t >= T(el["dock"]["cue"]) else 0.0
    lift = spring(t - T(el["lift"]["cue"]), *el["lift"].get("spring", (2.4, 0.72))) if "lift" in el and t >= T(el["lift"]["cue"]) else 0.0
    top = el["lines"][0]["top"]
    return mix(1.0, el["dock"]["scale"], u), mix(top, el["dock"]["top"], u), lift


def to_lock(el, x, y, t):
    sc, ay, lift = lockup(el, t); top = el["lines"][0]["top"]
    return 540 + (x - 540) * sc, ay + (y - top) * sc - el.get("lift", {}).get("dy", 760) * lift, sc


@lru_cache(maxsize=16)
def word_row(words, size, colors):
    spr = [text_sprite(w, size, col(c)) for w, c in zip(words, colors)]
    gap = size * 0.24; widths = [s[3] / SS for s in spr]; total = sum(widths) + gap * (len(words) - 1)
    x = 540 - total / 2; out = []
    for w, s, wd in zip(words, spr, widths): out.append((w, x, s, wd)); x += wd + gap
    return out


def draw_title(layer, el, t):
    """title: lines [{words, size, colors, top, t0, stagger, rise, spring, grow, fade}], dock {cue, scale, top}, lift {cue, dy},
    gone {cue}, drift (px/s before the dock), sub {text, size, in, out, y}: the cold-open lockup that docks over the grid."""
    if t > T(el["gone"]): return
    dock_t = T(el["dock"]["cue"])
    for ln in el["lines"]:
        row = word_row(tuple(ln["words"]), ln["size"], tuple(ln["colors"]))
        for i, (w, x, spr, wd) in enumerate(row):
            ti = t - (ln["t0"] + ln["stagger"] * i)
            if ti <= 0: continue
            f, d = ln["spring"]; p = spring(ti, f, d); drift = -el.get("drift", 8) * min(t, dock_t)
            a = min(1.0, ti / ln["fade"]) if ln.get("fade") else 1.0
            X, Y, s = to_lock(el, x + wd / 2, ln["top"] + (1 - p) * ln["rise"] + drift, t)
            X2, Y2, _ = to_lock(el, x + wd / 2, ln["top"] + (1 - spring(ti + 1 / P.fps, f, d)) * ln["rise"] + drift, t + 1 / P.fps)
            sc = s * (1 - ln.get("grow", 0) + ln.get("grow", 0) * p)
            paste(layer, spr[0], X * SS, Y * SS, scale=sc, alpha=a, anchor=((spr[1] + spr[3] / 2) / spr[0].width, spr[2] / spr[0].height), mb=((X2 - X) * SS, (Y2 - Y) * SS))
    sub = el.get("sub")
    if sub and T(sub["in"]) <= t < T(sub["out"]) + 0.3:       # the disclaimer, once, small, under the docked title
        a = min(1.0, (t - T(sub["in"])) / 0.12) * (1 - lin(t, T(sub["out"]), T(sub["out"]) + 0.2)); p = spring(t - T(sub["in"]), 3.0, 0.7)
        spr = text_sprite(sub["text"], sub.get("size", 34), (240, 240, 240), "ExtraBold", 3, True, 0.95)
        X, Y, s = to_lock(el, 540, sub["y"] + (1 - p) * 14, t)
        paste(layer, spr[0], X * SS, Y * SS, scale=1.0, alpha=a, anchor=(0.5, spr[2] / spr[0].height))


@lru_cache(maxsize=400)
def obj_sprite(d, k, n):
    return Image.open(os.path.join(d, f"p_{min(max(k, 0), n - 1) + 1:04d}.png")).convert("RGBA")


def obj_state(el, t):
    """object3d phases: drop {t, from [x,y,L], to [x,y,L], spring, rot0, rot_spring}, dock_title (follows a title lockup id),
    hero {cue, to [x,y,L], spring, kick, wobble}, exit {cue, d [dx,dy], rot, spring}, until (cue), play {rate_after, after}."""
    dr = el["drop"]; t_in = T(dr["t"])
    if t < t_in or t > T(el["until"]): return None
    p = spring(t - t_in, *dr["spring"]); x, y, L = mix(dr["from"][0], dr["to"][0], p), mix(dr["from"][1], dr["to"][1], p), mix(dr["from"][2], dr["to"][2], p)
    rot = dr.get("rot0", 0) * (1 - spring(t - t_in, *dr.get("rot_spring", (2.0, 0.5))))
    if "dock_title" in el:
        ti = next(e for e in CFG["elements"] if e.get("id") == el["dock_title"])
        if t >= T(ti["dock"]["cue"]):
            X, Y, s = to_lock(ti, x, y, t); x, y, L = X, Y + ti.get("lift", {}).get("dy", 760) * lockup(ti, t)[2], L * s
    if "hero" in el and t >= T(el["hero"]["cue"]):
        h = el["hero"]; th = T(h["cue"]); v = spring(t - th, *h.get("spring", (2.0, 0.62)))
        x, y, L = mix(x, h["to"][0], v), mix(y, h["to"][1], v), mix(L, h["to"][2], v)
        rot += h.get("kick", -9) * kick(t - th, 1.8, 0.4) + h.get("wobble", 2.6) * math.sin(2 * math.pi * 0.45 * (t - th))
    if "exit" in el and t >= T(el["exit"]["cue"]):
        ex = el["exit"]; w = spring(t - T(ex["cue"]), *ex.get("spring", (2.4, 0.9))); x += ex["d"][0] * w; y += ex["d"][1] * w; rot += ex.get("rot", -38) * w
    pl = el.get("play", {}); t0p = T(pl.get("t0", dr["t"])); after = T(pl.get("after", 1e9))   # render frame clock: 1x, then rate_after
    fk = int(P.fps * (pl.get("offset", 0.0) + (min(t, after) - t0p) + pl.get("rate_after", 1.0) * max(0.0, t - after)))
    return x, y, L, rot, fk


def draw_object3d(layer, el, t):
    st = obj_state(el, t)
    if not st: return
    x, y, L, rot, fk = st; d = el["frames"]; n = len([f for f in os.listdir(d) if f.startswith("p_")])
    spr = obj_sprite(d, fk, n); s = L * SS / el.get("len_px", 1300.0)
    nx = obj_state(el, t + 1 / P.fps); mv = ((nx[0] - x) * SS, (nx[1] - y) * SS) if nx else None
    sm = spr.resize((int(spr.width * s), int(spr.height * s)), Image.BICUBIC)
    paste(layer, drop_shadow(sm, blur=10 * SS, alpha=0.5), x * SS, (y + 26) * SS, rot=rot, mb=mv)
    paste(layer, sm, x * SS, y * SS, rot=rot, mb=mv)


@lru_cache(maxsize=8)
def letters(text, size, c):
    return [text_sprite(ch, size, col(c)) for ch in text]


def draw_depth_word(layer, el, t):
    """depth_word: text, size, color, top, rise (cue), stagger, sweep (cue), sag (cue), soft (cue), out (cue): the word rises
    from behind his head; one light sweep; on 'sag' it sags like a rope and greys; on 'soft' it defocuses; 'out' drops it away."""
    tr = T(el["rise"])
    if t < tr - 0.16: return
    if "out" in el and t > T(el["out"]) + 0.6: return
    S_ = letters(el["text"], el["size"], el.get("color", "yel")); G_ = letters(el["text"], el["size"], "grey")
    widths = [s_[3] / SS for s_ in S_]; gap = el.get("gap", 6); total = sum(widths) + gap * (len(S_) - 1)
    x = 540 - total / 2; base = el["top"]; L = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    tsag = T(el["sag"]) if "sag" in el else 1e9; tsoft = T(el["soft"]) if "soft" in el else 1e9
    grey = lin(t, tsag, tsag + 0.32); g = spring(t - tsag, 1.6, 0.45) if t >= tsag else 0.0
    soft = spring(t - tsoft, 2.4, 0.7) if t >= tsoft else 0.0
    out = spring(t - T(el["out"]), 2.2, 0.8) if "out" in el and t >= T(el["out"]) else 0.0
    for i, (spr, spg) in enumerate(zip(S_, G_)):
        ti = t - (tr - 0.16 + el.get("stagger", 0.035) * i)
        if ti <= 0: x += widths[i] + gap; continue
        p = spring(ti, 2.6, 0.55); dy = (1 - p) * 300; vy = ((1 - spring(ti + 1 / P.fps, 2.6, 0.55)) - (1 - p)) * 300
        u = (x + widths[i] / 2 - (540 - total / 2)) / total
        dy += g * 46 * math.sin(math.pi * u) + soft * 10 + out * 420; rot = -g * 11 * math.cos(math.pi * u)
        for spx, a in ((spr[0], (1 - grey) * (1 - out)), (spg[0], grey * (1 - out))):
            if a <= 0.01: continue
            paste(L, spx, (x + widths[i] / 2) * SS, (base + dy) * SS, alpha=a, rot=rot, anchor=((spr[1] + spr[3] / 2) / spr[0].width, spr[2] / spr[0].height), mb=(0, vy * SS))
        x += widths[i] + gap
    if soft > 0.02:
        box = (0, int(380 * SS), WW, int(1000 * SS)); L.paste(L.crop(box).filter(ImageFilter.GaussianBlur(8 * SS * min(soft, 1.2))), box[:2])
    if "sweep" in el and T(el["sweep"]) - 0.08 <= t < T(el["sweep"]) + 0.5 and t < tsag:
        sweep(L, t, T(el["sweep"]), (0, int((base - 48) * SS), WW, int((base + 352) * SS)))
    layer.alpha_composite(L)


def sweep(layer, t, tc, region):
    u = lin(t, tc - 0.08, tc + 0.42); x0, y0, x1, y1 = region
    a = np.asarray(layer.crop(region), np.float32); h, w = a.shape[:2]; yy, xx = np.mgrid[0:h, 0:w]
    pos = -0.3 * w + u * 1.6 * w; band = np.exp(-((xx + 0.35 * yy - pos) / (0.07 * w)) ** 2) * 0.55
    al = a[..., 3:4] / 255.0; a[..., :3] = a[..., :3] + (255 - a[..., :3]) * band[..., None] * al
    layer.paste(Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"), (x0, y0))


def exit_off(el, t):
    """0..1 exit progress for elements with out {cue, spring, dy}."""
    if "out" not in el or t < T(el["out"]["cue"]): return 0.0
    return spring(t - T(el["out"]["cue"]), *el["out"].get("spring", (2.6, 0.85)))


def draw_text_pop(layer, el, t):
    """text_pop: text, size, color, weight, track, x, y, in (cue), rise, spring, out {cue, dy, spring}, rot, stamp (kick scale)."""
    ti = T(el["in"])
    if t < ti or ("out" in el and t > T(el["out"]["cue"]) + 0.6): return
    o = exit_off(el, t); p = spring(t - ti, *el.get("spring", (3.0, 0.62)))
    spr = text_sprite(el["text"], el["size"], col(el.get("color", "white")), el.get("weight", "Black"), el.get("track", 10))
    sc = (1 + el.get("stamp", 0) * (1 - p)) if el.get("stamp") else 1.0
    if "pulse" in el: sc *= 1 + 0.08 * kick(t - T(el["pulse"]), 2.6, 0.3)
    y = el["y"] + (1 - p) * el.get("rise", 30) + el.get("out", {}).get("dy", -700) * o
    al = min(1, (t - ti) / 0.08) * ((1 - 0.9 * o) if el.get("fade_out") else 1.0); x = el.get("x", 540); bx = el.get("box_after")
    if bx:                                                     # "3. [   ]": an empty blinking slot after the text (an open loop)
        tw_ = spr[3] / SS; x = x - (tw_ + 30 + bx["w"]) / 2 + tw_ / 2; xs = x + tw_ / 2 + 30; pw = spring(t - ti - 0.12, 3.0, 0.62)
        blink = 0.6 + 0.4 * math.cos(2 * math.pi * 1.6 * (t - ti)); d = ImageDraw.Draw(layer, "RGBA"); sz = el["size"]
        d.rounded_rectangle([xs * SS, (y - sz * 0.04) * SS, (xs + bx["w"] * pw) * SS, (y + sz * 0.76) * SS], radius=18 * SS, fill=(12, 12, 14, int(150 * al)),
                            outline=YEL + (int(255 * blink * al),), width=int(7 * SS))
    paste(layer, spr[0], x * SS, y * SS, scale=sc, alpha=al, rot=el.get("rot", 0) * p, anchor=(el.get("ax", 0.5), spr[2] / spr[0].height))
    if el.get("underline"):
        w = spr[3] / SS * spring(t - ti - 0.08, 3.2, 0.7); d = ImageDraw.Draw(layer, "RGBA"); yy = y + el["size"] * 0.78
        d.rounded_rectangle([(x - w / 2) * SS, yy * SS, (x + w / 2) * SS, (yy + 12) * SS], radius=6 * SS, fill=YEL + (int(255 * (1 - o)),))


def draw_bar(layer, el, t):
    """bar: label, x0, x1, yc, hh, in (cue), levels [[cue, level, f, d]] (starts at level0), arrow {from, bounce, dir}, moves
    [[cue, yc]], label_color [[cue, color]], out {cue, dy}: a meter that slides in full and drains (or refills) on words."""
    ti = T(el["in"])
    if t < ti or ("out" in el and t > T(el["out"]["cue"]) + 0.7): return
    o = exit_off(el, t); q = spring(t - ti, *el.get("spring", (2.8, 0.7)))
    x0, x1, hh = el.get("x0", 170), el.get("x1", 910), el.get("hh", 34); yc = el["yc"]
    for m in el.get("moves", []):
        if t >= T(m[0]): yc = mix(yc, m[1], spring(t - T(m[0]), 2.6, 0.62))
    yo = el.get("out", {}).get("dy", -700) * o; w = (x1 - x0) * q; xa = 540 - w / 2
    d = ImageDraw.Draw(layer, "RGBA")
    d.rounded_rectangle([xa * SS, (yc - hh / 2 + yo) * SS, (xa + w) * SS, (yc + hh / 2 + yo) * SS], radius=hh / 2 * SS, fill=(10, 10, 12, 165), outline=(255, 255, 255, 70), width=int(2 * SS))
    for i in range(1, 10):
        xt = xa + w * i / 10; d.line([xt * SS, (yc - hh / 2 + 7 + yo) * SS, xt * SS, (yc + hh / 2 - 7 + yo) * SS], fill=(255, 255, 255, 38), width=int(2 * SS))
    fill = el.get("level0", 1.0)
    for lv in el.get("levels", []):
        if t >= T(lv[0]): fill = mix(fill, lv[1], spring(t - T(lv[0]), lv[2] if len(lv) > 2 else 1.55, lv[3] if len(lv) > 3 else 0.72))
    fw = max(hh, (w - 8) * min(fill, el.get("max_fill", 1.03)))
    d.rounded_rectangle([(xa + 4) * SS, (yc - hh / 2 + 4 + yo) * SS, (xa + 4 + fw) * SS, (yc + hh / 2 - 4 + yo) * SS], radius=(hh / 2 - 4) * SS, fill=YEL + (255,))
    lc = el.get("label_color0", "white")
    for c_ in el.get("label_color", []):
        if t >= T(c_[0]): lc = c_[1]
    lab = text_sprite(el["label"], el.get("label_size", 46), col(lc), "ExtraBold", 8)
    paste(layer, lab[0], (xa + 2) * SS, (yc - hh / 2 - 58 + yo) * SS, alpha=q, anchor=(lab[1] / lab[0].width, lab[2] / lab[0].height))
    ar = el.get("arrow")
    if ar and t >= T(ar["from"]) - 0.05 and t < T(ar.get("until", 1e9)):                       # the arrow rides the end of the fill and bounces on its word
        up = ar.get("dir", "down") == "up"; ax = xa + 4 + fw; ay = yc - hh / 2 - 26 + yo - 14 * kick(t - T(ar["bounce"]), 2.4, 0.35)
        tri = [((ax - 17) * SS, (ay - 16) * SS), ((ax + 17) * SS, (ay - 16) * SS), (ax * SS, (ay + 10) * SS)]
        if up: tri = [((ax - 17) * SS, (ay + 10) * SS), ((ax + 17) * SS, (ay + 10) * SS), (ax * SS, (ay - 16) * SS)]
        d.polygon(tri, fill=YEL + (int(255 * min(1, (t - T(ar["from"]) + 0.05) / 0.1) * (1 - o)),))


def draw_item_label(layer, el, t):
    """item_label: num ('1.'), name, in (cue), pulse (cue), dock (cue), tag [x, top, scale], big_top, size, out {cue}, reveal
    [[cue, word], ...] (the name types in word by word: an open slot until then), slot (cue: draw the empty slot)."""
    ti = T(el["in"])
    if t < ti + 0.02: return
    if "out" in el and t > T(el["out"]["cue"]) + 0.6: return
    o = exit_off(el, t)
    a = spring(t - (ti + 0.02), 3.4, 0.55); b = spring(t - (ti + 0.10), 2.8, 0.6)
    dock = spring(t - T(el["dock"]), 2.4, 0.7) if "dock" in el and t >= T(el["dock"]) else 0.0
    pulse = 1 + 0.07 * kick(t - T(el["pulse"]), 2.6, 0.3) if "pulse" in el else 1.0
    size = el.get("size", 196); one = text_sprite(el["num"], size, YEL)
    names = el.get("reveal") or [[el["in"], el["name"]]]
    shown = [w for c_, w in names if t >= T(c_)]; full = " ".join(w for _, w in names)
    mus_full = text_sprite(full, size, WHITE); w1, w2 = one[3] / SS, mus_full[3] / SS; gap = 30
    fit = min(1.0, el.get("fit_w", 940) / (w1 + gap + w2))      # long names shrink to fit the width while big
    total = (w1 + gap + w2) * fit; big_x, big_top = 540 - total / 2, el.get("big_top", 300.0)
    tag = el.get("tag", [46.0, 238.0, 0.30]); s = mix(fit, tag[2], dock) * pulse
    lx = mix(big_x, tag[0], dock); top = mix(big_top, tag[1], dock) - el.get("out", {}).get("dy", 700) * o
    al = 1 - o
    paste(layer, one[0], (lx + w1 / 2 * s) * SS, top * SS, scale=s * (0.55 + 0.45 * a), alpha=min(1, (t - ti) / 0.06) * al, anchor=((one[1] + one[3] / 2) / one[0].width, one[2] / one[0].height))
    x = lx + (w1 + gap) * s
    if el.get("reveal") and len(shown) < len(names) and "slot" in el and t >= T(el["slot"]):
        rest = text_sprite(" ".join(w for _, w in names[len(shown):]), size, WHITE); x_s = x + (sum(text_sprite(w + " ", size, WHITE)[3] for w in shown) / SS) * s
        d = ImageDraw.Draw(layer, "RGBA"); wv = rest[3] / SS * s; blink = 0.6 + 0.4 * math.cos(2 * math.pi * 1.6 * (t - T(el["slot"])))
        ps = spring(t - T(el["slot"]), 3.0, 0.6); y0s, y1s = top - size * 0.06 * s, top + size * 0.80 * s   # an empty slot the name types into
        d.rounded_rectangle([x_s * SS, y0s * SS, (x_s + wv * ps) * SS, y1s * SS], radius=14 * SS, fill=(12, 12, 14, int(110 * al)),
                            outline=YEL + (int(255 * blink * al),), width=int(6 * SS))
    for j, (c_, w) in enumerate(names):
        tw_ = T(c_) + (0.0 if el.get("reveal") else 0.10)       # a plain label's name lands 0.10 s after its number
        if t < tw_: break
        spr = text_sprite(w, size, WHITE); bj = spring(t - tw_, 2.8, 0.6)
        paste(layer, spr[0], (x + spr[3] / SS / 2 * s) * SS, (top + (1 - bj) * 60 * s) * SS, scale=s, alpha=min(1, (t - tw_) / 0.06) * al, anchor=((spr[1] + spr[3] / 2) / spr[0].width, spr[2] / spr[0].height))
        x += (spr[3] / SS + text_sprite(" ", size, WHITE)[3] / SS) * s


@lru_cache(maxsize=3)
def block_frame(d, k, fix_white):
    """A Blender render with its yellow pushed back to #FFD400 (AgX mutes saturated yellow), and the white text on ink faces lifted."""
    im = Image.open(os.path.join(d, f"b_{k + 1:04d}.png")).convert("RGBA")
    a = np.asarray(im, np.float32); rgb = a[..., :3] / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1); sat = (mx - mn) / (mx + 1e-6)
    yel = ((rgb[..., 0] > rgb[..., 2] + 0.12) & (rgb[..., 1] > rgb[..., 2] + 0.05)).astype(np.float32)
    target = np.array([1.0, 212 / 255, 0.0]); boosted = target * np.clip(mx[..., None] * 1.22, 0, 1.0)
    wgt = (yel * np.clip(sat * 2.2, 0, 1))[..., None] * 0.85; out = rgb * (1 - wgt) + boosted * wgt
    pj = os.path.join(d, "proj.json")
    if fix_white and os.path.exists(pj):
        proj = json.load(open(pj))
        if k < len(proj):
            for key, q in proj[k].items():
                if not isinstance(q, dict) or "lean_left" not in q: continue
                x0, x1 = int(q["lean_left"][0]) + 6, int(q["lean_right"][0]) - 6
                hh = max(20, int((q["base"][1] - q["lean_front"][1]) * 1.1)); y0, y1 = int(q["lean_front"][1] - hh), int(q["lean_front"][1] + hh)
                y0, y1 = max(0, y0), min(out.shape[0], y1); x0, x1 = max(0, x0), min(out.shape[1], x1)
                if x1 <= x0 or y1 <= y0: continue
                reg = out[y0:y1, x0:x1]; mxr, mnr = reg.max(-1), reg.min(-1)
                m = ((mxr > 0.45) & ((mxr - mnr) / (mxr + 1e-6) < 0.2))[..., None]
                reg[:] = np.where(m, reg + (1 - reg) * 0.75, reg)
    a[..., :3] = np.clip(out * 255, 0, 255); return Image.fromarray(a.astype(np.uint8), "RGBA")


def draw_blocks3d(layer, el, t):
    """blocks3d: frames (dir of b_####.png + proj.json), in (cue: frame 0), out (cue), y (1080-space top), scale, header {text,
    y, size}, sources {lines, after (cue), x, y, max_w}: a Blender render in the top stage, its receipts small beside his head."""
    ti, to = T(el["in"]), T(el["out"])
    if t < ti or t > to + 0.6: return
    d = el["frames"]; nb = len([f for f in os.listdir(d) if f.startswith("b_")]); k = min(int((t - ti) * P.fps), nb - 1)
    if k < 0: return
    im = block_frame(d, k, el.get("fix_white", True)); ex = spring(t - to, 2.6, 0.8) if t >= to else 0.0
    s = el.get("scale", 1.10) - 0.33 * ex; y = el.get("y", 206.0) * SS + im.height / 2 - 520 * SS * ex
    for pc in el.get("pulse", []): s *= 1 + 0.045 * kick(t - T(pc), 2.6, 0.3)   # a beat on a word while the render holds
    paste(layer, im, WW / 2, y, scale=s, alpha=1 - ex)
    sw = el.get("sweep")                                       # one light sweep across the render on a word
    if sw and T(sw) - 0.08 <= t < T(sw) + 0.5:
        hw_, hh_ = im.width * s / 2, im.height * s / 2
        sweep(layer, t, T(sw), (int(max(0, WW / 2 - hw_)), int(max(0, y - hh_)), int(min(WW, WW / 2 + hw_)), int(min(WH, y + hh_))))
    hd = el.get("header")
    if hd:
        a_in = min(1.0, (t - ti - 0.08) / 0.12); p = spring(t - ti - 0.08, 3.0, 0.7)
        ho = spring(t - T(hd["out"]), 3.0, 0.8) if "out" in hd and t >= T(hd["out"]) else 0.0   # the header can leave early
        lab = text_sprite(hd["text"], hd.get("size", 46), WHITE, "ExtraBold", 6)
        paste(layer, lab[0], 540 * SS, (hd.get("y", 254) + (1 - p) * 24 - 500 * ex - 120 * ho) * SS, alpha=max(0, a_in) * (1 - ex) * (1 - ho), anchor=(0.5, lab[2] / lab[0].height))
    src = el.get("sources")
    if src and t >= T(src["after"]): draw_source_lines(layer, src, t, (1 - ex) * min(1.0, (t - T(src["after"])) / 0.2))


def draw_source_lines(layer, src, t, a):
    for i, l in enumerate(src["lines"]):
        fs_ = src.get("size", 21.0); mw = src.get("max_w", 405)
        while text_sprite(l, fs_, (235, 235, 235), "ExtraBold", 1.5, True, 0.85)[3] / SS > mw and fs_ > 15: fs_ -= 0.5
        spr = text_sprite(l, fs_, (235, 235, 235), "ExtraBold", 1.5, True, 0.85)
        paste(layer, spr[0], src.get("x", 40) * SS, (src.get("y", 884) + src.get("lh", 25) * i) * SS, alpha=a, anchor=(spr[1] / spr[0].width, spr[2] / spr[0].height))


def draw_lines(layer, el, t):
    """lines: small receipt lines (lines, x, y, size, max_w, lh) between in and out cues."""
    if t < T(el["in"]) or t > T(el["out"]) + 0.3: return
    a = min(1.0, (t - T(el["in"])) / 0.2) * (1 - lin(t, T(el["out"]), T(el["out"]) + 0.25)); draw_source_lines(layer, el, t, a)


def draw_chips(layer, el, t):
    """chips: items (labels), tw/th (chip size, th defaults to tw), gap, yc, in (cue), stagger, lit {i: cue}, outlined {i: cue},
    text_size, out {cue, dy}: a row of tiles that springs in and lights on words (the week row, 1st/2nd, months)."""
    ti = T(el["in"])
    if t < ti - 0.12 or ("out" in el and t > T(el["out"]["cue"]) + 0.5): return
    o = exit_off(el, t); items = el["items"]; tw = el.get("tw", 92); th = el.get("th", tw); gap = el.get("gap", 14)
    cols = el.get("cols", len(items))                          # cols < len(items): a grid of tiles (a 12-month calendar)
    total = cols * tw + (cols - 1) * gap; x0 = el.get("x", 540) - total / 2; yc0 = el["yc"] + el.get("out", {}).get("dy", -600) * o
    lit = {int(k): T(v) for k, v in el.get("lit", {}).items()}; opt = {int(k): T(v) for k, v in el.get("outlined", {}).items()}
    d = ImageDraw.Draw(layer, "RGBA")
    item_in = {int(k): T(v) for k, v in el.get("item_in", {}).items()}
    for i, lab in enumerate(items):
        p = spring(t - ((item_in[i] - 0.12) if i in item_in else (ti - 0.12 + el.get("stagger", 0.025) * i)), 3.2, 0.6)
        if p <= 0: continue
        s = 0.6 + 0.4 * p; cx = x0 + (i % cols) * (tw + gap) + tw / 2; yc = yc0 + (i // cols) * (th + el.get("row_gap", gap)); hw_, hh_ = tw * s / 2, th * s / 2
        on = i in lit and t >= lit[i]; maybe = i in opt and t >= opt[i]
        pop = 1 + (0.18 * kick(t - lit[i], 3.0, 0.35) if on else 0) + (0.14 * kick(t - opt[i], 3.0, 0.35) if maybe else 0)
        hw_ *= pop; hh_ *= pop; box = [(cx - hw_) * SS, (yc - hh_) * SS, (cx + hw_) * SS, (yc + hh_) * SS]
        fa = max(0.0, 1 - 2 * o) if el.get("fade_out") else 1.0
        if fa <= 0.01: continue
        if on: d.rounded_rectangle(box, radius=16 * SS, fill=YEL + (int(255 * fa),))
        else: d.rounded_rectangle(box, radius=16 * SS, fill=(12, 12, 14, int(175 * fa)), outline=(YEL + (int(255 * fa),)) if maybe else (255, 255, 255, int(80 * fa)), width=int((5 if maybe else 2) * SS))
        ch = text_sprite(lab, el.get("text_size", 50), INK if on else WHITE, "Black", el.get("track", 0), not on)
        paste(layer, ch[0], cx * SS, yc * SS - 2, scale=s * pop, alpha=min(1, p * 1.5) * (max(0.0, 1 - 2 * o) if el.get("fade_out") else 1.0), anchor=((ch[1] + ch[3] / 2) / ch[0].width, (ch[2] + el.get("text_size", 50) * 0.4 * SS) / ch[0].height))


def draw_checklist(layer, el, t):
    """checklist: rows [{text, in (cue), tick (cue)}], x, y, lh, size, out {cue, dy}: rows spring in and tick on their words."""
    rows = el["rows"]
    if t < T(rows[0]["in"]) or ("out" in el and t > T(el["out"]["cue"]) + 0.6): return
    o = exit_off(el, t); d = ImageDraw.Draw(layer, "RGBA"); size = el.get("size", 64); box = size * 0.86
    for i, r in enumerate(rows):
        ti = T(r["in"])
        if t < ti: continue
        p = spring(t - ti, 3.0, 0.62); y = el["y"] + i * el.get("lh", 104) + el.get("out", {}).get("dy", -700) * o; x = el.get("x", 130) - (1 - p) * 60
        a = min(1.0, (t - ti) / 0.08) * max(0.0, 1 - 2 * o)    # gone before it crosses the IG top band on its way out
        tk = T(r["tick"]) if "tick" in r else None; on = tk is not None and t >= tk
        pop = 1 + (0.25 * kick(t - tk, 3.0, 0.35) if on else 0)
        bx = [x * SS, (y - box / 2 * pop) * SS, (x + box * pop) * SS, (y + box / 2 * pop) * SS]
        d.rounded_rectangle(bx, radius=12 * SS, fill=(YEL + (int(255 * a),)) if on else (12, 12, 14, int(170 * a)), outline=(255, 255, 255, int(110 * a)) if not on else None, width=int(3 * SS))
        if on:
            u = spring(t - tk, 4.0, 0.7); cx0, cy0 = x + box * 0.22, y + box * 0.02; cx1, cy1 = x + box * 0.42, y + box * 0.22; cx2, cy2 = x + box * 0.80, y - box * 0.24
            pts = [(cx0, cy0), (cx1, cy1)] if u < 0.4 else [(cx0, cy0), (cx1, cy1), (mix(cx1, cx2, (u - 0.4) / 0.6), mix(cy1, cy2, (u - 0.4) / 0.6))]
            if u < 0.4: pts[1] = (mix(cx0, cx1, u / 0.4), mix(cy0, cy1, u / 0.4))
            d.line([(px * SS, py * SS) for px, py in pts], fill=INK + (int(255 * a),), width=int(10 * SS), joint="curve")
        spr = text_sprite(r["text"], size, YEL if on and el.get("lit_yellow", True) else WHITE, "Black", 4)
        paste(layer, spr[0], (x + box + 26) * SS, y * SS, alpha=a, anchor=(spr[1] / spr[0].width, (spr[2] + size * 0.36 * SS) / spr[0].height))


def draw_keyword(layer, el, t):
    """keyword: text, size, x, y, in (cue), per (s per letter), kicker {text, size, y}, pulse [cues]: the one keyword of the
    video types on letter by letter, #FFD400, beside his head (no box)."""
    ti = T(el["in"])
    if t < ti - 0.3: return
    kk = el.get("kicker")
    if kk and t >= T(kk["in"]):
        pk = spring(t - T(kk["in"]), 3.0, 0.62); spr = text_sprite(kk["text"], kk.get("size", 64), WHITE, "Black", 8)
        paste(layer, spr[0], el.get("x", 540) * SS, (kk["y"] + (1 - pk) * 24) * SS, alpha=min(1, (t - T(kk["in"])) / 0.08), anchor=(0.5, spr[2] / spr[0].height))
    L_ = letters(el["text"], el["size"], "yel"); widths = [s[3] / SS for s in L_]; gap = el.get("gap", 10); total = sum(widths) + gap * (len(L_) - 1)
    x = el.get("x", 540) - total / 2; pulse = 1.0
    for pc in el.get("pulse", []): pulse += 0.06 * kick(t - T(pc), 2.6, 0.3)
    for i, spr in enumerate(L_):
        tl = t - (ti + el.get("per", 0.1) * i)
        if tl > 0:
            p = spring(tl, 3.4, 0.5); sc = (0.3 + 0.7 * p) * pulse
            paste(layer, spr[0], (x + widths[i] / 2) * SS, (el["y"] + (1 - p) * 40) * SS, scale=sc, alpha=min(1, tl / 0.05),
                  anchor=((spr[1] + spr[3] / 2) / spr[0].width, (spr[2] + el["size"] * 0.36 * SS) / spr[0].height))
        x += widths[i] + gap


def draw_card(layer, el, t):
    """card: a receipt card (rounded dark panel, 8 px #FFD400 outline): x0, y0, x1, y1, in (cue), out {cue, dy}, kicker, title
    (lines), foot (lines), track {y, from_label, to_label, go (cue), f, d}: a study, typeset, never a screenshot."""
    ti = T(el["in"])
    if t < ti or ("out" in el and t > T(el["out"]["cue"]) + 0.6): return
    o = exit_off(el, t); p = spring(t - ti, *el.get("spring", (2.6, 0.62)))
    x0, y0, x1, y1 = el["box"]; dy = (1 - p) * 90 + el.get("out", {}).get("dy", -900) * o; sc = 0.92 + 0.08 * p
    W_, H_ = int((x1 - x0) * SS), int((y1 - y0) * SS); card = Image.new("RGBA", (W_ + 4, H_ + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([2, 2, W_ + 1, H_ + 1], radius=int(26 * SS), fill=(14, 14, 16, 232), outline=YEL + (255,), width=int(8 * SS))
    y = 34
    for ln in el.get("kicker", []):
        spr = text_sprite(ln, 30, YEL, "ExtraBold", 4, False); card.alpha_composite(spr[0], (int(40 * SS - spr[1]), int(y * SS - spr[2]))); y += 44
    y += 8
    for ln in el.get("title", []):
        spr = text_sprite(ln, el.get("title_size", 54), WHITE, "Black", 2, False); card.alpha_composite(spr[0], (int(40 * SS - spr[1]), int(y * SS - spr[2]))); y += el.get("title_size", 54) * 1.02
    y += 14
    for ln in el.get("foot", []):
        spr = text_sprite(ln, 28, (225, 225, 225), "ExtraBold", 2, False); card.alpha_composite(spr[0], (int(40 * SS - spr[1]), int(y * SS - spr[2]))); y += 38
    tr = el.get("track")
    if tr:                                                    # a time track: a dot springs from the left label to the right one
        ty = tr["y"]; lx, rx = 70, (x1 - x0) - 70; dd = ImageDraw.Draw(card)
        dd.line([lx * SS, ty * SS, rx * SS, ty * SS], fill=(255, 255, 255, 110), width=int(4 * SS))
        for xx in (lx, rx): dd.ellipse([(xx - 9) * SS, (ty - 9) * SS, (xx + 9) * SS, (ty + 9) * SS], fill=(255, 255, 255, 200))
        u = spring(t - T(tr["go"]), tr.get("f", 0.9), tr.get("d", 0.85)) if t >= T(tr["go"]) else 0.0; xd = mix(lx, rx, u)
        dd.line([lx * SS, ty * SS, xd * SS, ty * SS], fill=YEL + (255,), width=int(8 * SS)); dd.ellipse([(xd - 15) * SS, (ty - 15) * SS, (xd + 15) * SS, (ty + 15) * SS], fill=YEL + (255,))
        for lab, xx, anc in ((tr["from_label"], lx, 0.0), (tr["to_label"], rx, 1.0)):
            spr = text_sprite(lab, 30, WHITE, "ExtraBold", 3, False); card.alpha_composite(spr[0], (int(xx * SS - spr[1] - anc * spr[3]), int((ty + 26) * SS - spr[2])))
    paste(layer, drop_shadow(card, blur=18 * SS, alpha=0.55), (x0 + x1) / 2 * SS + 10, ((y0 + y1) / 2 + dy + 14) * SS, scale=sc, alpha=min(1, (t - ti) / 0.1) * (1 - o))
    paste(layer, card, (x0 + x1) / 2 * SS, ((y0 + y1) / 2 + dy) * SS, scale=sc, alpha=min(1, (t - ti) / 0.1) * (1 - o))


DRAW = {"title": draw_title, "object3d": draw_object3d, "depth_word": draw_depth_word, "text_pop": draw_text_pop, "bar": draw_bar,
        "item_label": draw_item_label, "blocks3d": draw_blocks3d, "chips": draw_chips, "checklist": draw_checklist,
        "keyword": draw_keyword, "card": draw_card, "lines": draw_lines}


def layer_of(el, t):
    if "stage_from" in el and t >= T(el["stage_from"]): return "stage"
    return el.get("layer", "stage")


# ---------------- captions ----------------
def caption_groups():
    out = [dict(w) for w in P.words()]
    lines = []                                                 # 3-word groups restart at every piece
    for w in out:
        if not lines or lines[-1][-1]["piece"] != w["piece"] or len(lines[-1]) == 3: lines.append([w])
        else: lines[-1].append(w)
    return lines


@lru_cache(maxsize=256)
def cap_sprite(word, c):
    return text_sprite(word, 64 / SS, c, "ExtraBold", 1.28 / SS)


def draw_captions(fr, t, chin_screen):
    caps = CFG["caps"]; grp = None
    for g in caps:
        if g[0]["s"] - 0.1 <= t <= g[-1]["e"] + 0.30 and (grp is None or g[0]["s"] > grp[0]["s"]): grp = g
    if not grp: return
    nxt = [g for g in caps if g[0]["s"] - 0.1 <= t and g[0]["s"] > grp[0]["s"]]
    if nxt: grp = nxt[-1]
    shown = [w for w in grp if w["s"] - 0.1 <= t]
    if not shown: return
    f = font(64, "ExtraBold"); parts = [w["w"].upper().strip(",.!?") for w in grp]
    total = f.getlength(" ".join(parts)); x = 540 - total / 2
    cc = CFG["captions"]; y = min(max(chin_screen + cc.get("below_box", 16), cc.get("y_min", 760)), cc.get("y_max", 1436))
    for i, (w, p) in enumerate(zip(grp, parts)):
        wd = f.getlength(p)
        if w in shown:
            tt = t - (w["s"] - 0.1); s = 0.78 + 0.22 * spring(tt, 4.6, 0.58); spr = cap_sprite(p, YEL if w is shown[-1] else WHITE)
            paste(fr, spr[0], x + wd / 2, y, scale=s, alpha=min(1.0, tt / 0.05), anchor=((spr[1] + spr[3] / 2) / spr[0].width, spr[2] / spr[0].height))
        x += wd + f.getlength(" ")


# ---------------- frame ----------------
@lru_cache(maxsize=1)
def vignette():
    yy, xx = np.mgrid[0:1920, 0:1080]; r = np.sqrt(((xx - 540) / 620) ** 2 + ((yy - 900) / 1150) ** 2)
    return (1 - 0.20 * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None].astype(np.float32)


def render(k):
    t = k / P.fps
    S, ox, oy = layout(t)
    rgb_w, al_w = him_layer(k, S); X0, Y0 = int(round(ox * SS)), int(round(oy * SS))
    if t < CFG["cold_until"]:                                  # cold open: his own full frame, slat wall extended above
        bg = Image.new("RGB", (WW, WH)); top = rgb_w.crop((0, 0, rgb_w.width, 46)).resize((rgb_w.width, Y0 + 60), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
        bg.paste(top, (X0, 0)); bg.paste(rgb_w, (X0, Y0))
        grad = Image.linear_gradient("L").resize((WW, int(760 * SS))).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * 0.42))
        bg.paste((0, 0, 0), (0, 0, WW, grad.height), grad)
    else:
        bg = grid_bg(t); r, blur, dim = rack(t)
        if r > 0.01:
            bg = bg.filter(ImageFilter.GaussianBlur(blur * SS * min(r, 1))); bg = Image.blend(bg, Image.new("RGB", bg.size, (6, 6, 8)), dim * min(r, 1))
        for a, b, h, st in CFG["top_grade"]:                   # darker grade under a docked title (no box)
            if a <= t < b:
                grad = Image.linear_gradient("L").resize((WW, int(h * SS))).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * st))
                bg.paste((0, 0, 0), (0, 0, WW, grad.height), grad)
    world = bg.convert("RGBA")
    depth = Image.new("RGBA", (WW, WH), (0, 0, 0, 0))
    for el in CFG["elements"]:
        if layer_of(el, t) == "depth": DRAW[el["type"]](depth, el, t)
    world.alpha_composite(depth)
    if t >= CFG["cold_until"]:                                 # his soft shadow on the grid, then him
        sh = Image.new("RGBA", rgb_w.size, (0, 0, 0, 0)); sh.putalpha(al_w.point(lambda v: int(v * 0.5)).filter(ImageFilter.GaussianBlur(20 * SS)))
        _paste_clip(world, sh, X0 + int(10 * SS), Y0 + int(18 * SS))
    cut = rgb_w.convert("RGBA"); cut.putalpha(al_w); _paste_clip(world, cut, X0, Y0)
    stage = Image.new("RGBA", (WW, WH), (0, 0, 0, 0))
    for el in CFG["elements"]:
        if layer_of(el, t) == "stage": DRAW[el["type"]](stage, el, t)
    world.alpha_composite(stage)
    z, cx, cy, zb = camera(t); ww, wh = min(WW, 1242 / z), min(WH, 2208 / z)
    x0 = min(max(cx * SS - ww / 2, 0.0), WW - ww); y0 = min(max(cy * SS - wh / 2, 0.0), WH - wh)
    fr = world.convert("RGB").resize((1080, 1920), Image.LANCZOS, box=(x0, y0, x0 + ww, y0 + wh))
    if zb > 0.02:                                              # zoom blur on a section zoom (3 scaled copies)
        acc = np.asarray(fr, np.float32)
        for zz in (1.03, 1.07):
            ww2, wh2 = ww / (1 + (zz - 1) * zb), wh / (1 + (zz - 1) * zb)
            bx0 = min(max(cx * SS - ww2 / 2, 0.0), WW - ww2); by0 = min(max(cy * SS - wh2 / 2, 0.0), WH - wh2)
            acc += np.asarray(world.convert("RGB").resize((1080, 1920), Image.BILINEAR, box=(bx0, by0, bx0 + ww2, by0 + wh2)), np.float32)
        fr = Image.fromarray((acc / 3).astype(np.uint8))
    fr = fr.convert("RGBA")
    box_bottom = oy + CFG["face"]["box_bottom"] * S * 1920; draw_captions(fr, t, (box_bottom - cy) * z + 960)
    a = np.asarray(fr.convert("RGB"), np.float32) * vignette()
    g = np.random.default_rng(k).normal(0, 2.2, (960, 540)).astype(np.float32)
    g = np.asarray(Image.fromarray(g).resize((1080, 1920), Image.BILINEAR), np.float32)[..., None]
    return Image.fromarray(np.clip(a + g, 0, 255).astype(np.uint8))


def job(k):
    render(k).save(os.path.join(P.work, "out", f"f_{k:05d}.png"), compress_level=1); return k
