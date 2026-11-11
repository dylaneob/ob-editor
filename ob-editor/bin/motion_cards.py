#!/usr/bin/env python3
"""Code-drawn motion graphics for the side panel (C4365 visceral fat, 2026-10-18). No AI imagery: every shape is drawn here.

Imported by cards.py like bowl_anim. Each type gives html(ev) for the panel's content area (2820 x 2160, scaled by
cards.SIDE_S) and js(ev) for its GSAP timeline lines. Times inside an event are seconds from the event start.

  belly  cross-section of the waist: skin, the fat under it, the muscle wall, organs, visceral fat between them.
         ev["mode"]: "intro" (labels the two fats), "tofi" (thin outside, fat inside), "mri" (a scan line sweeps it)
         ev["labels"]: [[text, anchor] or [text, anchor, "sub"|"vis"], ...]  ->  resolve_events gives labels_t
  tape   front torso outline, a tape wraps the waist, thresholds appear as he says them
         ev["rows"]: [[value, unit, label, anchor], ...]  ->  rows_t
  cycle  four steps on a loop, each arrow draws into the next step as he says it
         ev["items"]: [[text, anchor], ...] (4)  ->  items_t
  meal   one food: kicker ("Meal 2 · Lunch"), name, numbers that count up, an optional note
         ev["rows"]: [[value, label, anchor], ...]  ->  rows_t;  ev["note"]: [text, anchor]  ->  note_t
"""
import html, math, random, re

Y = "#F7DC3A"
esc = lambda s: html.escape(s or "", quote=True)

# ---------------------------------------------------------------- body figure (belly + tape share it)
# Front view, viewBox 0 0 1000 1500: head, shoulders, arms hanging, waist at y ~700 (just above the hip bones), hips, legs.
HEAD = '<circle cx="500" cy="118" r="86"/>'
TORSO = ("M455 232 C400 248 322 250 287 288 C262 316 268 382 300 470 C330 556 346 636 346 700 C346 760 322 818 332 880 "
         "C340 950 402 992 500 996 C598 992 660 950 668 880 C678 818 654 760 654 700 C654 636 670 556 700 470 "
         "C732 382 738 316 713 288 C678 250 600 248 545 232 Z")
ARMS = ("M276 300 C246 318 232 352 230 400 L216 720 C214 762 252 772 262 736 L292 446 C286 400 284 346 276 300 Z "
        "M724 300 C754 318 768 352 770 400 L784 720 C786 762 748 772 738 736 L708 446 C714 400 716 346 724 300 Z")
LEGS = ("M352 930 C350 1050 340 1250 336 1420 C336 1452 476 1452 478 1420 L496 1000 C460 998 390 980 352 930 Z "
        "M648 930 C650 1050 660 1250 664 1420 C664 1452 524 1452 522 1420 L504 1000 C540 998 610 980 648 930 Z")
NECK = '<path d="M462 196 L462 240 L538 240 L538 196 Z"/>'
VIEW = "80 20 840 1060"   # head to upper thighs: the waist fills the panel


def figure(fill="rgba(255,255,255,.08)", stroke="#fff"):
    return (f'<g fill="{fill}" stroke="{stroke}" stroke-width="9" stroke-linejoin="round">{HEAD}{NECK}'
            f'<path d="{LEGS}"/><path d="{ARMS}"/><path d="{TORSO}"/></g>')


# ---------------------------------------------------------------- belly
# Inside the waist: the fat under the skin is a pale band along the inside of the outline; the organs sit in the belly
# (liver, stomach, coiled intestines) and the visceral fat is the yellow tucked around and between them.
INTESTINE = "M392 668 H608 A34 34 0 0 1 608 736 H392 A34 34 0 0 0 392 804 H608 A34 34 0 0 1 608 872 H408"
BLOBS = [(374, 640, 30, 22), (622, 642, 28, 22), (500, 628, 34, 16), (356, 742, 26, 30), (644, 770, 26, 32), (500, 702, 40, 13),
         (500, 770, 42, 13), (360, 860, 30, 26), (640, 862, 30, 24), (470, 838, 34, 12), (560, 912, 46, 18), (440, 912, 40, 18)]
