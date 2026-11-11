#!/usr/bin/env python3
"""Kinetic cards (OB 2026-10-30 on the C4398/C4402 previews: "your graphics and animations are boring asf"; on the now-vs-new test,
OB-EDITS/GRAPHICS-TEST-2026-10-30: "i like the bigger text an effects so much better", "the new is way better"). Loaded by cards.py
when OB_KINETIC=1; every other render is unchanged.

Measured on v1: lines were 150 px (7% of the frame) and all came in with the same fade-and-slide; charts were scaled to 0.745 inside a
black panel. Here:
  - words in Big Shoulders Display Black (the brand font, ~3x bigger), each rising out of its own mask on the spoken word;
  - the key word ("hi") slams in (scale 1.7 -> 1, blur -> sharp) with one damped shake of the frame, a soft flash and a yellow brush
    stroke drawn under it;
  - footage: every cut lands with a punch (1.14 -> 1, motion blur off in 0.14 s), then a slow push; one grade, vignette and moving
    grain over all of it, so stock and his clips read as one film;
  - words sit on the empty side of each shot (story/kinetic_sides.json from kinetic_sides.py: the subject's extent per footage
    piece); when the next shot's subject stands on that side, the words whip across at the cut;
  - charts (stat_bars, dotgrid) fill a panel whose background is his own A-roll, blurred, warm and drifting, with a faint dot grid,
    never black (memory feedback_on_screen_while_talking); values count up riding their bars, the gap between two bars is hatched;
  - chapter cards: the title huge, word by word, its last word slammed, the brush under it, the old chapter number outlined behind;
  - his hook plate: his words straight on his frame, no box (memory feedback_no_bubble_cards_brand_font).
Spring physics as in cards.py (POP/SNAP/SOFT/SLIDE/BAR); the shake is a damped spring sampled into short linear steps (seek-safe).
"""
import html, json, math, os, random, subprocess, sys

W, H = 3840, 2160; Y = "#F7DC3A"; RED = "#E53935"; PW = 2300
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
SHADOW = "text-shadow:0 22px 80px rgba(0,0,0,.85),0 0 22px rgba(0,0,0,.55)"
EM = 0.46   # Big Shoulders Display Black, width of a capital in em, with room: CLOTHES measured 0.36, WANT MY 0.41, EVERYONE DOES IT wrapped at 0.42

CSS = f"""
@font-face {{ font-family: 'BSD'; src: url('../assets/fonts/BigShouldersDisplay.ttf'); font-weight: 100 900; }}
.bsd {{ font-family: 'BSD'; font-weight: 900; text-transform: uppercase; line-height: .9; letter-spacing: 1px; text-wrap: balance; }}
.kmask {{ display: inline-block; overflow: hidden; vertical-align: top; padding: .02em .03em .06em; margin: -.02em -.03em -.06em; }}
.kwi {{ display: inline-block; }}
.kkw {{ display: inline-block; position: relative; color: {Y}; }}
.kkw svg {{ position: absolute; left: -4%; width: 108%; bottom: -.16em; height: .2em; overflow: visible; }}
.kfoot {{ position: absolute; inset: 0; filter: contrast(1.12) saturate(.84) brightness(.9); }}
.kvig {{ position: absolute; inset: 0; background: radial-gradient(ellipse 80% 75% at 50% 48%, rgba(0,0,0,0) 42%, rgba(0,0,0,.6) 100%); }}
.kgrain {{ position: absolute; left: -300px; top: -300px; width: {W + 600}px; height: {H + 600}px; background: url('../assets/grain.png');
          opacity: .14; mix-blend-mode: overlay; pointer-events: none; }}
.kflash {{ position: absolute; inset: 0; background: #fff; mix-blend-mode: soft-light; opacity: 0; pointer-events: none; }}
"""
BRUSH = ('<svg viewBox="0 0 400 40" preserveAspectRatio="none"><path d="M6,26 C80,12 170,30 250,18 S360,14 394,20" fill="none" '
         f'stroke="{Y}" stroke-width="13" stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/></svg>')
TYPES = {"reel", "stat_bars", "dotgrid", "chapter", "end", "plate", "chart_line"}
_SIDES = None


def sides_db():
    global _SIDES
    if _SIDES is None:
        p = os.environ.get("OB_KSIDES", "")
        _SIDES = json.load(open(p)) if p and os.path.exists(p) else {}
    return _SIDES


def handles(ev):
    """Kinetic versions exist for these shapes; anything else keeps its v1 renderer."""
    t = ev["type"]
    if t == "reel": return not (ev.get("face") or ev.get("split"))
    if t in ("stat_bars", "dotgrid", "chart_line"): return not (ev.get("full") or ev.get("face") or ev.get("chain_in") or ev.get("chain_out"))
    if t == "chapter": return not ev.get("map")
    return t in ("end", "plate")


def fit(text, width, top):
    """The biggest size up to `top` at which `text` fits `width` on one row, but never under 60% of top (it wraps instead)."""
    n = max(4, len(text)); return int(max(top * 0.6, min(top, width / (EM * n))))


def rows_at(text, size, width):
    words, rows, cur = text.split(), 1, 0.0
    for w in words:
        ww = EM * size * (len(w) + 1)
        if cur and cur + ww > width: rows += 1; cur = ww
        else: cur += ww
    return rows


def shake(sel, t0, amp=16.0, f=19.0, z=12.0, T=0.34, steps=14):
    if os.environ.get("OB_NO_PUSH") == "1":   # 2026-11-11 C4465 (R18/R19, OB 11-07 "Why is it so fidgety?"): no frame kicks
        return []
    js = []
    for k in range(1, steps + 1):
        t = T * k / steps; a = amp * math.exp(-z * t) * math.sin(2 * math.pi * f * t)
        js.append(f'tl.to("{sel}",{{x:{a:.1f},y:{-0.4 * a:.1f},duration:{T / steps:.4f},ease:"none"}},{t0 + T * (k - 1) / steps:.4f});')
    js.append(f'tl.set("{sel}",{{x:0,y:0}},{t0 + T:.4f});')
    return js


