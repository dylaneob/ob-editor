#!/usr/bin/env python3
"""Moving overlays, loaded by cards.py (OB 2026-10-29 on C4395: "no overlays can be static, all has to be moving, no just images
unless its a before and after", "no all text overlays ever", "when you use a vertical overlay ... have me move to the side dont
overlay the full screen", "the overlays you used are a little long til you switch to another"). Decoded from his references:
Markus Hunter (youtu.be/OPUwq4p29yQ: vertical media in a panel beside him, small stacked labels that land on his words) and
Jeff Nippard (youtu.be/MT9ZeE5JJsI: fast real footage, numbers that animate over it).

  reel   full-frame footage, a hard cut every ~2 s (ev["shots"]); over it, stacked lines that land on his words (ev["lines"]),
         a number that counts up (ev["big"]), or two clips side by side with a drawn divider (ev["split"]). ev["face"]: windows
         ([[t0, t1], ...] from the card's start) where the footage stops and OB is back on screen, the lines staying beside him
  vpair  vertical clips at full height on one side (ev["vids"]); the other side is OB himself (ev["beside"]: his A-roll slides
         over, so his face is on screen) or the dark card with the same lines / number as a reel

Footage: hf/assets/broll/KEY.mp4 (story/prep_broll.py; landscape 1920x1080, vertical "vert" pieces 1080x1920), muted.
Shot times are seconds from the card's start: {"b": key, "t": start, "d": length, "fx": 0.5, "fy": 0.5}. Lines:
{"text", "hi": the word in yellow, "at": seconds}; ev["kicker"]: a small yellow line above them. House style (brand, 10-28): no
boxes or bubbles, white with a soft shadow, OB yellow on the one word that matters.
"""
import html

Y = "#F7DC3A"; W, H = 3840, 2160
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
SHADOW = "text-shadow:0 10px 50px rgba(0,0,0,.9),0 0 10px rgba(0,0,0,.55)"


def _hl(text, hi):
    t = esc(text)
    return t.replace(esc(hi), f'<span style="color:{Y}">{esc(hi)}</span>', 1) if hi and esc(hi) in t else t


def _active(shots, t, gaps=False):
    """The shot on screen at t (for the breakdown still); with gaps (a reel that cuts back to OB), None between shots."""
    return next((s for s in shots if s["t"] <= t < s["t"] + s["d"]), None if gaps else (shots[-1] if shots else None))


def _shots(shots, mock, pre, settle, gaps=False):
    """Footage filling its parent box: one <video> per shot, timed by the runtime; each wrapper pushes in slowly (constant speed)."""
    b, js = "", []
    for k, s in enumerate(shots):
        if mock and s is not _active(shots, settle, gaps): continue
        fx, fy = s.get("fx", 0.5), s.get("fy", 0.5)
        m = (f'<img src="../assets/broll/{s["b"]}.jpg" style="width:100%;height:100%;object-fit:cover;object-position:{fx * 100:.0f}% {fy * 100:.0f}%;display:block"/>' if mock else
             f'<video class="media clip" src="../assets/broll/{s["b"]}.mp4" muted playsinline data-start="{s["t"]:.3f}" data-duration="{s["d"]:.3f}" '
             f'data-track-index="{k % 2}" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:{fx * 100:.0f}% {fy * 100:.0f}%"></video>')
        b += (f'<div id="{pre}{k}" style="position:absolute;inset:0;overflow:hidden;transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%">{m}</div>')
        js.append(f'tl.fromTo("#{pre}{k}",{{scale:1}},{{scale:{s.get("z", 1.06)},duration:{s["d"]:.3f},ease:"none"}},{s["t"]:.3f});')
    return b, js