TOFI_EXTRA = [(410, 600, 34, 20), (590, 600, 34, 20), (330, 800, 22, 34), (670, 700, 22, 34), (500, 945, 60, 20)]


def belly_svg(mode):
    band = 22 if mode == "tofi" else 62                          # thickness of the fat under the skin
    sc = 1.35 if mode == "tofi" else 1.0
    blobs = BLOBS + (TOFI_EXTRA if mode == "tofi" else [])
    out = [f'<svg id="bsvg" viewBox="{VIEW}" width="1300" height="1640" style="position:absolute;left:120px;top:300px;overflow:hidden">',
           '<defs><clipPath id="btor"><path d="' + TORSO + '"/></clipPath></defs>',
           figure(),
           f'<path id="bsub" d="{TORSO}" fill="none" stroke="#f2dca4" stroke-width="{band * 2}" clip-path="url(#btor)" opacity=".92"/>',
           f'<path id="bring" d="{TORSO}" fill="none" stroke="#fff" stroke-width="{band * 2 + 14}" clip-path="url(#btor)" stroke-opacity="0"/>',
           '<g clip-path="url(#btor)">',
           '<g class="bl"><path d="M346 520 C380 490 470 488 492 520 C505 548 470 590 420 596 C380 600 348 580 346 520 Z" fill="#9c4a3c"/></g>',   # liver
           '<g class="bl"><path d="M520 520 C548 492 640 496 650 540 C658 582 610 612 566 600 C540 594 512 560 520 520 Z" fill="#d98a8a"/></g>',  # stomach
           f'<g class="bl"><path d="{INTESTINE}" fill="none" stroke="#b86a68" stroke-width="58" stroke-linecap="round" stroke-linejoin="round"/>'
           f'<path d="{INTESTINE}" fill="none" stroke="#eaa7a4" stroke-width="42" stroke-linecap="round" stroke-linejoin="round"/></g>']
    for x, y, a, b in blobs:
        out.append(f'<ellipse class="bv" cx="{x}" cy="{y}" rx="{a * sc:.0f}" ry="{b * sc:.0f}" fill="{Y}" stroke="#c9a90f" stroke-width="4"/>')
    out.append('</g>')
    out.append(f'<path d="{TORSO}" fill="none" stroke="#fff" stroke-width="9"/>')   # crisp outline back on top
    if mode == "mri":
        out.append(f'<rect id="bscan" x="150" y="380" width="700" height="34" rx="8" fill="{Y}" opacity="0"/>')
    out.append('</svg>')
    return "".join(out)


def belly_html(ev):
    mode = ev.get("mode", "intro")
    sw = {"sub": '<span style="display:inline-block;width:90px;height:90px;border-radius:24px;background:#f2dca4;margin-right:44px;flex:none"></span>',
          "vis": f'<span style="display:inline-block;width:90px;height:90px;border-radius:45px;background:{Y};margin-right:44px;flex:none"></span>'}
    title = (f'<div id="btt" class="din" style="position:absolute;left:1560px;width:1220px;top:520px;font-size:170px;line-height:1">{esc(ev["title"])}</div>'
             if ev.get("title") else "")
    kind = lambda i, lb: lb[2] if len(lb) > 2 else ("sub" if i == 0 else "vis")   # which fat the label's swatch shows
    y0 = 1080 if ev.get("title") else 820
    rows = "".join(f'<div id="bg{i}" class="avb" style="position:absolute;left:1560px;width:1220px;top:{y0 + i * 300}px;display:flex;align-items:center;'
                   f'font-size:96px;line-height:1.12;opacity:0">{sw[kind(i, lb)]}<span>{esc(lb[0])}</span></div>' for i, lb in enumerate(ev["labels"]))
    return title + belly_svg(mode) + rows