def grain(D, sel="#kgrain", fps=12, seed=1030):
    rnd = random.Random(seed)
    return [f'tl.set("{sel}",{{x:{rnd.randint(-280, 0)},y:{rnd.randint(-280, 0)}}},{k / fps:.3f});' for k in range(int(D * fps) + 1)]


def kline(lid, text, hi, at, size, x, y, width, align="left", stagger=0.075, slam=0.06, D=None, upper=True):
    """A line built word by word: plain words rise out of their masks; the key phrase (hi) slams in as one and gets the brush.
    Returns html, js and the time the key phrase lands."""
    words = (text.upper() if upper else text).split(); hw = [h.strip(",.?!:;") for h in ((hi or "").upper() if upper else (hi or "")).split()]
    ks = next((i for i in range(len(words)) if hw and [w.strip(",.?!:;") for w in words[i:i + len(hw)]] == hw), None)
    groups, i = [], 0
    while i < len(words):
        if ks is not None and i == ks: groups.append((" ".join(words[i:i + len(hw)]), True)); i += len(hw)
        else: groups.append((words[i], False)); i += 1
    b = (f'<div id="{lid}" class="bsd" style="position:absolute;left:{x}px;top:{y}px;width:{width}px;text-align:{align};'
         f'font-size:{size}px;{SHADOW}">')
    js, t, land = [], at, None
    cap = (D - 0.25) if D else None
    for i, (w, key) in enumerate(groups):
        wid = f"{lid}w{i}"; tt = min(t, cap) if cap else t
        if key:
            b += f'<span id="{wid}" class="kkw">{esc(w)}{BRUSH}</span> '
            js.append(f'tl.fromTo("#{wid}",{{opacity:0,scale:1.7,filter:"blur(22px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:POP.dur,ease:POP.ease}},{tt + slam:.3f});')
            js.append(f'tl.fromTo("#{wid} path",{{strokeDashoffset:100}},{{strokeDashoffset:0,duration:SOFT.dur,ease:SOFT.ease}},{tt + slam + 0.16:.3f});')
            land = land if land is not None else tt + slam + 0.05
        else:
            b += f'<span class="kmask"><span id="{wid}" class="kwi">{esc(w)}</span></span> '
            js.append(f'tl.fromTo("#{wid}",{{yPercent:112,rotate:5}},{{yPercent:0,rotate:0,duration:SNAP.dur,ease:SNAP.ease}},{tt:.3f});')
        t += stagger
    return b + "</div>", js, land


def footage(shots, D, punch=1.14):
    b, js = '<div id="kfoot" class="kfoot">', []
    for k, s in enumerate(shots):
        fx, fy = s.get("fx", 0.5), s.get("fy", 0.5); z0 = s.get("z0", 1.0)
        b += (f'<div id="ks{k}" style="position:absolute;inset:0;overflow:hidden;transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%">'
              f'<video id="kv{k}" class="media clip" src="../assets/broll/{s["b"]}.mp4" muted playsinline data-start="{s["t"]:.3f}" '
              f'data-duration="{s["d"]:.3f}" data-track-index="{k % 2}" style="position:absolute;left:0;top:0;width:100%;height:100%;'
              f'object-fit:cover;object-position:{fx * 100:.0f}% {fy * 100:.0f}%"></video></div>')
        if os.environ.get("OB_NO_PUSH") == "1":   # 2026-11-11 C4465 (R18, OB 11-07 "zooming in and out non stop"): no punch, no push
            js += ([f'tl.set("#ks{k}",{{scale:{z0:.3f}}},0);'] if z0 != 1.0 else []) + \
                  [f'tl.fromTo("#kv{k}",{{filter:"blur(14px)"}},{{filter:"blur(0px)",duration:0.14,ease:"none"}},{s["t"]:.3f});']
            continue
        js += [f'tl.fromTo("#ks{k}",{{scale:{z0 * punch:.3f}}},{{scale:{z0:.3f},duration:SNAP.dur,ease:SNAP.ease}},{s["t"]:.3f});',
               f'tl.to("#ks{k}",{{scale:{z0 * 1.045:.3f},duration:{max(0.2, s["d"] - 0.5):.3f},ease:"none"}},{s["t"] + 0.5:.3f});',
               f'tl.fromTo("#kv{k}",{{filter:"blur(14px)"}},{{filter:"blur(0px)",duration:0.14,ease:"none"}},{s["t"]:.3f});']
    return b + "</div>", js


LAYOUTS = ((2000, (0.05, 0.57), (0.43, 0.95)), (1500, (0.04, 0.43), (0.57, 0.96)), (1150, (0.03, 0.33), (0.67, 0.97)))
FACE_MARGIN = 0.05   # C4402 6:16 (gate text_face): a block clear of his face in the thumbnail sat on it 1 s later (he moves)


def pick_layout(shots):
    """(sides per shot, text width, left x, right x). The words go on the side the subject leaves free (kinetic_sides.json: the
    subject's extent x0-x1 and its faces, 0-1). The widest block whose side is clear of the body (2000 px: 6% overlap at most) and
    of every face widened by FACE_MARGIN; a face in the middle (a vertical clip) leaves only the outer thirds (1150 px)."""
    def ov(a0, a1, b0, b1): return max(0.0, min(a1, b1) - max(a0, b0))
    recs = [sides_db().get(sh["b"]) or {} for sh in shots]; fallback = None
    for tw, (la, lb), (ra, rb) in LAYOUTS:
        sd, ok, fsum = [], True, 0.0
        for r in recs:
            opts = []
            for side, (a, b) in (("left", (la, lb)), ("right", (ra, rb))):
                body = ov(r["x0"], r["x1"], a, b) if r.get("x0") is not None else 0.0
                face = sum(ov(f[0] - FACE_MARGIN, f[1] + FACE_MARGIN, a, b) for f in r.get("faces", []))
                opts.append((face, body, 0 if (side == "right") == (r.get("cx", 0.5) < 0.5) else 1, side))
            face, body, _, side = min(opts)
            sd.append(side); fsum += face
            if face > 0 or (tw == 2000 and body > 0.06): ok = False
        if ok: return sd, tw, int(la * W), int(ra * W)
        if fallback is None or fsum < fallback[0]: fallback = (fsum, sd, tw, int(la * W), int(ra * W))
    return fallback[1], fallback[2], fallback[3], fallback[4]