def _lines(ev, x, y, width, D):
    """The kicker and the stacked lines (left-aligned), each landing on its word; a big number if ev["big"]."""
    b, js = "", []
    if ev.get("kicker"):
        b += (f'<div id="rk" class="avb" style="position:absolute;left:{x}px;top:{y - 130}px;font-size:76px;letter-spacing:8px;color:{Y};{SHADOW};opacity:0">'
              f'{esc(ev["kicker"]).upper()}</div>')
        js.append(f'tl.fromTo("#rk",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{min(0.1, D / 4):.3f});')
    size = ev.get("lsize", 150); gap = int(size * 1.08); bg = ev.get("big"); L = ev.get("lines", [])
    first = bool(bg) and bool(L) and bg.get("at", 0.2) <= min(ln.get("at", 0.2) for ln in L)   # the number lands first: it goes on top
    ly = y + (int(bg.get("size", 460) * 0.95) + (130 if bg.get("sub") else 0) + 40 if first else 0)
    for k, ln in enumerate(L):
        b += (f'<div id="rl{k}" class="din" style="position:absolute;left:{x}px;top:{ly + k * gap}px;width:{width}px;font-size:{ln.get("size", size)}px;'
              f'line-height:1;{SHADOW};opacity:0">{_hl(ln["text"], ln.get("hi"))}</div>')
        js.append(f'tl.fromTo("#rl{k}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{min(max(ln.get("at", 0.2), 0.05), max(D - 0.5, 0.05)):.3f});')
    if bg:
        txt = str(bg["text"]); digits = txt.replace(",", "")
        num = f'<span id="rbv">{esc(txt)}</span>' if digits.replace(".", "").isdigit() and bg.get("count", True) else esc(txt)
        ty = y if first else y + len(L) * gap
        b += (f'<div id="rb" style="position:absolute;left:{x}px;top:{ty}px;width:{width}px;opacity:0"><div class="din" style="font-size:{bg.get("size", 460)}px;line-height:.95;{SHADOW}">'
              f'{esc(bg.get("pre", ""))}{num}<span style="font-size:.42em;color:{Y};margin-left:30px">{esc(bg.get("unit", ""))}</span></div>'
              + (f'<div class="avb" style="font-size:96px;color:#f2f2f2;margin-top:24px;{SHADOW}">{_hl(bg["sub"], bg.get("hi"))}</div>' if bg.get("sub") else "") + '</div>')
        t0 = min(max(bg.get("at", 0.2), 0.05), max(D - 0.8, 0.05))
        js.append(f'tl.fromTo("#rb",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t0:.3f});')
        if "rbv" in num:
            dec = len(digits.split(".")[1]) if "." in digits else 0
            js.append(f'tl.fromTo("#rbv",{{innerText:0}},{{innerText:{float(digits)},snap:{{innerText:{10 ** -dec}}},duration:COUNT.dur,ease:COUNT.ease,immediateRender:false}},{t0:.3f});')
    return b, js


def settle(ev):
    ts = [ln.get("at", 0) for ln in ev.get("lines", [])] + ([ev["big"].get("at", 0) + 1.2] if ev.get("big") else [])
    ts += [s.get("at", 0) for s in ev.get("split", [])]
    return min(ev["dur"] - 0.15, max(ts + [0.6]) + 0.7)


def reel(ev, mock, aroll_html=""):
    D = ev["dur"]; st = ev["settle_t"] if mock and ev.get("settle_t") is not None else settle(ev); b, js = '<div class="bg"></div>', []
    if ev.get("split"):   # a versus: two clips side by side, a divider drawn down the middle, each side's label at its foot
        # ev["reveal"]: the first side fills the frame until then, then gives up half to the second (it slides in from the right)
        half = W // 2; rv = ev.get("reveal")
        for k, side in enumerate(ev["split"][:2]):
            sb, sj = _shots(side["shots"], mock, f"s{k}_", st); js += sj
            w0, x0 = (W, 0) if (rv and k == 0) else (half, k * half)
            b += f'<div id="sp{k}" style="position:absolute;left:{x0}px;top:0;width:{w0}px;height:{H}px;overflow:hidden">{sb}</div>'
        if rv:
            js += [f'tl.fromTo("#sp0",{{width:{W}}},{{width:{half},duration:SLIDE.dur,ease:SLIDE.ease}},{rv:.3f});',
                   f'tl.fromTo("#sp1",{{x:{half}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{rv:.3f});']
        b += ('<div style="position:absolute;left:0;bottom:0;width:100%;height:900px;background:linear-gradient(0deg,rgba(0,0,0,.72),rgba(0,0,0,0))"></div>'
              f'<div id="rdv" style="position:absolute;left:{half - 6}px;top:{260 if ev.get("kicker") else 0}px;width:12px;height:{H - (260 if ev.get("kicker") else 0)}px;background:#fff;transform-origin:50% 0;box-shadow:0 0 30px rgba(0,0,0,.5)"></div>')
        js.append(f'tl.fromTo("#rdv",{{scaleY:0}},{{scaleY:1,duration:SLIDE.dur,ease:SLIDE.ease}},{(rv or 0.05):.3f});')
        for k, side in enumerate(ev["split"][:2]):
            lw = (W - 240) if (rv and k == 0) else (half - 240); lx = 120 if (rv and k == 0) else k * half + 120
            b += (f'<div id="rs{k}" class="din" style="position:absolute;left:{lx}px;width:{lw}px;bottom:200px;text-align:center;'
                  f'font-size:{side.get("size", 170)}px;line-height:1;{SHADOW};opacity:0">{_hl(side["label"], side.get("hi"))}'
                  + (f'<div class="avb" style="font-size:84px;color:#eee;margin-top:22px">{esc(side["sub"])}</div>' if side.get("sub") else "") + '</div>')
            js.append(f'tl.fromTo("#rs{k}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{min(max(side.get("at", 0.2 + k * 0.8), 0.05), max(D - 0.5, 0.05)):.3f});')
            if rv and k == 0:   # the first label moves with its side into the left half
                js.append(f'tl.to("#rs0",{{left:120,width:{half - 240},duration:SLIDE.dur,ease:SLIDE.ease}},{rv:.3f});')
        if ev.get("kicker"):   # a soft dark band behind it: the kicker sits across both halves, one of them often bright
            b += ('<div style="position:absolute;left:0;top:0;width:100%;height:420px;background:linear-gradient(180deg,rgba(0,0,0,.6),rgba(0,0,0,0))"></div>'
                  f'<div id="rk" class="avb center" style="top:120px;font-size:76px;letter-spacing:8px;color:{Y};{SHADOW};opacity:0">{esc(ev["kicker"]).upper()}</div>')
            js.append('tl.fromTo("#rk",{opacity:0,y:-20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.1);')
        return b, js
    if ev.get("face"):   # OB 10-29: "its a little too long on the overlays when its the full screen you can come back to me a little more":
        # his A-roll runs under the whole card; the footage only plays outside ev["face"] (windows where his eyes are on the lens)
        b += f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll_html}</div>'
    sb, sj = _shots(ev["shots"], mock, "sh", st, bool(ev.get("face"))); b += f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{sb}</div>'; js += sj
    if ev.get("lines") or ev.get("big") or ev.get("kicker"):
        b += (f'<div id="rg" style="position:absolute;left:0;top:0;width:2600px;height:{H}px;opacity:0;'
              'background:linear-gradient(90deg,rgba(0,0,0,.62),rgba(0,0,0,.38) 55%,rgba(0,0,0,0))"></div>')
        js.append('tl.fromTo("#rg",{opacity:0},{opacity:1,duration:.25,ease:"none"},0);')
        lb, lj = _lines(ev, 220, ev.get("ly", 760), 2300, D); b += lb; js += lj
    return b, js