def belly_js(ev):
    mode, lt = ev.get("mode", "intro"), ev.get("labels_t") or [0.9, 1.9]
    js = ['tl.fromTo("#bsvg",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
          'tl.fromTo(".bl",{scale:.001,transformOrigin:"50% 50%"},{scale:1,duration:POP.dur,ease:POP.ease,stagger:.06},.35);']
    if ev.get("title"): js.append('tl.fromTo("#btt",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.2);')
    kinds = [lb[2] if len(lb) > 2 else ("sub" if i == 0 else "vis") for i, lb in enumerate(ev["labels"])]
    vis_t = next((t for t, k in zip(lt, kinds) if k == "vis"), lt[-1])   # the visceral fat pops on its own label
    sub_t = next((t for t, k in zip(lt, kinds) if k == "sub"), lt[0])
    if "sub" in kinds:       # the fat under the skin glows on its label
        js += [f'tl.fromTo("#bring",{{attr:{{"stroke-opacity":0}}}},{{attr:{{"stroke-opacity":.5}},duration:SOFT.dur,ease:SOFT.ease}},{sub_t:.3f});',
               f'tl.to("#bring",{{attr:{{"stroke-opacity":0}},duration:SOFT.dur,ease:SOFT.ease}},{sub_t + 0.9:.3f});']
    js.append(f'tl.fromTo(".bv",{{scale:.001,transformOrigin:"50% 50%"}},{{scale:1,duration:POP.dur,ease:POP.ease,stagger:.035}},{(vis_t if mode != "mri" else 0.45):.3f});')
    if mode == "mri":        # a scan line sweeps down the body, then the visceral fat brightens
        js += ['tl.set("#bscan",{opacity:.8},.7);', 'tl.fromTo("#bscan",{attr:{y:380}},{attr:{y:1000},duration:1.4,ease:"none"},.7);',
               'tl.to("#bscan",{opacity:0,duration:.2,ease:"none"},2.1);',
               f'tl.fromTo(".bv",{{attr:{{stroke:"#c9a90f","stroke-width":4}}}},{{attr:{{stroke:"#fff","stroke-width":10}},duration:SOFT.dur,ease:SOFT.ease}},{max(2.1, vis_t):.3f});']
    for i, t in enumerate(lt):
        js.append(f'tl.fromTo("#bg{i}",{{opacity:0,x:-36}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(t, 0.5):.3f});')
    return js


# ---------------------------------------------------------------- tape
TAPE = "M338 668 Q500 700 662 668 L664 732 Q500 764 336 732 Z"   # band around the waist, curved like it wraps


def tape_html(ev):
    rows = "".join(f'<div id="tr{i}" style="position:absolute;left:1560px;top:{800 + i * 560}px;opacity:0">'
                   f'<div class="din" style="font-size:330px;line-height:.92;color:{Y if i == 0 else "#fff"}">{esc(v)}<span style="font-size:150px"> {esc(u)}</span></div>'
                   f'<div class="avb" style="font-size:88px;color:#dcdcdc;margin-top:18px">{esc(lb)}</div></div>'
                   for i, (v, u, lb, _) in enumerate(ev["rows"]))
    title = f'<div id="tt" class="avb" style="position:absolute;left:1560px;top:470px;width:1220px;font-size:96px;line-height:1.15">{esc(ev.get("title", ""))}</div>'
    svg = (f'<svg id="tsv" viewBox="{VIEW}" width="1300" height="1640" style="position:absolute;left:120px;top:300px;overflow:hidden">'
           f'<defs><clipPath id="tcl"><rect id="tcr" x="300" y="600" width="0" height="220"/></clipPath></defs>{figure()}'
           f'<g clip-path="url(#tcl)"><path d="{TAPE}" fill="{Y}" stroke="#c9a90f" stroke-width="5"/>'
           f'<path d="M346 700 Q500 732 654 700" fill="none" stroke="#111" stroke-width="16" stroke-dasharray="3 20"/></g>'
           f'<g id="tlead" opacity="0"><path d="M668 700 L760 700" stroke="{Y}" stroke-width="8" stroke-dasharray="6 10"/>'
           f'<circle cx="668" cy="700" r="12" fill="{Y}"/></g></svg>')
    return title + svg + rows


def tape_js(ev):
    rt = ev.get("rows_t") or [0.8 + 1.2 * i for i in range(len(ev["rows"]))]
    js = ['tl.fromTo("#tsv",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
          'tl.fromTo("#tt",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.3);',
          'tl.fromTo("#tcr",{attr:{width:0}},{attr:{width:400},duration:1.0,ease:"none"},.55);',   # the tape wraps the waist
          'tl.fromTo("#tlead",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},1.5);']
    for i, t in enumerate(rt):
        js.append(f'tl.fromTo("#tr{i}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(t, 0.6):.3f});')
    return js