def reel(ev, mock, aroll_html=""):
    D = ev["dur"]; shots = ev.get("shots", [])
    sd, TW, XL, XR = pick_layout(shots) if shots else (["left"], 2000, 200, W - 2200)
    if ev.get("ob_pip"):   # 2026-11-11 C4465 (M87): he sits in the box at the bottom right, so the words keep to the left
        sd = ["left"] * max(1, len(shots)); TW = min(TW, 2000); XL = 200
    fb, fj = footage(shots, D)
    first = sd[0]
    b = f'<div id="kcam" style="position:absolute;inset:0">{fb}<div class="kvig"></div>'
    js = list(fj)
    for side in ("left", "right"):
        g = (f"linear-gradient({'90deg' if side == 'left' else '270deg'},rgba(0,0,0,.7),rgba(0,0,0,.38) 45%,rgba(0,0,0,0) 78%)")
        b += f'<div id="kb{side[0]}" style="position:absolute;top:0;{side}:0;width:2900px;height:{H}px;background:{g};opacity:0"></div>'
    js.append(f'tl.fromTo("#kb{first[0]}",{{opacity:0}},{{opacity:1,duration:.25,ease:"none"}},0);')
    # the words: one block, its height measured from the sizes, centred vertically
    parts, y = [], 0
    if ev.get("kicker"): parts.append(("kicker", y)); y += 150
    bg = ev.get("big")
    if bg:
        num = f'{bg.get("pre", "")}{bg["text"]}'
        bsz = fit(num + " " + str(bg.get("unit", "")), TW, {2000: 620, 1500: 520, 1150: 430}.get(TW, 520)); parts.append(("big", y, bsz)); y += int(bsz * 0.95) + 40
        if bg.get("sub"):
            ssz = fit(bg["sub"], TW, 190); r_ = rows_at(bg["sub"].upper(), ssz, TW); parts.append(("sub", y, ssz)); y += int(ssz * 0.95 * r_) + 30
    for k, ln in enumerate(ev.get("lines", [])):
        top = (460 if (k == 0 and not bg) else 280) * {2000: 1.0, 1500: 0.85, 1150: 0.72}.get(TW, 0.85)
        sz = fit(ln["text"], TW, top); r_ = rows_at(ln["text"].upper(), sz, TW)
        parts.append(("line", y, sz, k)); y += int(sz * 0.93 * r_) + 34
    y0 = max(150, int((H - y) / 2) - 40) if "ly" not in ev else max(150, min(int((H - y) / 2) - 40, ev["ly"] + 200))
    tx = XL if first == "left" else XR
    b += f'<div id="ktx" style="position:absolute;left:{tx}px;top:{y0}px;width:{TW}px;height:{y + 60}px">'
    lands = []
    for p in parts:
        if p[0] == "kicker":
            b += (f'<div id="kk" class="bsd" style="position:absolute;left:0;top:{p[1]}px;font-weight:700;font-size:96px;letter-spacing:10px;color:{Y};{SHADOW};opacity:0">'
                  f'{esc(ev["kicker"]).upper()}</div>')
            js.append('tl.fromTo("#kk",{opacity:0,letterSpacing:"34px"},{opacity:1,letterSpacing:"10px",duration:SOFT.dur,ease:SOFT.ease},.08);')
        elif p[0] == "big":
            txt = str(bg["text"]); digits = txt.replace(",", "")
            dec = len(digits.split(".")[1]) if "." in digits else 0
            countable = digits.replace(".", "").isdigit() and bg.get("count", True)
            whole = digits.split(".")[0]
            numhtml = (f'<span id="kbn">0</span>{("." + digits.split(".")[1]) if dec else ""}' if countable else esc(txt))
            b += (f'<div id="kbig" class="bsd" style="position:absolute;left:0;top:{p[1]}px;font-size:{p[2]}px;{SHADOW};opacity:0">'
                  f'{esc(bg.get("pre", ""))}{numhtml}<span style="font-size:.42em;color:{Y};margin-left:.12em">{esc(bg.get("unit", ""))}</span>'
                  f'<svg style="position:absolute;left:0;width:60%;bottom:-.08em;height:.09em;overflow:visible" viewBox="0 0 400 40" preserveAspectRatio="none">'
                  f'<path d="M6,26 C80,12 170,30 250,18 S360,14 394,20" fill="none" stroke="{Y}" stroke-width="13" stroke-linecap="round" pathLength="100" '
                  f'stroke-dasharray="100" stroke-dashoffset="100"/></svg></div>')
            t0 = min(max(bg.get("at", 0.2), 0.05), max(D - 0.8, 0.05))
            js += [f'tl.fromTo("#kbig",{{opacity:0,scale:1.45,filter:"blur(20px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:POP.dur,ease:POP.ease}},{t0:.3f});',
                   f'tl.fromTo("#kbig path",{{strokeDashoffset:100}},{{strokeDashoffset:0,duration:SOFT.dur,ease:SOFT.ease}},{t0 + 0.3:.3f});']
            if countable:
                js.append(f'tl.fromTo("#kbn",{{innerText:0}},{{innerText:{int(whole)},snap:{{innerText:1}},duration:COUNT.dur,ease:COUNT.ease,immediateRender:false}},{t0:.3f});')
            lands.append(t0 + 0.05)
        elif p[0] == "sub":
            lb, lj, ld = kline("ksub", bg["sub"], bg.get("hi"), min(bg.get("at", 0.2) + 0.45, max(D - 0.6, 0.1)), p[2], 0, p[1], TW, D=D)
            b += lb; js += lj
            if ld is not None: lands.append(ld)
        else:
            ln = ev["lines"][p[3]]
            lb, lj, ld = kline(f"kl{p[3]}", ln["text"], ln.get("hi"), min(max(ln.get("at", 0.2), 0.05), max(D - 0.5, 0.05)), p[2], 0, p[1], TW, D=D)
            b += lb; js += lj
            if ld is not None: lands.append(ld)
    b += "</div>"
    # one hit per landing, at least 0.6 s apart
    last = -9.0
    for t in sorted(lands):
        if t - last >= 0.6 and t < D - 0.2:
            js += shake("#kcam", t + 0.02) + [f'tl.fromTo("#kfl",{{opacity:.5}},{{opacity:0,duration:.22,ease:"none"}},{t:.3f});']; last = t
    # the words whip to the other side at a cut where the next shot's subject stands under them
    cur = first
    for k, s in enumerate(shots[1:], 1):
        if sd[k] != cur:
            nx = (XL if sd[k] == "left" else XR) - tx
            js += [f'tl.to("#ktx",{{x:{nx},duration:SNAP.dur,ease:SNAP.ease}},{max(s["t"] - 0.06, 0):.3f});',
                   f'tl.fromTo("#ktx",{{filter:"blur(0px)"}},{{filter:"blur(12px)",duration:.08,ease:"none",yoyo:true,repeat:1}},{max(s["t"] - 0.06, 0):.3f});',
                   f'tl.to("#kb{cur[0]}",{{opacity:0,duration:.2,ease:"none"}},{s["t"]:.3f});',
                   f'tl.to("#kb{sd[k][0]}",{{opacity:1,duration:.2,ease:"none"}},{s["t"]:.3f});']
            cur = sd[k]
    b += '<div id="kfl" class="kflash"></div></div><div id="kgrain" class="kgrain"></div>'
    return b, js + grain(D)