def vpair(ev, mock, aroll_html=""):
    """Vertical clips at full height on one side; OB (beside) or the dark card with lines/number on the other."""
    D = ev["dur"]; st = ev["settle_t"] if mock and ev.get("settle_t") is not None else settle(ev); side = ev.get("side", "L"); vw = 1215; vx = 230 if side == "L" else W - 230 - vw
    b, js = '<div class="bg"></div>', []
    if ev.get("beside"):   # his A-roll slides over to the far side so his face stays on screen (Markus Hunter's layout)
        shift = ev.get("shift", 1150) * (1 if side == "L" else -1)
        b += f'<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll_html}</div>'
        js.append(f'tl.fromTo("#vid",{{x:0}},{{x:{shift},duration:SLIDE.dur,ease:SLIDE.ease}},0);')
        b += (f'<div id="vpan" style="position:absolute;{"left" if side == "L" else "right"}:0;top:0;width:{vw + 460}px;height:{H}px;'
              f'background:#0c0c0c url(../assets/topo_bg.png) center/cover"></div>')
        js.append(f'tl.fromTo("#vpan",{{x:{-(vw + 460) if side == "L" else vw + 460}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);')
        if D > 1.6:
            js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.52:.3f});',
                   f'tl.to("#vpan",{{x:{-(vw + 460) if side == "L" else vw + 460},duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.52:.3f});']
    vb, vj = _shots(ev["vids"], mock, "vv", st)
    b += (f'<div id="vframe" style="position:absolute;left:{vx}px;top:58px;width:{vw}px;height:{H - 116}px;border-radius:44px;overflow:hidden;'
          f'box-shadow:0 30px 90px rgba(0,0,0,.65)">{vb}</div>')
    js += vj; js.append(f'tl.fromTo("#vframe",{{x:{-500 if side == "L" else 500},opacity:0}},{{x:0,opacity:1,duration:SLIDE.dur,ease:SLIDE.ease}},0);')
    if ev.get("tag"):   # what the footage is ("Me, 2025", "Client session"), small and yellow above the clip
        b += (f'<div id="vtag" class="avb" style="position:absolute;left:{vx + 40}px;top:110px;font-size:58px;letter-spacing:5px;color:{Y};{SHADOW};opacity:0">'
              f'{esc(ev["tag"]).upper()}</div>')
        js.append('tl.fromTo("#vtag",{opacity:0,y:-16},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.3);')
    if not ev.get("beside"):
        lx = vx + vw + 260 if side == "L" else 260
        lb, lj = _lines(ev, lx, ev.get("ly", 700), W - vw - 230 - 520, D); b += lb; js += lj
    return b, js


FN = {"reel": reel, "vpair": vpair}
TYPES = set(FN)
COVER = {"reel", "vpair"}   # full frame unless a vpair is "beside" him (assemble.is_cover checks "beside" first)


def body(ev, mock, aroll_html=""):
    return FN[ev["type"]](ev, mock, aroll_html)