# ---------------------------------------------------------------- cycle
CX, CY, CR = 1410, 1060, 700
ANG = [-90, 0, 90, 180]


def _pt(a):
    r = math.radians(a); return CX + CR * math.cos(r), CY + CR * math.sin(r)


def _arc(a0, a1):
    (x0, y0), (x1, y1) = _pt(a0), _pt(a1)
    return f"M{x0:.1f} {y0:.1f} A{CR} {CR} 0 0 1 {x1:.1f} {y1:.1f}"


def cycle_html(ev):
    gap = [(38, 22), (22, 38), (38, 22), (22, 38)]   # degrees kept clear at each end so arrows meet the boxes, not overlap them
    arcs, heads = [], []
    for k in range(4):
        a0, a1 = ANG[k] + gap[k][0], ANG[(k + 1) % 4] + (360 if k == 3 else 0) - gap[k][1]
        arcs.append(f'<path id="ca{k}" d="{_arc(a0, a1)}" fill="none" stroke="{Y}" stroke-width="16" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>')
        x, y = _pt(a1); t = math.radians(a1); dx, dy = -math.sin(t), math.cos(t); nx, ny = -dy, dx
        p = [(x + dx * 46, y + dy * 46), (x - dx * 10 + nx * 34, y - dy * 10 + ny * 34), (x - dx * 10 - nx * 34, y - dy * 10 - ny * 34)]
        heads.append(f'<polygon id="ch{k}" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in p)}" fill="{Y}" opacity="0"/>')
    svg = f'<svg viewBox="0 0 2820 2160" width="2820" height="2160" style="position:absolute;left:0;top:0">{"".join(arcs)}{"".join(heads)}</svg>'
    nodes = ""
    for k, (txt, _) in enumerate(ev["items"]):
        x, y = _pt(ANG[k])
        nodes += (f'<div id="cn{k}" class="din" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;transform:translate(-50%,-50%);'
                  f'background:#fff;color:#111;border-radius:40px;padding:40px 64px;font-size:104px;line-height:1;white-space:nowrap;'
                  f'box-shadow:0 24px 70px rgba(0,0,0,.55);opacity:0">{esc(txt)}</div>')
    # above the middle row: the left and right steps sit on the centre line, and a centred title ran under them (C4365 frame QC)
    title = f'<div id="ctt" class="din" style="position:absolute;left:0;width:2820px;text-align:center;top:{CY - 330}px;font-size:170px;color:{Y};opacity:0">{esc(ev.get("title", ""))}</div>'
    return svg + nodes + title


def cycle_js(ev):
    it = ev.get("items_t") or [0.3 + 1.2 * k for k in range(4)]
    js = [f'tl.fromTo("#ctt",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ev.get("title_t", 0.3):.3f});']
    for k, t in enumerate(it):
        js.append(f'tl.fromTo("#cn{k}",{{opacity:0,scale:.8}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{max(t, 0.35):.3f});')
    for k in range(4):   # the arrow into the next step lands as that step appears; the last one closes the loop
        land = it[k + 1] if k < 3 else it[3] + 0.9
        start = max(it[k] + 0.25, land - 0.6)
        js += [f'tl.fromTo("#ca{k}",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:{max(land - start, 0.25):.3f},ease:"none"}},{start:.3f});',
               f'tl.fromTo("#ch{k}",{{opacity:0}},{{opacity:1,duration:.08,ease:"none"}},{land - 0.05:.3f});']
    return js


# ---------------------------------------------------------------- meal
NUM = re.compile(r"^(\d+)((?:\s|[A-Za-z%]).*)?$")   # "17 g", "323%": counts; "1.8 g", "~4": shown as is


def _counts(ev, i):
    """Does row i count up? Only a whole number of up to 3 digits, on a card that stays up 2 s after it lands."""
    m = NUM.match(ev["rows"][i][0].replace(",", ""))
    t = max((ev.get("rows_t") or [0.6 + 0.8 * k for k in range(len(ev["rows"]))])[i], 0.5)
    return (m if m and len(m.group(1)) <= 3 and ev.get("dur", 99) - t >= 2.0 else None), t