def warm_panel(ev, mock, width=PW):
    """His studio, blurred, warm and drifting, with a faint dot grid: the panel behind a chart (never black)."""
    D = ev["dur"]
    proj = sys.argv[2] if len(sys.argv) > 2 and os.path.isdir(sys.argv[2]) else None   # cards.py EVENTS.json HF_DIR
    arp = f"{proj}/assets/aroll/{ev['id']}.mp4" if proj else ""; still = f"{proj}/assets/stills/kw_{ev['id']}.jpg" if proj else ""
    if not mock and arp and os.path.exists(arp):   # one frame of his A-roll, small (the blur hides detail): no second video to decode
        os.makedirs(os.path.dirname(still), exist_ok=True)
        if not os.path.exists(still) or os.path.getmtime(still) < os.path.getmtime(arp):
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{min(1.0, D / 2):.2f}", "-i", arp, "-frames:v", "1",
                            "-vf", "scale=960:-2", still], check=False)
    if not mock and still and os.path.exists(still):
        src = f'<img src="../assets/stills/kw_{ev["id"]}.jpg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover"/>'
    else:
        src = (f'<img class="media" src="{ev.get("mock_still") or "../assets/stills/" + ev["id"] + ".jpg"}" style="width:100%;height:100%;object-fit:cover"/>' if mock else
               f'<video class="media clip" src="../assets/aroll/{ev["id"]}.mp4" muted playsinline data-start="0" data-duration="{D:.3f}" data-track-index="1" '
               'style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover"></video>')
    b = (f'<div id="kpb" style="position:absolute;left:-200px;top:-200px;width:{W + 400}px;height:{H + 400}px">'
         f'<div style="position:absolute;left:0;top:0;width:{(W + 400) // 4}px;height:{(H + 400) // 4}px;transform:scale(4);transform-origin:0 0;'
         f'filter:blur(11.5px) brightness(.66) saturate(1.3)">{src}</div></div>'
         '<div style="position:absolute;inset:0;background:linear-gradient(100deg,rgba(14,10,6,.55),rgba(14,10,6,.28) 75%,rgba(14,10,6,.12))"></div>'
         '<div style="position:absolute;inset:0;opacity:.16;background-image:radial-gradient(rgba(255,255,255,.9) 2.2px,transparent 2.6px);background-size:46px 46px"></div>'
         '<div class="kvig"></div>')
    if os.environ.get("OB_NO_PUSH") == "1":   # OB 11-07 "zooming in and out non stop": no push on backgrounds (memory feedback_no_zoom_in_out); the pan stays
        return b, [f'tl.fromTo("#kpb",{{x:0}},{{x:-160,duration:{D:.3f},ease:"none"}},0);']
    return b, [f'tl.fromTo("#kpb",{{x:0,scale:1}},{{x:-160,scale:1.08,duration:{D:.3f},ease:"none"}},0);']