# ---------------------------------------------------------------- meal: food plates
# OB 2026-10-19, after watching the render: "you didnt do anything [on the foods], not even a photo of them".
# Real food photos (Pexels License: free, no credit needed; WORK/foods/dl/SOURCES.txt), cropped square (WORK/foods/crops.py)
# and shown as round plates with a white rim. Each lands on its spoken word with a spring, then the photo slowly pushes in
# and turns inside its rim. foods: [[key, label, anchor, [cx, cy, d], label_anchor?]] appear on their words;
# foods_keep: [[key, label, [cx, cy, d], [from cx, cy, d]]] carry over from the card before and glide to their new place.
# fx: ["salt" | "steam", anchor, plate index].
ENTER = [(0, -190, -9), (260, 0, 8), (0, 190, -6), (-260, 0, 7)]   # varied entrances: drop in, from the right, rise, from the left


def _slot(ev, i):
    keep = ev.get("foods_keep", [])
    return keep[i][2] if i < len(keep) else ev["foods"][i - len(keep)][3]


def _plates(ev):
    items = ev.get("foods_keep", []) + ev.get("foods", [])
    out = ""
    for i, it in enumerate(items):
        key, label = it[0], it[1]
        cx, cy, d = _slot(ev, i)
        ring = max(14, round(d * 0.028))
        pill = (f'<div id="fl{i}" class="avb" style="position:absolute;left:0;width:{d}px;top:{d - 74}px;text-align:center;opacity:0">'
                f'<span style="display:inline-block;background:#fff;color:#111;border-radius:60px;padding:20px 54px;font-size:{64 if d > 600 else 50}px;'
                f'box-shadow:0 14px 40px rgba(0,0,0,.45)">{esc(label)}</span></div>') if label else ""
        out += (f'<div id="fw{i}" style="position:absolute;left:{cx - d / 2:.0f}px;top:{cy - d / 2:.0f}px;width:{d}px;height:{d}px;opacity:0">'
                f'<div style="position:absolute;left:0;top:0;width:{d}px;height:{d}px;border-radius:50%;overflow:hidden;border:{ring}px solid #fff;'
                f'box-sizing:border-box;background:#1d1d1d;box-shadow:0 34px 90px rgba(0,0,0,.6)">'
                f'<img id="fi{i}" src="../assets/foods/{esc(key)}.jpg" style="width:100%;height:100%;object-fit:cover;display:block"/></div>{pill}</div>')
    fx = ev.get("fx")
    if fx:
        cx, cy, d = _slot(ev, fx[2])
        if fx[0] == "salt":   # coarse salt landing on the food: deterministic scatter inside the plate
            r = random.Random(5)
            for k in range(70):
                a, rr = r.uniform(0, 2 * math.pi), d * 0.36 * math.sqrt(r.random())
                x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.9
                out += (f'<div class="salt" style="position:absolute;left:{x - 7:.0f}px;top:{y - 5:.0f}px;width:{r.choice((22, 26, 30))}px;'
                        f'height:{r.choice((16, 19))}px;border-radius:5px;background:{r.choice(("#ffffff", "#f3f3f3", "#e2e2e2"))};'
                        f'box-shadow:0 2px 3px rgba(0,0,0,.35);opacity:0"></div>')
        elif fx[0] == "steam":   # three wisps rising off the top of the mug, inside the plate's top half
            for k, dx in enumerate((-0.16, 0.03, 0.2)):
                out += (f'<svg id="st{k}" viewBox="0 0 120 420" width="{d * 0.13:.0f}" height="{d * 0.44:.0f}" style="position:absolute;'
                        f'left:{cx + dx * d - d * 0.065:.0f}px;top:{cy - d * 0.5:.0f}px;opacity:0;overflow:visible">'
                        f'<path d="M60,410 C14,330 106,270 60,200 C14,130 106,80 60,12" fill="none" stroke="#ffffff" stroke-width="20" '
                        f'stroke-linecap="round" opacity=".8"/></svg>')
    return out


def _plates_js(ev):
    keep, new, D = ev.get("foods_keep", []), ev.get("foods", []), ev["dur"]
    ts = ev.get("foods_t") or [0.4 + 0.6 * k for k in range(len(new))]
    lts = ev.get("foods_label_t") or [None] * len(new)
    js = []
    for i, it in enumerate(keep):   # visible where the card before left it, then glides into this card's layout
        (cx, cy, d), (fx_, fy_, fd) = it[2], it[3]
        js += [f'tl.fromTo("#fw{i}",{{opacity:0,x:{fx_ - cx:.0f},y:{fy_ - cy:.0f},scale:{fd / d:.4f}}},{{opacity:1,duration:.14,ease:"none",immediateRender:true}},0);',
               f'tl.to("#fw{i}",{{x:0,y:0,scale:1,duration:SLIDE.dur,ease:SLIDE.ease}},.16);']
        if it[1]: js.append(f'tl.set("#fl{i}",{{opacity:1}},0);')
    for k, it in enumerate(new):
        i, t = len(keep) + k, max(ts[k], 0.12)
        if ev.get("foods_instant"):   # a short card: the plate is simply there
            js.append(f'tl.fromTo("#fw{i}",{{opacity:0,scale:.97}},{{opacity:1,scale:1,duration:.16,ease:"none",immediateRender:true}},0);')
        else:
            x0, y0, r0 = ENTER[k % len(ENTER)]
            js.append(f'tl.fromTo("#fw{i}",{{opacity:0,scale:.5,x:{x0},y:{y0},rotation:{r0}}},{{opacity:1,scale:1,x:0,y:0,rotation:0,duration:POP.dur,ease:POP.ease}},{t:.3f});')
        if it[1]:
            lt = lts[k] if lts[k] is not None else t + .35
            js.append(f'tl.fromTo("#fl{i}",{{opacity:0,y:18}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{max(lt, t + .2):.3f});')
    for i in range(len(keep) + len(new)):   # Ken Burns on the photo (child of the entrance wrapper, so no transform clash)
        js.append(f'tl.fromTo("#fi{i}",{{scale:1.0,rotation:0}},{{scale:1.1,rotation:{3 if i % 2 else -3},duration:{max(D, 1):.3f},ease:"none"}},0);')
    fx = ev.get("fx")
    if fx:
        ft = max(ev.get("fx_t", 1.5), 0.3)
        if fx[0] == "salt":
            js.append('tl.fromTo(".salt",{opacity:0,y:i => -420 - (i * 61) % 260},{opacity:1,y:0,duration:.55,ease:p => p * p,stagger:.012},' + f'{ft:.3f});')
        elif fx[0] == "steam":
            per = 1.6; n = max(1, int((D - ft) / per))
            for k in range(3):
                js.append(f'tl.fromTo("#st{k}",{{opacity:0,y:50,scaleY:.75}},{{opacity:.85,y:-40,scaleY:1.06,duration:{per:.2f},ease:"sine.inOut",repeat:{n},yoyo:true}},{ft + .32 * k:.3f});')
    return js