def side_frame(ev, mock, aroll_html, inner, inner_js):
    """OB slides right, the warm panel slides in on the left with the content; both go back at the end (as cards.py's side cards)."""
    D = ev["dur"]; pb, pj = warm_panel(ev, mock)
    b = (f'<div class="bg"></div><div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll_html}</div>'
         f'<div id="panel" style="position:absolute;left:0;top:0;width:{PW}px;height:{H}px;overflow:hidden;box-shadow:40px 0 120px rgba(0,0,0,.7)">'
         f'{pb}<div id="pcam" style="position:absolute;inset:0;transform-origin:30% 50%">{inner}</div></div><div id="kgrain" class="kgrain"></div>')
    js = ['tl.fromTo("#vid",{x:0},{x:1150,duration:SLIDE.dur,ease:SLIDE.ease},0);',
          f'tl.fromTo("#panel",{{x:-{PW}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);',
          (f'tl.fromTo("#pcam",{{scale:1}},{{scale:1.035,duration:{D:.3f},ease:"none"}},0);' if os.environ.get("OB_NO_PUSH") != "1" else 'void 0;')] + pj + inner_js
    if D > 1.6:
        js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.52:.3f});', f'tl.to("#panel",{{x:-{PW},duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.52:.3f});']
    return b, js + grain(D)


def title_rows(title, X0, top, size=230, at=0.22, D=None):
    """A chart title in two balanced rows, word by word."""
    words = title.upper().split(); half = (len(words) + 1) // 2
    rows = [" ".join(words[:half]), " ".join(words[half:])] if len(" ".join(words)) > 18 else [" ".join(words)]
    sz = min(size, fit(max(rows, key=len), PW - 2 * X0, size))
    b, js = "", []
    for r, row in enumerate(rows):
        lb, lj, _ = kline(f"kt{r}", row, "", at + r * 0.16, sz, X0, top + r * int(sz * 0.94), PW - 2 * X0, D=D); b += lb; js += lj
    return b, js, top + len(rows) * int(sz * 0.94)


def source_line(ev, X0):
    return (f'<div class="av" style="position:absolute;left:{X0}px;top:1990px;width:{PW - 2 * X0}px;font-size:46px;line-height:1.25;color:#a39a8e">'
            f'{esc(ev.get("source", ""))}</div>') if ev.get("source") else ""


def bars(ev, mock, aroll_html):
    D = ev["dur"]; X0 = 170; BMAX = 1450; ts = ev.get("bars_t") or [0.2 + i * 0.9 for i in range(len(ev["bars"]))]
    vals = [v for _, v, *_ in ev["bars"]]; top = max(vals)
    inner, js = "", []
    yb = 250
    if ev.get("title"):
        tb, tj, yb = title_rows(ev["title"], X0, 210, D=D); inner += tb; js += tj; yb += 60
    n = len(ev["bars"]); step = min(390, int((1900 - yb) / max(n, 1)))
    colors = [Y] + ["#f4f4f4"] * (n - 2) + ["#8a8a8a"] if n > 2 else [Y, "#f4f4f4"][:n]
    ends = []
    for i, (label, v, txt, *_) in enumerate(ev["bars"]):
        y = yb + i * step; bw = max(40, int(BMAX * v / top)); t = max(ts[i] if i < len(ts) else 0.2 + i, 0.2)
        num = txt.rstrip("%"); dec = len(num.split(".")[1]) if "." in num else 0; whole = num.split(".")[0]
        countable = whole.replace(",", "").isdigit()
        val = (f'<span id="kbn{i}">0</span>{("." + num.split(".")[1]) if dec else ""}{"%" if txt.endswith("%") else ""}' if countable else esc(txt))
        glow = "box-shadow:0 0 70px rgba(247,220,58,.35);" if i == 0 else ""
        inner += (f'<div id="kbl{i}" class="avb" style="position:absolute;left:{X0}px;top:{y}px;font-size:92px;color:#ececec;{SHADOW};opacity:0">{esc(label)}</div>'
                  f'<div id="kbar{i}" style="position:absolute;left:{X0}px;top:{y + 112}px;width:{bw}px;height:150px;border-radius:14px;background:{colors[i]};'
                  f'{glow}transform-origin:left center;transform:scaleX(0)"></div>'
                  f'<div id="kbv{i}" class="bsd" style="position:absolute;left:{X0 + bw + 44}px;top:{y + 80}px;font-size:236px;{SHADOW};'
                  f'color:{Y if i == 0 else "#fff"};opacity:0">{val}</div>')
        js += [f'tl.fromTo("#kbl{i}",{{opacity:0,x:-50}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(0.05, t - 0.45):.3f});',
               f'tl.fromTo("#kbar{i}",{{scaleX:0}},{{scaleX:1,duration:BAR.dur,ease:BAR.ease}},{t:.3f});',
               f'tl.fromTo("#kbv{i}",{{x:-{bw},opacity:0}},{{x:0,opacity:1,duration:BAR.dur,ease:BAR.ease}},{t:.3f});']
        if countable:
            js.append(f'tl.fromTo("#kbn{i}",{{innerText:0}},{{innerText:{int(whole.replace(",", ""))},snap:{{innerText:1}},duration:BAR.dur,ease:BAR.ease,immediateRender:false}},{t:.3f});')
        js += shake("#pcam", t + 0.55, amp=10.0)
        ends.append((X0 + bw, y))
    if n >= 2 and vals[1] < vals[0]:   # the part of the first bar the second doesn't reach, hatched once both have landed
        (x0e, y0_), (x1e, _) = ends[0], ends[1]; tg = (ts[1] if len(ts) > 1 else 1.2) + 1.1
        if tg < D - 0.8 and x0e - x1e > 30:
            inner += (f'<div id="kgap" style="position:absolute;left:{x1e}px;top:{y0_ + 112}px;width:{x0e - x1e}px;height:150px;border-radius:0 14px 14px 0;'
                      f'background:repeating-linear-gradient(135deg,rgba(229,57,53,.95) 0 22px,rgba(229,57,53,.55) 22px 44px);transform-origin:left center;transform:scaleX(0)"></div>')
            js.append(f'tl.fromTo("#kgap",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{tg:.3f});')
    inner += source_line(ev, X0)
    return side_frame(ev, mock, aroll_html, inner, js)


def dotgrid(ev, mock, aroll_html):
    """Dot rows that fill the panel: each row's dots as big as the width and the shared height allow (a row of 7 days gets fat
    dots, a row of 100 a 5 x 20 block), the whole stack centred under the title. Dots pop in, the counted ones light up in the
    row's colour, the value slams in and counts."""
    D = ev["dur"]; X0 = 160; rows = ev["rows"]; rt = ev.get("rows_t") or [0.3 + i * 1.0 for i in range(len(rows))]
    inner, js = "", []; top = 230
    if ev.get("title"):
        tb, tj, top = title_rows(ev["title"], X0, 190, size=210, D=D); inner += tb; js += tj; top += 40
    bot = 1930; per = (bot - top) / max(len(rows), 1); LAB, GAPV = 96 + 24, 70
    plan = []
    for r in rows:
        n = r["n"]; cols = n if n <= 20 else 20; nr = -(-n // cols)
        vsz = 220 if n > 20 else 200; vw = EM * vsz * max(3, len(str(r.get("text", ""))))
        sw = (PW - 2 * X0 - 50 - vw) / (cols + (cols - 1) * 0.3)
        sh = (per - LAB - GAPV) / (nr + (nr - 1) * 0.3)
        size = int(max(26, min(sw, sh, 200 if n <= 10 else (130 if n <= 20 else 70))))
        gap = int(size * 0.3); blockh = nr * size + (nr - 1) * gap
        plan.append((n, cols, nr, size, gap, blockh, vsz))
    total = sum(LAB + p[5] for p in plan) + GAPV * (len(plan) - 1)
    y = int(top + max(0, (bot - top - total) / 2))
    for i, (r, (n, cols, nr, size, gap, blockh, vsz)) in enumerate(zip(rows, plan)):
        k = r["k"]; bw = cols * size + (cols - 1) * gap; f0 = r.get("from", 0); col = r.get("color", Y)
        shape = "border-radius:50% 50% 46% 46%" if r.get("shape") == "person" else "border-radius:50%"
        dots = "".join(f'<div class="kd{i}{" kdh" + str(i) if f0 <= j < f0 + k else ""}" style="width:{size}px;height:{size}px;{shape};'
                       f'background:rgba(255,255,255,.22);transform:scale(0)"></div>' for j in range(n))
        txt = str(r.get("text", "")); m_ = __import__("re").match(r"^(\D*)(\d+)(.*)$", txt)
        val = (f'{esc(m_.group(1))}<span id="kdn{i}">0</span>{esc(m_.group(3))}' if m_ else esc(txt))
        inner += (f'<div style="position:absolute;left:{X0}px;top:{y}px;width:{PW - 2 * X0}px">'
                  f'<div id="kdl{i}" class="avb" style="font-size:88px;color:#ececec;{SHADOW};opacity:0">{esc(r["label"])}</div>'
                  f'<div style="display:flex;align-items:center;gap:50px;margin-top:24px">'
                  f'<div style="display:grid;grid-template-columns:repeat({cols},{size}px);gap:{gap}px;width:{bw}px">{dots}</div>'
                  f'<div id="kdv{i}" class="bsd" style="font-size:{vsz}px;color:{col};{SHADOW};opacity:0;white-space:nowrap">{val}</div></div></div>')
        t0 = max((rt[i] if i < len(rt) else 0.3 + i) - 0.5, 0.15); each = min(0.03, 0.6 / max(n, 1)); lit = t0 + 0.3 + n * each
        js += [f'tl.fromTo("#kdl{i}",{{opacity:0,x:-50}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{t0:.3f});',
               f'tl.to(".kd{i}",{{scale:1,duration:SNAP.dur,ease:SNAP.ease,stagger:{each:.4f}}},{t0 + 0.05:.3f});',
               f'tl.to(".kdh{i}",{{backgroundColor:"{col}",duration:.2,ease:"none",stagger:{min(0.04, 0.55 / max(k, 1)):.4f}}},{lit:.3f});',
               f'tl.fromTo("#kdv{i}",{{opacity:0,scale:1.5,filter:"blur(16px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:POP.dur,ease:POP.ease}},{lit:.3f});']
        if m_:
            js.append(f'tl.fromTo("#kdn{i}",{{innerText:0}},{{innerText:{int(m_.group(2))},snap:{{innerText:1}},duration:{min(0.04, 0.55 / max(k, 1)) * max(k, 1) + 0.2:.3f},ease:"none",immediateRender:false}},{lit:.3f});')
        js += shake("#pcam", lit + 0.05, amp=9.0)
        y += LAB + blockh + GAPV
    inner += source_line(ev, X0)
    return side_frame(ev, mock, aroll_html, inner, js)


def chapter(ev, mock):
    """The chapter title huge, word by word, its last word slammed with the brush; the kicker's letters close in; the chapter
    number outlined behind, drifting. Starts with the flat .bg so stage.dress lays the chapter's own wash and grain under it."""
    D = ev["dur"]; n = ev.get("n", 1); title = ev["title"]; kick = ev.get("kicker", f"PART {n}")
    size = fit(title, 3100, 560); r_ = rows_at(title.upper(), size, 3100); th = int(size * 0.92 * r_)
    ty = int(H / 2 - th / 2) + 60
    words = title.split(); hi = words[-1] if len(words) > 1 else title
    b = (f'<div class="bg"></div>'
         f'<div id="kcbig" class="bsd" style="position:absolute;right:140px;top:{H // 2 - 900}px;font-size:1700px;line-height:1;color:transparent;'
         f'-webkit-text-stroke:6px rgba(255,255,255,.55);opacity:0">{n:02d}</div>'
         f'<div id="kcam" style="position:absolute;inset:0">'
         f'<div id="kck" class="bsd" style="position:absolute;left:0;width:{W}px;top:{ty - 190}px;text-align:center;font-weight:700;font-size:110px;'
         f'letter-spacing:16px;color:{Y};{SHADOW};opacity:0">{esc(kick).upper()}</div>')
    lb, lj, land = kline("kct", title, hi, 0.12, size, (W - 3100) // 2, ty, 3100, align="center", stagger=0.09)
    b += lb + '<div id="kfl" class="kflash"></div></div>'
    js = [f'tl.fromTo("#kcbig",{{opacity:0,x:260}},{{opacity:.16,x:120,duration:SOFT.dur,ease:SOFT.ease}},0);',
          f'tl.to("#kcbig",{{x:-120,duration:{max(D - 0.6, 0.4):.3f},ease:"none"}},.6);',
          'tl.fromTo("#kck",{opacity:0,letterSpacing:"48px"},{opacity:1,letterSpacing:"16px",duration:SOFT.dur,ease:SOFT.ease},0);'] + lj
    if land is not None and land < D - 0.25:
        js += shake("#kcam", land + 0.02, amp=18.0) + [f'tl.fromTo("#kfl",{{opacity:.55}},{{opacity:0,duration:.22,ease:"none"}},{land:.3f});']
    return b, js


def end(ev, mock, aroll_html):
    """The call to action beside him: the title word by word, the line and the link under it, laid out from the title's rows."""
    D = ev["dur"]; X0 = 200; TWd = PW - 2 * X0
    tsz = fit(ev["title"], TWd, 330); tr = rows_at(ev["title"].upper(), tsz, TWd); th = int(tsz * 0.92 * tr)
    y0 = int((H - (th + 60 + 120 + 200)) / 2) - 60
    inner = f'<div style="position:absolute;left:{X0}px;top:{y0 - 60}px;width:160px;height:14px;background:{Y}"></div>'
    lb, lj, _ = kline("ket", ev["title"], "", 0.2, tsz, X0, y0, TWd, D=D)
    inner += lb; yl = y0 + th + 70
    inner += (f'<div id="kel" class="avb" style="position:absolute;left:{X0}px;top:{yl}px;width:{TWd}px;font-size:92px;line-height:1.2;{SHADOW};opacity:0">{esc(ev.get("line", ""))}</div>'
              f'<div id="keu" class="avb" style="position:absolute;left:{X0}px;top:{yl + 250}px;width:{TWd}px;font-size:70px;color:{Y};{SHADOW};opacity:0">{esc(ev.get("small") or ev.get("url", ""))}</div>')
    js = lj + ['tl.fromTo("#kel",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.75);',
               'tl.fromTo("#keu",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},1.0);']
    b, js = side_frame(ev, mock, aroll_html, inner, js)
    if D > 1.6:   # the call to action stays up to the end: no slide-out
        js = [j for j in js if not (j.startswith('tl.to("#vid"') or j.startswith('tl.to("#panel"'))]
    return b, js


KB_X, KB_W, KB_BASE = 100, 3640, 1960   # the kinetic bar: one row, its glyph bottoms ~1960 (clear of the player bar), its top clear of his face


def kbar(ev, mock, aroll_html):
    """2026-11-11 C4465 round 2 (gfx_kind, R03): the C4398 kinetic bar for his own words. ev["kchunks"]: runs of his words, each
    [{"text", "size" (470-640 px), "t" (s), "words": [[WORD, t_on, t_off], ...], "key": [i, j] or None}], times relative to the
    event. One row in the lower band over his sharp moving A-roll (no box, no panel, a light shade only); each word rises out of
    its mask on the moment he says it; the key word slams in yellow with the brush stroke; a run leaves as the next one starts."""
    D = ev["dur"]; ch = ev["kchunks"]
    b = f'<div id="kcam" style="position:absolute;inset:0">{aroll_html}'
    b += ('<div style="position:absolute;left:0;top:1260px;width:100%;height:900px;'
          'background:linear-gradient(0deg,rgba(0,0,0,.38),rgba(0,0,0,0))"></div>')
    js = []
    for k, c in enumerate(ch):
        sz = int(c["size"]); top = KB_BASE - sz; ws = c["words"]; key = c.get("key")   # rendered glyph bottom ~ top + 1.0 em (mock 11-11)
        b += (f'<div id="kb{k}" class="bsd" style="position:absolute;left:{KB_X}px;top:{top}px;width:{KB_W}px;text-align:center;'
              f'white-space:nowrap;font-size:{sz}px;opacity:0;{SHADOW}">')
        js.append(f'tl.set("#kb{k}",{{opacity:1}},{max(0.0, min(ws[0][1] - 0.05, D - 0.3)):.3f});')   # a run is not on screen before its first word
        i = 0
        while i < len(ws):
            wid = f"kb{k}w{i}"; t = max(0.0, min(ws[i][1] - 0.04, D - 0.3))
            if key and i == key[0]:
                txt = " ".join(w[0] for w in ws[key[0]:key[1]])
                b += f'<span id="{wid}" class="kkw">{esc(txt)}{BRUSH}</span> '
                js.append(f'tl.fromTo("#{wid}",{{opacity:0,scale:1.7,filter:"blur(22px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:POP.dur,ease:POP.ease}},{t:.3f});')
                js.append(f'tl.fromTo("#{wid} path",{{strokeDashoffset:100}},{{strokeDashoffset:0,duration:SOFT.dur,ease:SOFT.ease}},{t + 0.16:.3f});')
                i = key[1]; continue
            b += f'<span class="kmask"><span id="{wid}" class="kwi">{esc(ws[i][0])}</span></span> '
            js.append(f'tl.fromTo("#{wid}",{{yPercent:112,rotate:5}},{{yPercent:0,rotate:0,duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});')
            i += 1
        b += "</div>"
        nxt = ch[k + 1]["words"][0][1] - 0.04 if k + 1 < len(ch) else None
        out = (nxt - 0.14) if nxt is not None else (D - 0.24)
        js.append(f'tl.to("#kb{k}",{{opacity:0,yPercent:-12,duration:{0.14 if nxt is not None else 0.2},ease:"none"}},{max(out, ws[0][1] + 0.12):.3f});')
    b += '</div><div id="kgrain" class="kgrain"></div>'
    return b, js + grain(D)


def plate(ev, mock, aroll_html):
    """His hook words straight on his frame (no box), lower third, centred: one chunk at a time, its yellow word slammed."""
    if ev.get("kchunks"): return kbar(ev, mock, aroll_html)
    D = ev["dur"]; at = ev.get("at_t") or {}; ch = ev["chunks"]; ts, last = [], -1.0
    for k, c in enumerate(ch):
        r = at.get(c[1], 0.05 if k == 0 else last + 0.7)
        if k == 0: r = min(r, 0.05)
        if k and r < last + 0.3: r = last + 0.3
        ts.append(round(min(r, max(D - 0.35, 0.0)), 3)); last = ts[-1]
    b = f'<div id="kcam" style="position:absolute;inset:0">{aroll_html}'
    b += ('<div style="position:absolute;left:0;top:1250px;width:100%;height:910px;'
          'background:linear-gradient(0deg,rgba(0,0,0,.55),rgba(0,0,0,0))"></div>')
    js, lands = [], []
    y = ev.get("y", 1640) - 120
    for k, (txt, key, yw) in enumerate(ch):
        sz = fit(txt, 3000, 300)
        lb, lj, land = kline(f"kp{k}", txt, yw, ts[k], sz, 420, y, 3000, align="center", D=D)
        b += lb; js += lj
        if land is not None: lands.append(land)
        if k + 1 < len(ts): js.append(f'tl.to("#kp{k}",{{opacity:0,yPercent:-12,duration:.14,ease:"none"}},{max(ts[k + 1] - 0.14, ts[k] + 0.2):.3f});')
    b += '<div id="kfl" class="kflash"></div></div><div id="kgrain" class="kgrain"></div>'
    lastt = -9.0
    for t in lands:
        if t - lastt >= 0.6 and t < D - 0.2: js += shake("#kcam", t + 0.02, amp=12.0); lastt = t
    return b, js + grain(D)


def chart_line(ev, mock, aroll_html):
    """A line chart that fills the warm panel: the title word by word, a thick yellow line drawn at constant speed, each point
    popping as the line reaches it, the lowest value slammed beside its point, callouts that land inside the card."""
    D = ev["dur"]; c = ev["chart"]; X0 = 160
    tb, tj, ty = title_rows(c["title"], X0, 170, size=190, D=D)
    x0, x1, y1, y0 = X0 + 190, PW - 200, ty + 110, 1760
    X = lambda v: x0 + (v - c["xmin"]) / (c["xmax"] - c["xmin"]) * (x1 - x0)
    Yp = lambda v: y0 - (v - c["ymin"]) / (c["ymax"] - c["ymin"]) * (y0 - y1)
    u = c.get("unit", "")
    grid = "".join(f'<line x1="{x0}" y1="{Yp(g):.0f}" x2="{x1}" y2="{Yp(g):.0f}" stroke="rgba(255,255,255,.14)" stroke-width="3"/>'
                   f'<text x="{x0 - 30}" y="{Yp(g) + 20:.0f}" text-anchor="end" font-family="AvDB" font-size="58" fill="#d8d0c4">{g}{u}</text>' for g in c["yticks"])
    xy = [(X(x), Yp(y)) for x, y in c["points"]]
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in xy)
    dots = "".join(f'<circle id="kcd{i}" cx="{a:.1f}" cy="{b:.1f}" r="22" fill="{Y}" style="transform-box:fill-box;transform-origin:center"/>' for i, (a, b) in enumerate(xy))
    lo = min(range(len(xy)), key=lambda i: c["points"][i][1]); lv = c["points"][lo][1]
    inner = tb + (f'<svg style="position:absolute;left:0;top:0;width:{PW}px;height:{H}px;overflow:visible">{grid}'
                  f'<polyline id="kcl" points="{pts}" fill="none" stroke="{Y}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" '
                  f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" style="filter:drop-shadow(0 0 18px rgba(247,220,58,.45))"/>{dots}</svg>'
                  f'<div id="kclo" class="bsd" style="position:absolute;left:{xy[lo][0] + 40:.0f}px;top:{xy[lo][1] + 10:.0f}px;font-size:190px;color:{Y};{SHADOW};opacity:0">'
                  f'{"\u2212" if lv < 0 else ""}{abs(lv):g}{esc(u)}</div>')
    draw = max(0.8, min(2.0, D - 1.2))
    seg = [((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in zip(xy, xy[1:])]
    cum = [0.0] + [sum(seg[:k + 1]) for k in range(len(seg))]
    js = tj + [f'tl.fromTo("#kcl",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:{draw:.3f},ease:"none"}},.45);']
    for i in range(len(xy)):
        js.append(f'tl.fromTo("#kcd{i}",{{scale:0}},{{scale:1,duration:POP.dur,ease:POP.ease}},{0.45 + draw * cum[i] / max(cum[-1], 1):.3f});')
    tlo = 0.45 + draw * cum[lo] / max(cum[-1], 1)
    js += [f'tl.fromTo("#kclo",{{opacity:0,scale:1.5,filter:"blur(16px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:POP.dur,ease:POP.ease}},{tlo:.3f});'] + shake("#pcam", tlo + 0.05, amp=10.0)
    for i, tt in enumerate(ev.get("callouts_t", [])):
        if tt < D - 0.4 and i < len(c.get("callouts", [])):
            txt, _, _ = c["callouts"][i]
            lb, lj, _ = kline(f"kcc{i}", txt, "", tt, 150, X0, 1830, PW - 2 * X0, D=D); inner += lb; js += lj
    inner += (f'<div class="av" style="position:absolute;left:{X0}px;top:2010px;width:{PW - 2 * X0}px;font-size:40px;line-height:1.2;color:#a39a8e">'
              f'{esc(c.get("source", ""))}</div>')
    return side_frame(ev, mock, aroll_html, inner, js)


def body(ev, mock, aroll_html=""):
    t = ev["type"]
    if t == "reel": return reel(ev, mock, aroll_html)
    if t == "stat_bars": return bars(ev, mock, aroll_html)
    if t == "dotgrid": return dotgrid(ev, mock, aroll_html)
    if t == "chapter": return chapter(ev, mock)
    if t == "end": return end(ev, mock, aroll_html)
    if t == "plate": return plate(ev, mock, aroll_html)
    if t == "chart_line": return chart_line(ev, mock, aroll_html)
    raise KeyError(t)


def warm_other_panels(ev, b, mock):
    """The side cards without a kinetic version (chart_line...) keep their layout; their flat black panel becomes the warm studio."""
    flat = '<div id="panel" style="position:absolute;left:0;top:0;width:'
    if ev["type"] in TYPES or flat not in b: return b, []
    i = b.find('<div class="bg"></div>', b.find(flat))
    if i < 0: return b, []
    pb, pj = warm_panel(ev, mock)
    return b[:i] + pb + b[i + len('<div class="bg"></div>'):], pj