def meal_html(ev):
    rows = ev.get("rows", []); n = max(1, len(rows)); foods = bool(ev.get("foods") or ev.get("foods_keep")); has_ph = bool(ev.get("photo")) or foods
    top = 1560 if has_ph else 760
    big = 260 if has_ph else 400
    colw = min(1300, (2700 - 120 * (n - 1)) // n)
    cols = ""
    for i, (v, lb, _) in enumerate(rows):
        m = _counts(ev, i)[0]
        num = (f'<span id="mn{i}" class="din mcnt" style="--n:0"></span><span class="din" style="font-size:{int(big * .42)}px">{esc(m.group(2) or "")}</span>'
               if m else (lambda n, u: f'<span class="din">{esc(n)}</span><span class="din" style="font-size:{int(big * .42)}px">{(" " + esc(u)) if u else ""}</span>')(*(v.split(" ", 1) + [""])[:2]))
        cols += (f'<div id="mr{i}" style="width:{colw}px;text-align:center;opacity:0"><div class="din" style="font-size:{big}px;line-height:1;color:{Y if i == ev.get("hl_row", 0) else "#fff"}">{num}</div>'
                 f'<div class="avb" style="font-size:{76 if has_ph else 84}px;line-height:1.2;margin-top:30px;color:#e6e6e6">{esc(lb)}</div></div>')
    photo = (f'<div id="mph" style="position:absolute;left:{1410 - 800}px;top:640px;width:1600px;height:860px;border-radius:30px;overflow:hidden;'
             f'background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.55);opacity:0"><img src="../assets/photos/{esc(ev["photo"])}.jpg" '
             f'style="width:100%;height:100%;object-fit:cover"/></div>') if ev.get("photo") else _plates(ev) if foods else ""
    note = ""
    if ev.get("note"):   # with no numbers the note is the card's payload: centred and bigger
        ntop, nfs = (1650, 96) if (foods and not rows) else (1890, 84) if has_ph else (1620, 84) if rows else (980, 112)
        note = (f'<div id="mno" style="position:absolute;left:0;width:2820px;top:{ntop}px;text-align:center;opacity:0">'
                f'<span class="avb" style="display:inline-block;background:#fff;color:#111;border-radius:70px;padding:34px 80px;font-size:{nfs}px">{esc(ev["note"][0])}</span></div>')
    return (f'<style>.mcnt::before{{counter-reset:n var(--n);content:counter(n)}}</style>'
            f'<div id="mk" class="avb" style="position:absolute;left:0;width:2820px;text-align:center;top:250px;font-size:76px;letter-spacing:6px;color:{Y}">{esc(ev.get("kicker", "")).upper()}</div>'
            f'<div id="mt" class="din" style="position:absolute;left:60px;width:2700px;text-align:center;top:360px;font-size:{170 if len(ev.get("title", "")) < 24 else 140}px;line-height:1.05">{esc(ev.get("title", ""))}</div>'
            f'{photo}<div style="position:absolute;left:60px;top:{top}px;width:2700px;display:flex;justify-content:center;gap:120px">{cols}</div>{note}')


def meal_js(ev):
    rt = ev.get("rows_t") or [0.6 + 0.8 * i for i in range(len(ev.get("rows", [])))]
    js = ['tl.fromTo("#mk",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
          'tl.fromTo("#mt",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.3);']
    if ev.get("photo"): js.append('tl.fromTo("#mph",{opacity:0,scale:.92},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},.45);')
    if ev.get("foods") or ev.get("foods_keep"): js += _plates_js(ev)
    for i, (v, _, _) in enumerate(ev.get("rows", [])):
        t = max(rt[i], 0.5)
        js.append(f'tl.fromTo("#mr{i}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});')
        m = _counts(ev, i)[0]
        if m:   # the number counts up as it lands (CSS counter: seek-safe, no per-frame JS)
            cap = max(0.25, ev["dur"] - t - 0.45)   # a short card still lands on the final number before it hands off
            js.append(f'tl.fromTo("#mn{i}",{{"--n":0}},{{"--n":{int(m.group(1))},duration:Math.min(COUNT.dur*.6,{cap:.3f}),ease:COUNT.ease,snap:{{"--n":1}}}},{t:.3f});')
    if ev.get("note"):
        js.append(f'tl.fromTo("#mno",{{opacity:0,scale:.85}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{max(ev.get("note_t", 1.5), 0.6):.3f});')
    return js


HTML = {"belly": belly_html, "tape": tape_html, "cycle": cycle_html, "meal": meal_html}
JS = {"belly": belly_js, "tape": tape_js, "cycle": cycle_js, "meal": meal_js}

# ---------------------------------------------------------------- shared panel extras
DAY = ["Breakfast", "Lunch", "Snack", "Dinner", "Dessert"]


def day_tracker(at, panel_w):
    """The day of eating so far: meals already covered dimmed, the current one in yellow (sits on the panel, unscaled)."""
    k = panel_w / 2300; fs, pad, gap = int(50 * k), int(34 * k), int(22 * k)
    chips = ""
    for i, name in enumerate(DAY):
        st = (f"background:{Y};color:#111" if i == at else
              "background:rgba(255,255,255,.10);color:#a8a8a8" if i < at else "border:3px solid rgba(255,255,255,.28);color:rgba(255,255,255,.55)")
        chips += (f'<div style="display:inline-flex;align-items:center;height:{int(96 * k)}px;padding:0 {pad}px;border-radius:{int(48 * k)}px;'
                  f'margin-right:{gap}px;font-family:AvDB;font-size:{fs}px;{st}">{name}</div>')
    return f'<div id="dtr" style="position:absolute;left:{int(110 * k)}px;top:70px;white-space:nowrap">{chips}</div>'
