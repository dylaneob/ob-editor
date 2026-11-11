#!/usr/bin/env python3
"""Full-frame explainer cards (C4367, David bar video: Josh Brett's devices under OB's rules), drawn in code, loaded by cards.py.

  clip        an external clip in a white frame with its channel tag (montages chain with a banner); optional pull quote
  photo_full  a real photo filling the frame, slow push, kicker + title + sub at the foot
  num         one or two big numbers that count up, each with its label (two = a comparison with bars)
  math        arithmetic that builds line by line; optional number-line gauge (a marker slides from one value to another,
              against a dashed limit)
  dose        the EPG dose ladder: 10 / 25 / 40 g zones from the 8-week trial, then pins for bars a day
  coins       face value vs what your body spends: 9 coins vs a sliver
  timeline    points along a line, drawn as they're said
  title       the title card on gold, with the chapter chips
  disclaimer  one line, small

Every card reads its word times from ev["at_t"] (resolve_events "at" anchors, seconds from the card's start), and its
first frame is a finished picture (motion library rule 4). Springs come from the page (POP, SNAP, SOFT, SLIDE, BAR, COUNT).
"""
import html, re

Y, R, G, A_ = "#F7DC3A", "#E53935", "#22C55E", "#F59E0B"
W, H = 3840, 2160
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def T(ev, key, default):
    return float((ev.get("at_t") or {}).get(key, default))


# ------------------------------------------------------------------------------------------------ clip
def clip(ev, mock):
    D, a, key = ev["dur"], ev.get("aspect", "v"), ev["clip"]
    banner, quote = ev.get("banner"), ev.get("quote")
    if a == "v":   # full height (v3, OB 10-20: "don't have black on the side but do the blur"): the blurred copy fills the sides
        fh = 1760 if banner else 1990
        fw = round(fh * 9 / 16)
        fx = 560 if quote else (W - fw) // 2
        fy = 290 if banner else (H - fh) // 2 - 10
    else:   # a pull quote needs the right third: the frame shrinks and moves left
        fw = 2400 if quote else (2920 if banner else 3300)
        fh = round(fw * 9 / 16)
        fx, fy = (170 if quote else (W - fw) // 2), (300 if banner else (H - fh) // 2 - 10)
    media = (f'<img src="../assets/clips/{key}.jpg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:block"/>'
             if mock else
             f'<video class="media clip" src="../assets/clips/{key}.mp4" muted playsinline data-start="0" data-duration="{D:.3f}" '
             f'data-track-index="0" style="width:{fw}px;height:{fh}px"></video>')
    b = (f'<div class="bg"></div><div id="cgrp" style="position:absolute;inset:0;transform-origin:{fx + fw // 2}px {fy + fh // 2}px">'
         f'<div id="cfr" style="position:absolute;left:{fx}px;top:{fy}px;width:{fw}px;height:{fh}px;border-radius:30px;overflow:hidden;'
         f'background:#000;box-shadow:0 0 0 12px #fff, 0 40px 110px rgba(0,0,0,.7);transform-origin:50% 50%">'
         f'<div id="cin" style="position:absolute;left:0;top:0;width:{fw}px;height:{fh}px;transform-origin:50% 45%">{media}</div></div>'
         f'<div id="ctag" style="position:absolute;left:{fx + 40}px;top:{fy + fh - 64}px;display:flex;align-items:baseline;gap:28px;'
         f'background:#fff;color:#111;border-radius:22px;padding:22px 42px 24px;box-shadow:0 20px 50px rgba(0,0,0,.55);white-space:nowrap">'
         f'<span class="avb" style="font-size:66px">{esc(ev["tag"])}</span>'
         f'<span class="av" style="font-size:50px;color:#666">{esc(ev.get("sub", ""))}</span></div></div>')
    js = []
    if banner:
        b += (f'<div id="cban" class="center din" style="top:110px;font-size:118px;letter-spacing:1px">{banner}</div>')
        js.append('tl.set("#cban",{opacity:1,immediateRender:true},0);' if ev.get("chain_in") else
                  'tl.fromTo("#cban",{opacity:0,y:-30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    if quote:   # v4 (OB 10-20: "only half the screen"): the quote fills the right side, centred and sized to its length
        qx = fx + fw + (200 if a == "v" else 160); n = len(quote)
        fs = (740 if n <= 4 else 540 if n <= 8 else 300) if a == "v" else (400 if n <= 6 else 230)
        b += (f'<div style="position:absolute;left:{qx}px;top:0;width:{W - qx - 140}px;height:{H}px;display:flex;flex-direction:column;justify-content:center;'
              f'align-items:center;text-align:center">'
              + (f'<div id="cqs" class="avb" style="font-size:84px;color:#ececec;margin:0 0 34px;opacity:0;text-shadow:0 4px 24px rgba(0,0,0,.6)">'
                 f'{esc(ev["quote_kicker"])}</div>' if ev.get("quote_kicker") else "")
              + f'<div id="cq" class="din" style="font-size:{fs}px;line-height:1.0;color:{Y};text-wrap:balance;opacity:0;transform-origin:50% 50%;'
                f'text-shadow:0 10px 40px rgba(0,0,0,.45)">{esc(quote)}</div></div>')
        qt = T(ev, "quote", ev.get("quote_at", D * 0.5))
        if qt >= 0.6 and not ev.get("chain_in"):   # centred, the blur on both sides, until the quote lands; then it slides over
            x0 = (W - fw) // 2 - fx if a == "v" else W // 2 - (fx + fw // 2)
            s0 = 1.0 if a == "v" else round(3300 / fw, 4)
            js.append(f'tl.fromTo("#cgrp",{{x:{x0},scale:{s0}}},{{x:0,scale:1,duration:.55,ease:"power3.inOut"}},{max(0.0, qt - 0.4):.3f});')
        js += [f'tl.fromTo("#cq",{{opacity:0,scale:.82}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{qt:.3f});']
        if ev.get("quote_kicker"):
            js.append(f'tl.fromTo("#cqs",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(0, qt - 0.25):.3f});')
    if ev.get("chain_in"):   # a montage cut: hard cut, the new tag pops
        js += ['tl.fromTo("#ctag",{scale:.8},{scale:1,duration:POP.dur,ease:POP.ease},0);']
    else:
        js += ['tl.fromTo("#cfr",{scale:1.05},{scale:1,duration:SNAP.dur,ease:SNAP.ease},0);',
               'tl.fromTo("#ctag",{x:-60},{x:0,duration:SNAP.dur,ease:SNAP.ease},.08);']
    js.append(f'tl.fromTo("#cin",{{scale:1}},{{scale:{1.06 if a == "v" else 1.04},duration:{D:.3f},ease:"none"}},0);')
    return b, js


# ------------------------------------------------------------------------------------------------ photo_full
def _asset(k):
    """'david_box' -> photos/david_box.jpg; 'clips/M1.jpg' and 'ph:...' pass through."""
    k = str(k)
    return k if ("/" in k or k.startswith("ph:")) else f"photos/{k}.jpg"


def _img(src, style):
    """<img> for an asset path, or a labelled placeholder box for "ph:<what>" (a photo waiting on OB's OK to download)."""
    if str(src).startswith("ph:"):
        return (f'<div style="{style};display:flex;align-items:center;justify-content:center;background:repeating-linear-gradient(45deg,#2a2a2a 0 40px,#333 40px 80px);'
                f'border:6px dashed #777;color:#cfcfcf;font-family:AvDB;font-size:72px;text-align:center;padding:40px">PHOTO<br/>{esc(src[3:])}</div>')
    return f'<img src="../assets/{src}" style="{style}"/>'


def _photo_split(ev):
    """layout "split": a product shot that has to stay whole (the David box photo is square, and a full-frame crop cuts its
    wordmark): the photo in a card on the left, kicker + title + sub on the right. A sub with an at-key "sub" lands on his word."""
    D = ev["dur"]; s = 1560; x, y = 240, (H - s) // 2; tx = x + s + 170
    timed = bool(ev.get("sub")) and "sub" in (ev.get("at_t") or {})
    b = ('<div class="bg"></div>'
         f'<div id="psc" style="position:absolute;left:{x}px;top:{y}px;width:{s}px;height:{s}px;border-radius:44px;overflow:hidden;background:#fff;'
         f'box-shadow:0 40px 120px rgba(0,0,0,.65)">' + _img(_asset(ev["image"]), "width:100%;height:100%;object-fit:cover").replace("<img ", '<img id="pfi" ', 1) + '</div>'
         f'<div id="pft" style="position:absolute;left:{tx}px;width:{W - tx - 200}px;top:0;height:{H}px;display:flex;flex-direction:column;justify-content:center">'
         + (f'<div class="avb" style="font-size:96px;color:{Y};letter-spacing:4px;margin-bottom:30px">{esc(ev["kicker"])}</div>' if ev.get("kicker") else "")
         + (f'<div class="din" style="font-size:270px;line-height:1.0;text-wrap:balance;text-shadow:0 10px 40px rgba(0,0,0,.45)">{"<br/>".join(esc(x) for x in re.split(r" · |\n", str(ev["title"])))}</div>'
            if ev.get("title") else "")   # label facts ("28 g protein · 150 cal · 0 g sugar") stack one per line, never split mid-unit
         + (f'<div id="psub" class="avb" style="font-size:100px;line-height:1.15;color:#f0f0f0;margin-top:44px;text-wrap:balance{";opacity:0" if timed else ""}">{esc(ev["sub"])}</div>'
            if ev.get("sub") else "") + '</div>')
    js = ['tl.fromTo("#psc",{scale:.94,rotation:-2},{scale:1,rotation:0,duration:POP.dur,ease:POP.ease},0);',
          f'tl.fromTo("#pfi",{{scale:1}},{{scale:{ev.get("zoom", 1.06)},duration:{D:.3f},ease:"none",transformOrigin:"50% 55%"}},0);',
          'tl.fromTo("#pft",{x:60},{x:0,duration:SNAP.dur,ease:SNAP.ease},.06);']
    if timed:
        js.append(f'tl.fromTo("#psub",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{T(ev, "sub", 0.5):.3f});')
    return b, js


def _sponge(ev):
    """S08, v3 (OB 10-20: "why is it just a photo here and not an animation or a cool overlay"): the authors' 'lipid sink'.
    A light marble card: the sponge photo feathered into its own marble on the right, the line big on the left. Vitamin chips
    gather round the sponge on "like a sponge"; on "dissolve into" beta-carotene and K are soaked in (lower in the 8-week trial),
    D partly (rose less than control), A and E untouched (unchanged: PubMed 25497998); on "leave your body" the sponge slides
    out of frame with what it soaked up."""
    D = ev["dur"]; ts, td, tl_ = T(ev, "sponge", 1.4), T(ev, "dissolve", 4.0), T(ev, "leave", 5.6)
    MARBLE = "#e1e5ec"; cx, cy = 2700, 1100            # where the sponges sit on the frame
    s = 1.25; iw, ih = round(2000 * s), round(3000 * s); ix, iy = cx - round(1010 * s), cy - round(1560 * s)
    chip = lambda cid, x, y, txt, wide=False: (
        f'<div id="{cid}" style="position:absolute;left:{x - (330 if wide else 150)}px;top:{y - 150}px;width:{660 if wide else 300}px;height:300px;'
        f'border-radius:150px;background:radial-gradient(circle at 35% 30%,#ffe27a,#f5a623 60%,#d9820f);box-shadow:0 18px 40px rgba(120,70,0,.35);'
        f'display:flex;align-items:center;justify-content:center;color:#3a2200;font-family:DINC;font-size:{124 if wide else 186}px;opacity:0">{txt}</div>')
    b = (f'<div class="bg" style="background:{MARBLE}"></div>'
         f'<div id="spw" style="position:absolute;left:{ix}px;top:{iy}px;width:{iw}px;height:{ih}px;'
         f'-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 20%);mask-image:linear-gradient(90deg,transparent 0,#000 20%)">'
         f'<img id="spi" src="../assets/photos/sponge.jpg" style="width:100%;height:100%;transform-origin:{1010 * s:.0f}px {1560 * s:.0f}px"/></div>'
         '<div id="stg2" style="position:absolute;inset:0;transform-origin:50% 50%">'
         + chip("vK", 2230, 330, "K") + chip("vB", 3200, 330, "β-carotene", True) + chip("vD", 3540, 1180, "D")
         + chip("vA", 1980, 1830, "A") + chip("vE", 3260, 1930, "E")
         + f'<div id="spt" style="position:absolute;left:230px;top:0;width:1720px;height:{H}px;display:flex;flex-direction:column;justify-content:center">'
         f'<div class="avb" style="font-size:74px;color:#8a5a00;letter-spacing:5px;margin-bottom:30px">{esc(ev.get("kicker", ""))}</div>'
         f'<div class="din" style="font-size:236px;line-height:1.0;color:#141414">{"<br/>".join(esc(x) for x in str(ev.get("title", "")).split(chr(10)))}</div>'
         '<div id="sps" class="avb" style="font-size:84px;line-height:1.2;color:#2b2b2b;margin-top:46px;opacity:0">β-carotene and vitamin K ran lower.<br/>A and E didn\'t change.</div>'
         '</div></div>')
    js = [f'tl.fromTo("#spi",{{scale:1}},{{scale:1.06,duration:{D:.3f},ease:"none"}},0);',
          f'tl.fromTo("#stg2",{{scale:1}},{{scale:1.03,duration:{D:.3f},ease:"none"}},0);',
          'tl.fromTo("#spt",{x:-60,opacity:0},{x:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease},.05);']
    for k, c in enumerate(("vK", "vB", "vD", "vA", "vE")):
        js += [f'tl.fromTo("#{c}",{{opacity:0,scale:.4}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ts + 0.12 * k:.3f});',
               f'tl.to("#{c}",{{y:-18,duration:.9,ease:"sine.inOut",yoyo:true,repeat:{max(1, int(D / .9))}}},{ts + 0.5 + 0.12 * k:.3f});']
    for k, (c, x, y) in enumerate((("vK", 2230, 330), ("vB", 3200, 330))):   # soaked in
        js.append(f'tl.to("#{c}",{{x:{cx - x},y:{cy - y},scale:0,opacity:0,duration:.75,ease:"power2.in",overwrite:"auto"}},{td + 0.18 * k:.3f});')
    js += [f'tl.to("#vD",{{x:{(cx - 3540) * 0.45:.0f},y:{(cy - 1180) * 0.45:.0f},scale:.7,opacity:.55,duration:.8,ease:"power2.inOut",overwrite:"auto"}},{td + 0.3:.3f});',
           f'tl.fromTo("#spi",{{scale:1.0}},{{scale:1.045,duration:.22,ease:"power2.out",yoyo:true,repeat:1,immediateRender:false}},{td + 0.75:.3f});',
           f'tl.fromTo("#vA",{{x:0}},{{x:-24,duration:.12,ease:"none",yoyo:true,repeat:3,immediateRender:false}},{td + 0.25:.3f});',
           f'tl.fromTo("#vE",{{x:0}},{{x:24,duration:.12,ease:"none",yoyo:true,repeat:3,immediateRender:false}},{td + 0.35:.3f});',
           f'tl.fromTo("#sps",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{td + 1.0:.3f});',
           f'tl.to(["#spw","#vD"],{{x:"+=1900",duration:1.1,ease:"power2.in"}},{tl_:.3f});']
    return b, js


def _select_svg(j, a, pre):
    """The reel's "take a picture" box (2026-10-20): a white selection rectangle drawn on, four corner handles that pop in,
    and everything outside it dimmed, so the eye goes to one region. a: {"cx","cy","rx","ry"} like the red ellipses."""
    x0, y0, w_, h_ = a["cx"] - a["rx"], a["cy"] - a["ry"], 2 * a["rx"], 2 * a["ry"]; P = 2 * (w_ + h_)
    hs = [(x0, y0), (x0 + w_, y0), (x0, y0 + h_), (x0 + w_, y0 + h_)]
    svg = (f'<svg style="position:absolute;left:0;top:0;overflow:visible" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs><mask id="{pre}m{j}"><rect width="{W}" height="{H}" fill="#fff"/><rect x="{x0}" y="{y0}" width="{w_}" height="{h_}" rx="10" fill="#000"/></mask></defs>'
           f'<rect id="{pre}dim{j}" width="{W}" height="{H}" fill="#000" opacity="0" mask="url(#{pre}m{j})"/>'
           f'<rect id="{pre}{j}" x="{x0}" y="{y0}" width="{w_}" height="{h_}" rx="10" fill="none" stroke="#fff" stroke-width="9" '
           f'stroke-dasharray="{P:.0f}" stroke-dashoffset="{P:.0f}"/>'
           + "".join(f'<rect id="{pre}h{j}_{c}" x="{hx - 24}" y="{hy - 24}" width="48" height="48" fill="#fff"/>' for c, (hx, hy) in enumerate(hs))
           + '</svg>')
    def js(ta):
        out = [f'tl.to("#{pre}dim{j}",{{opacity:.5,duration:.35,ease:"none"}},{ta:.3f});',
               f'tl.to("#{pre}{j}",{{strokeDashoffset:0,duration:.45,ease:"power2.out"}},{ta:.3f});']
        for c, (hx, hy) in enumerate(hs):   # SVG: never scale to exactly 0, and pin svgOrigin on every tween (PRESET gotcha)
            out.append(f'tl.fromTo("#{pre}h{j}_{c}",{{scale:.001,svgOrigin:"{hx} {hy}"}},{{scale:1,svgOrigin:"{hx} {hy}",duration:POP.dur,ease:POP.ease}},{ta + 0.3 + 0.04 * c:.3f});')
        return out
    return svg, js


def _hand_label(lid, a, x, y, ta, size=150):
    """A handwritten label (Bradley Hand, white) that writes on left to right: the reel's marker notes. Opt in with "hand": true."""
    html = (f'<div id="{lid}" class="hand" style="position:absolute;left:{x}px;top:{y}px;font-size:{a.get("size", size)}px;color:#fff;'
            f'white-space:nowrap;transform:rotate(-3deg);text-shadow:0 0 14px rgba(0,0,0,.95),0 0 32px rgba(0,0,0,.85),0 8px 40px rgba(0,0,0,.8);clip-path:inset(0 100% 0 0)">{esc(a["label"])}</div>')
    return html, [f'tl.to("#{lid}",{{clipPath:"inset(0 0% 0 0)",duration:{max(0.4, 0.06 * len(a["label"])):.2f},ease:"none"}},{ta + 0.25:.3f});']


def _sunburn(ev):
    """The sun analogy (S15; OB 10-20: "we could've made a figure get sun burned and increased retention"). A flat figure on the
    sand, drawn in code (no AI art): the sun crosses the sky as the three lines land on his words (at keys a, b, c: 10 minutes,
    6 hours, 12 hours); his skin goes from normal to pink to lobster red, sweat drops at 6 hours, and at 12 hours the sky turns to
    sunset, his sunglasses lift off two pale tan lines, the smile turns to a wince and heat rises off him."""
    D = ev["dur"]
    rows = ev.get("rows") or [["10 minutes", "fantastic", "a", "sun"], ["6 hours", "you're feeling it", "b", "sun"], ["12 hours", "you're going home a lobster", "c", "x"]]
    tt = [T(ev, r[2], D * (0.12 + 0.2 * k)) for k, r in enumerate(rows)]
    ta, tb, tc_ = tt[0], tt[-2], tt[-1]                     # first beat, "feeling it", "lobster"
    th = tt[1] if len(rows) > 3 else None                   # "an hour in, you're tanning" (4-row version)
    SK0, SKT, SK1, SK2 = "#e8b48c", "#d39a68", "#f2937a", "#df3b2b"; LN0, LN2 = "#a8714e", "#8f1d12"
    fs = lambda c: f'style="fill:var(--skin);stroke:var(--line);stroke-width:6;stroke-linejoin:round"'
    fig = (f'<svg id="fig" viewBox="0 0 600 1100" width="720" height="1320" style="position:absolute;left:2560px;top:470px;overflow:visible;'
           f'--skin:{SK0};--line:{LN0}">'
           # legs, feet, shorts, torso, arms, neck, ears, head
           f'<rect x="178" y="700" width="92" height="310" rx="40" {fs(0)}/><rect x="330" y="700" width="92" height="310" rx="40" {fs(0)}/>'
           f'<ellipse cx="220" cy="1030" rx="70" ry="30" {fs(0)}/><ellipse cx="382" cy="1030" rx="70" ry="30" {fs(0)}/>'
           f'<path d="M185 330 Q138 345 128 470 L118 640 Q133 662 156 645 L170 480 Q180 400 214 372 Z" {fs(0)}/>'
           f'<path d="M415 330 Q462 345 472 470 L482 640 Q467 662 444 645 L430 480 Q420 400 386 372 Z" {fs(0)}/>'
           f'<path d="M180 318 Q300 290 420 318 L440 580 Q300 606 160 580 Z" {fs(0)}/>'
           '<path d="M232 420 Q262 440 292 420 M308 420 Q338 440 368 420 M300 455 L300 560" style="fill:none;stroke:var(--line);stroke-width:5;opacity:.45"/>'
           f'<path d="M160 572 Q300 600 440 572 L458 740 L318 740 L300 662 L282 740 L142 740 Z" style="fill:{Y};stroke:#b89400;stroke-width:6;stroke-linejoin:round"/>'
           f'<rect x="268" y="262" width="64" height="62" rx="18" {fs(0)}/>'
           f'<circle cx="195" cy="182" r="24" {fs(0)}/><circle cx="405" cy="182" r="24" {fs(0)}/>'
           f'<circle cx="300" cy="172" r="106" {fs(0)}/>'
           '<path d="M196 158 Q196 58 300 56 Q404 58 404 158 Q372 108 300 108 Q228 108 196 158 Z" style="fill:#3a281c"/>'
           # the tan lines and eyes (revealed at 12 h when the glasses lift), the glasses, the mouths
           f'<g id="tan" style="opacity:0"><ellipse cx="258" cy="172" rx="40" ry="27" style="fill:{SK0}"/><ellipse cx="342" cy="172" rx="40" ry="27" style="fill:{SK0}"/>'
           '<circle cx="258" cy="174" r="8" style="fill:#2a1a12"/><circle cx="342" cy="174" r="8" style="fill:#2a1a12"/></g>'
           '<g id="gls"><rect x="214" y="148" width="88" height="50" rx="20" style="fill:#151515"/><rect x="298" y="148" width="88" height="50" rx="20" style="fill:#151515"/>'
           '<path d="M298 164 L302 164" style="stroke:#151515;stroke-width:10"/><rect x="226" y="156" width="26" height="10" rx="5" style="fill:#fff;opacity:.35"/></g>'
           '<path id="smile" d="M258 232 Q300 268 342 232" style="fill:none;stroke:#5a2414;stroke-width:9;stroke-linecap:round"/>'
           '<path id="wince" d="M258 246 Q279 230 300 246 Q321 262 342 246" style="fill:none;stroke:#5a2414;stroke-width:9;stroke-linecap:round;opacity:0"/>'
           # sweat at 6 h, heat at 12 h
           '<g id="sw" style="opacity:0"><path d="M168 120 Q178 140 168 152 Q158 140 168 120 Z" style="fill:#7ec8ff"/>'
           '<path d="M440 108 Q450 128 440 140 Q430 128 440 108 Z" style="fill:#7ec8ff"/><path d="M452 232 Q462 252 452 264 Q442 252 452 232 Z" style="fill:#7ec8ff"/></g>'
           '<g id="heat" style="opacity:0;stroke:#fff;stroke-width:9;fill:none;stroke-linecap:round">'
           '<path d="M230 30 Q215 0 230 -30 Q245 -60 230 -90"/><path d="M300 10 Q285 -20 300 -50 Q315 -80 300 -110"/><path d="M370 30 Q355 0 370 -30 Q385 -60 370 -90"/></g>'
           '</svg>')
    sun = ('<div id="sun" style="position:absolute;left:0;top:0;width:300px;height:300px;transform:translate(1820px,860px)">'
           '<svg id="rays" viewBox="-150 -150 300 300" width="300" height="300" style="position:absolute;inset:0;overflow:visible">'
           + "".join(f'<rect x="-9" y="-150" width="18" height="46" rx="9" transform="rotate({k * 30})" style="fill:#ffe58a"/>' for k in range(12))
           + '</svg><div style="position:absolute;left:60px;top:60px;width:180px;height:180px;border-radius:90px;'
           'background:radial-gradient(circle at 40% 38%,#fffbe0,#ffd84a 55%,#f7a41d);box-shadow:0 0 120px 40px rgba(255,214,90,.55)"></div></div>')
    rowh = "".join(
        f'<div id="sbr{k}" style="opacity:0;margin-bottom:{40 if len(rows) > 3 else 54}px"><div class="din" style="font-size:{176 if len(rows) > 3 else 200}px;line-height:1">{esc(r[0]).upper()}</div>'
        f'<div class="avb" style="font-size:{78 if len(rows) > 3 else 86}px;line-height:1.1;color:{"#9cff9c" if k == 0 else ("#ff8a7a" if k == len(rows) - 1 else ("#ffd0c0" if k == len(rows) - 2 else "#ffe2a8"))}">{esc(r[1])}'
        f'{" ✓" if k == 0 else ""}</div></div>' for k, r in enumerate(rows))
    b = ('<div class="bg" style="background:#16233f"></div>'
         '<div id="sbstage" style="position:absolute;inset:0;transform-origin:62% 60%">'
         '<div id="sky1" style="position:absolute;inset:0;background:linear-gradient(180deg,#2f6fc4 0%,#86bdea 58%,#f7e2b0 100%)"></div>'
         '<div id="sky2" style="position:absolute;inset:0;opacity:0;background:linear-gradient(180deg,#2b1747 0%,#b8443a 52%,#f59a4e 100%)"></div>'
         + sun +
         '<div style="position:absolute;left:0;top:1790px;width:3840px;height:400px;background:linear-gradient(180deg,#f0d29a,#d9b06c)"></div>'
         '<div style="position:absolute;left:2420px;top:1860px;width:1000px;height:70px;border-radius:12px;background:repeating-linear-gradient(90deg,#e53935 0 90px,#fff 90px 180px);opacity:.92"></div>'
         + fig + '</div>'
         '<div style="position:absolute;left:0;top:0;width:2300px;height:2160px;background:linear-gradient(90deg,rgba(0,0,0,.55),rgba(0,0,0,.25) 70%,rgba(0,0,0,0))"></div>'
         f'<div id="sbt" style="position:absolute;left:230px;top:250px;width:1900px">'
         f'<div class="avb" style="font-size:76px;color:{Y};letter-spacing:6px;margin-bottom:60px;text-shadow:0 4px 24px rgba(0,0,0,.5)">{esc(ev.get("kicker", "THINK OF IT LIKE THE SUN"))}</div>'
         f'<div style="text-shadow:0 8px 40px rgba(0,0,0,.6)">{rowh}</div></div>')
    pos = [(1820, 860), (2120, 560), (2500, 300), (2860, 240), (3380, 600), (3560, 760)] if len(rows) > 3 else [(1820, 860), (2120, 560), (2760, 250), (3380, 600), (3560, 760)]
    js = [f'tl.fromTo("#sbstage",{{scale:1}},{{scale:1.035,duration:{D:.3f},ease:"none"}},0);',
          f'tl.to("#rays",{{rotation:120,duration:{D:.3f},ease:"none"}},0);',
          'tl.fromTo("#sbt",{x:-50,opacity:0},{x:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease},.05);',
          f'tl.to("#sun",{{x:{pos[1][0]},y:{pos[1][1]},duration:{max(0.3, tt[0]):.3f},ease:"sine.inOut"}},0);',
          *[f'tl.to("#sun",{{x:{pos[k + 2][0]},y:{pos[k + 2][1]},duration:{max(0.3, tt[k + 1] - tt[k]):.3f},ease:"sine.inOut"}},{tt[k]:.3f});' for k in range(len(tt) - 1)],
          f'tl.to("#sun",{{x:{pos[-1][0]},y:{pos[-1][1]},duration:{max(0.3, D - tt[-1]):.3f},ease:"sine.in"}},{tt[-1]:.3f});',
          f'tl.fromTo("#fig",{{scale:1}},{{scale:1.012,duration:1.1,ease:"sine.inOut",yoyo:true,repeat:{max(1, int(D / 1.1))},svgOrigin:"300 1060"}},0);']
    for k, t in enumerate(tt):
        js.append(f'tl.fromTo("#sbr{k}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:POP.dur,ease:POP.ease}},{t:.3f});')
        if k: js.append(f'tl.to("#sbr{k - 1}",{{opacity:.42,duration:.3,ease:"none"}},{t:.3f});')
    if th is not None: js.append(f'tl.to("#fig",{{"--skin":"{SKT}",duration:.9,ease:"power1.inOut"}},{th:.3f});')
    js += [f'tl.to("#fig",{{"--skin":"{SK1}",duration:1.1,ease:"power1.inOut"}},{tb:.3f});',
           f'tl.fromTo("#sw",{{opacity:0,y:-10}},{{opacity:1,y:0,duration:.3,ease:"none"}},{tb + 0.5:.3f});',
           f'tl.to("#sw",{{y:60,duration:{max(0.4, tc_ - tb - 0.6):.3f},ease:"power1.in"}},{tb + 0.8:.3f});',
           f'tl.to("#sky2",{{opacity:1,duration:{max(0.6, (tc_ - tb) * 0.8):.3f},ease:"none"}},{tb + 0.3:.3f});',
           f'tl.to("#fig",{{"--skin":"{SK2}","--line":"{LN2}",duration:.8,ease:"power2.out"}},{tc_:.3f});',
           f'tl.to("#sw",{{opacity:0,duration:.2,ease:"none"}},{tc_:.3f});',
           f'tl.to("#gls",{{y:-150,rotation:-8,svgOrigin:"300 172",duration:.45,ease:"back.out(2)"}},{tc_ + 0.45:.3f});',
           f'tl.to("#tan",{{opacity:1,duration:.2,ease:"none"}},{tc_ + 0.5:.3f});',
           f'tl.to("#smile",{{opacity:0,duration:.15,ease:"none"}},{tc_ + 0.3:.3f});',
           f'tl.to("#wince",{{opacity:1,duration:.15,ease:"none"}},{tc_ + 0.3:.3f});',
           f'tl.fromTo("#heat",{{opacity:0,y:20}},{{opacity:.85,y:-30,duration:.9,ease:"sine.out",repeat:{max(1, int((D - tc_) / 0.9))},yoyo:true}},{tc_ + 0.6:.3f});']
    return b, js


def photo_full(ev, mock):
    D = ev["dur"]; fx, fy = ev.get("focal", [0.5, 0.5])
    if ev.get("anim") == "sponge": return _sponge(ev)
    if ev.get("anim") == "sunburn": return _sunburn(ev)
    if ev.get("layout") == "split" and not str(ev["image"]).startswith("ph:"):
        return _photo_split(ev)
    if str(ev["image"]).startswith("ph:"):
        b = ('<div class="bg"></div>' + _img(ev["image"], f"position:absolute;left:0;top:0;width:{W}px;height:{H - 600}px")
             + f'<div id="pft" style="position:absolute;left:200px;bottom:170px;width:3300px">'
             + (f'<div class="avb" style="font-size:70px;color:{Y};letter-spacing:3px;margin-bottom:20px">{esc(ev["kicker"])}</div>' if ev.get("kicker") else "")
             + (f'<div class="din" style="font-size:210px;line-height:1">{esc(ev["title"])}</div>' if ev.get("title") else "") + '</div>')
        return b, ['tl.fromTo("#pft",{y:40},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);']
    ann = ""   # v3 (OB 10-20: "why is it just a photo... not an animation or a cool overlay"): red circles drawn on as he says it
    ajs = []
    for j, a in enumerate(ev.get("annot", [])):
        ta = T(ev, a["at"], 0.5) if isinstance(a.get("at"), str) else float(a.get("at", 0.5))
        if a.get("style") == "select":
            svg, sjs = _select_svg(j, a, "pa"); ann += svg; ajs += sjs(ta)
            if a.get("label"):
                h, hj = (_hand_label(f"pal{j}", a, a.get("lx", a["cx"] - a["rx"]), a.get("ly", a["cy"] - a["ry"] - 190), ta) if a.get("hand") else
                         (f'<div id="pal{j}" class="din" style="position:absolute;left:{a.get("lx", a["cx"] - a["rx"])}px;top:{a.get("ly", a["cy"] - a["ry"] - 220)}px;'
                          f'font-size:{a.get("size", 160)}px;color:#fff;text-shadow:0 8px 40px rgba(0,0,0,.75);opacity:0;white-space:nowrap">{esc(a["label"])}</div>',
                          [f'tl.fromTo("#pal{j}",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ta + 0.3:.3f});']))
                ann += h; ajs += hj
            continue
        L = 3.1416 * (3 * (a["rx"] + a["ry"]) - ((3 * a["rx"] + a["ry"]) * (a["rx"] + 3 * a["ry"])) ** 0.5) * 1.05
        ann += (f'<svg style="position:absolute;left:0;top:0;overflow:visible" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                f'<ellipse id="pa{j}" cx="{a["cx"]}" cy="{a["cy"]}" rx="{a["rx"]}" ry="{a["ry"]}" fill="none" stroke="{R}" stroke-width="18" '
                f'stroke-linecap="round" stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}" transform="rotate(-4 {a["cx"]} {a["cy"]})"/></svg>')
        ajs.append(f'tl.to("#pa{j}",{{strokeDashoffset:0,duration:.5,ease:"power2.out"}},{ta:.3f});')
        if a.get("label") and a.get("hand"):
            h, hj = _hand_label(f"pal{j}", a, a.get("lx", a["cx"] + a["rx"] + 40), a.get("ly", a["cy"] - 110), ta); ann += h; ajs += hj
        elif a.get("label"):
            ann += (f'<div id="pal{j}" class="din" style="position:absolute;left:{a.get("lx", a["cx"] + a["rx"] + 40)}px;top:{a.get("ly", a["cy"] - 110)}px;'
                    f'font-size:{a.get("size", 200)}px;color:#fff;text-shadow:0 8px 40px rgba(0,0,0,.75);opacity:0;white-space:nowrap">{esc(a["label"])}</div>')
            ajs.append(f'tl.fromTo("#pal{j}",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ta + 0.3:.3f});')
    b = (f'<div class="bg"></div><div style="position:absolute;inset:0;overflow:hidden">'
         f'<img id="pfi" src="../assets/{_asset(ev["image"])}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover;'
         f'object-position:{fx * 100:.0f}% {fy * 100:.0f}%;transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%"/>'
         f'<div id="pfa" style="position:absolute;inset:0;transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%">{ann}</div></div>'
         f'<div style="position:absolute;left:0;top:{H - 1000}px;width:{W}px;height:1000px;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.85))"></div>'
         f'<div id="pft" style="position:absolute;left:200px;bottom:160px;width:3400px">'
         + (f'<div class="avb" style="font-size:96px;color:{Y};letter-spacing:4px;margin-bottom:24px">{esc(ev["kicker"])}</div>' if ev.get("kicker") else "")
         + (f'<div class="din" style="font-size:300px;line-height:.98">{esc(ev["title"])}</div>' if ev.get("title") else "")
         + (f'<div class="av" style="font-size:92px;color:#efefef;margin-top:26px">{esc(ev["sub"])}</div>' if ev.get("sub") else "")
         + '</div>'
         + (f'<div class="av" style="position:absolute;right:40px;bottom:26px;font-size:38px;color:rgba(255,255,255,.65)">{esc(ev["credit"])}</div>' if ev.get("credit") else ""))
    js = [f'tl.fromTo(["#pfi","#pfa"],{{scale:1.0}},{{scale:{ev.get("zoom", 1.09)},duration:{D:.3f},ease:"none"}},0);',
          'tl.fromTo("#pft",{y:40},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);'] + ajs
    return b, js


# ------------------------------------------------------------------------------------------------ num
def _split_num(s):
    m = re.match(r"^([^\d]*)([\d,]*\.?\d+)(.*)$", s)
    return (m.group(1), m.group(2), m.group(3)) if m else (s, None, "")


def num(ev, mock):
    """ev["items"]: [[number text, label, at-key], ...]; one item = a big centred number, two = side by side with bars;
    optional ev["image"] (assets/photos) shown left of a single number; optional ev["anim"] draws the idea instead (NUM_ANIM)."""
    if ev.get("anim") in NUM_ANIM: return NUM_ANIM[ev["anim"]](ev, mock)
    D, items = ev["dur"], ev["items"]
    b, js = '<div class="bg"></div>', []
    if ev.get("title"):
        b += f'<div id="nt" class="center avb" style="top:300px;font-size:92px;color:#e8e8e8">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#nt",{y:30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    vals = []
    for k, it in enumerate(items):   # [text, label, at-key, value]: the value sizes the bars (6.1M vs 659K -> 6100, 659)
        pre, n, post = _split_num(it[0]); vals.append(it[3] if len(it) > 3 else (float(n.replace(",", "")) if n else 0))
    if len(items) == 1:
        it = items[0]; pre, n, post = _split_num(it[0])
        t0 = T(ev, it[2], 0.1) if len(it) > 2 and it[2] else 0.1
        x0 = 0
        if ev.get("image"):   # v3 (OB 10-20: "why did you crop my face... so small"): the full vertical frame at full height
            asp = ev.get("_img_aspect", 9 / 16)   # vertical phone frames at full height; a square product shot as a big square
            ph = 1900 if asp < 0.8 else 1560; pw = round(ph * min(asp, 1.0)); px, py = 330, (H - ph) // 2; x0 = px + pw + 60
            b += (f'<div id="nim" style="position:absolute;left:{px}px;top:{py}px;width:{pw}px;height:{ph}px;border-radius:36px;overflow:hidden;'
                  f'box-shadow:0 0 0 10px #fff,0 40px 120px rgba(0,0,0,.7);background:#fff">' + _img(_asset(ev["image"]), f"width:100%;height:100%;object-fit:{'cover' if asp > 1.05 else 'contain'}") + '</div>')
            dx = (W - pw) // 2 - px if t0 > 0.6 else 0   # a late number: the photo holds the frame centred, then slides over for it
            js += [f'tl.fromTo("#nim",{{scale:.9,rotation:-4,opacity:0,x:{dx}}},{{scale:1,rotation:-1.5,opacity:1,x:{dx},duration:POP.dur,ease:POP.ease}},0);',
                   f'tl.fromTo("#nim",{{y:0}},{{y:-22,duration:{max(1.0, D / 2):.3f},ease:"sine.inOut",yoyo:true,repeat:1}},.4);']
            if dx: js.append(f'tl.to("#nim",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{max(0.3, t0 - 0.15):.3f});')
        rw = W - x0 - (360 if x0 else 0)   # keep clear of the right edge: the stage push and camera beats scale the frame ~1.1x
        b += (f'<div id="n0" style="position:absolute;left:{x0}px;width:{rw}px;top:{560 if x0 else 640}px;text-align:center">'
              f'<span class="din" style="font-size:{640 if x0 else 600}px;line-height:1;text-shadow:0 12px 50px rgba(0,0,0,.5)">{esc(pre)}<span id="nv0" data-to="{esc(n or "")}">{esc(n or "")}</span>{esc(post)}</span>'
              f'<div class="avb" style="font-size:{110 if x0 else 104}px;color:#f0f0f0;margin-top:30px;padding:0 {60 if x0 else 120}px;text-wrap:balance;text-shadow:0 6px 30px rgba(0,0,0,.6)">{esc(it[1])}</div></div>')
        js.append(f'tl.fromTo("#n0",{{scale:.86,opacity:0}},{{scale:1,opacity:1,duration:POP.dur,ease:POP.ease}},{t0:.3f});')
        if n and ev.get("count", True):   # counts from 0 as the number lands; tweening innerText (with snap) renders on seek, callbacks don't
            dec = len(n.split(".")[1]) if "." in n else 0
            js.append(f'tl.fromTo("#nv0",{{innerText:0}},{{innerText:{float(n.replace(",", ""))},snap:{{innerText:{10 ** -dec}}},'
                      f'duration:COUNT.dur,ease:COUNT.ease,immediateRender:false}},{t0:.3f});')
    else:
        mx = max(vals) or 1
        for k, it in enumerate(items):
            pre, n, post = _split_num(it[0]); x = 420 + k * 1600
            hpx = int(900 * vals[k] / mx) if ev.get("bars", True) else 0
            col = Y if k == 0 else "#f2f2f2"
            b += (f'<div id="n{k}" style="position:absolute;left:{x}px;top:500px;width:1400px;text-align:center">'
                  f'<div class="din" style="font-size:330px;line-height:1">{esc(it[0])}</div>'
                  f'<div class="avb" style="font-size:80px;color:#e6e6e6;margin-top:24px;text-wrap:balance">{esc(it[1])}</div></div>')
            if hpx:
                b += (f'<div id="nb{k}" style="position:absolute;left:{x + 450}px;top:{1960 - hpx}px;width:500px;height:{hpx}px;border-radius:30px 30px 0 0;'
                      f'background:{col};transform-origin:50% 100%"></div>')
            t0 = T(ev, it[2], 0.1 + 0.9 * k) if len(it) > 2 and it[2] else 0.1 + 0.9 * k
            js.append(f'tl.fromTo("#n{k}",{{y:40,opacity:0}},{{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease}},{t0:.3f});')
            if hpx: js.append(f'tl.fromTo("#nb{k}",{{scaleY:.001}},{{scaleY:1,duration:BAR.dur,ease:BAR.ease}},{t0:.3f});')
    if ev.get("source"):
        b += f'<div class="av" style="position:absolute;left:200px;top:2030px;font-size:50px;color:#8f8f8f">{esc(ev["source"])}</div>'
    return b, js


# ------------------------------------------------------------------------------------------------ num, drawn
# C4369 (OB 10-21, scrolling the breakdown: "make an animation on this one", "better slide and animation for this one",
# "better visual here"): a num card with ev["anim"] draws its idea instead of a bare number. Opt-in: no "anim", no change.
def _src(ev):   # num's source line, same shape, so stage.py lifts it out of the push
    return (f'<div class="av" style="position:absolute;left:200px;top:2030px;font-size:50px;color:#8f8f8f">{esc(ev["source"])}</div>'
            if ev.get("source") else "")


def _num_clock(ev, mock):
    """Spring forward: a wall clock jumps 2:00 to 3:00 as "dst" is said (the lost hour sweeps the face red), then the week
    after grows its cap over a normal week and the number lands on the item's key. ev["bar_head"], ev["bar_labels"]."""
    D, it = ev["dur"], ev["items"][0]; pre, n, post = _split_num(it[0]); pct = float(n.replace(",", ""))
    tv = T(ev, it[2], D * 0.7) if len(it) > 2 and it[2] else D * 0.7
    td = min(T(ev, "dst", tv - 1.4), tv - 0.9); sp = max(0.5, min(0.85, tv - td - 0.2))
    cx, cy, Rr = 1120, 1110, 470; S2 = 2 * Rr
    b, js = '<div class="bg"></div>', []
    if ev.get("title"):
        b += f'<div id="nt" class="center din" style="top:250px;font-size:130px">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#nt",{y:-30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    ticks = ""
    for k in range(60):
        big = k % 5 == 0; w, h = ((22, 84) if k % 15 == 0 else (14, 62)) if big else (6, 26)
        ticks += (f'<div style="position:absolute;left:{Rr - w / 2:.0f}px;top:{Rr - h / 2:.0f}px;width:{w}px;height:{h}px;border-radius:{w // 2}px;'
                  f'background:{"#1d1d1d" if big else "#8a8a8a"};transform:rotate({6 * k}deg) translateY(-{Rr - 52 - h / 2:.0f}px)"></div>')
    nums = "".join(f'<div class="din" style="position:absolute;left:{Rr + dx}px;top:{Rr + dy}px;transform:translate(-50%,-46%);font-size:120px;color:#1d1d1d">{t}</div>'
                   for t, dx, dy in (("12", 0, -(Rr - 175)), ("3", Rr - 175, 0), ("6", 0, Rr - 175), ("9", -(Rr - 175), 0)))
    rs = (Rr - 40) / 2; C = 2 * 3.14159265 * rs
    hand = lambda hid, w, ln, tail, col, a: (f'<div id="{hid}" style="position:absolute;left:{Rr - w / 2:.0f}px;top:{Rr - ln}px;width:{w}px;height:{ln + tail}px;'
                                            f'border-radius:{w / 2:.0f}px;background:{col};transform-origin:{w / 2:.0f}px {ln}px;transform:rotate({a}deg);'
                                            f'box-shadow:0 6px 14px rgba(0,0,0,.35)"></div>')
    b += (f'<div id="clk" style="position:absolute;left:{cx - Rr}px;top:{cy - Rr}px;width:{S2}px;height:{S2}px;transform-origin:50% 50%">'
          f'<div style="position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle at 40% 32%,#fff 0%,#f2f2f2 58%,#d9d9d9 100%);'
          f'box-shadow:0 0 0 26px #161616,0 0 0 34px #3c3c3c,0 50px 140px rgba(0,0,0,.65)"></div>'
          f'<svg width="{S2}" height="{S2}" viewBox="0 0 {S2} {S2}" style="position:absolute;left:0;top:0">'
          f'<circle id="csec" cx="{Rr}" cy="{Rr}" r="{rs:.1f}" fill="none" stroke="{R}" stroke-opacity=".34" stroke-width="{2 * rs:.1f}" '
          f'stroke-dasharray="{C:.1f}" stroke-dashoffset="{C:.1f}" transform="rotate(-90 {Rr} {Rr})"/></svg>'
          f'{ticks}{nums}{hand("chh", 38, round(Rr * 0.5), 44, "#151515", 60)}{hand("cmh", 26, round(Rr * 0.78), 56, "#151515", 0)}'
          f'{hand("csh", 9, round(Rr * 0.86), 80, R, 0)}'
          f'<div style="position:absolute;left:{Rr - 34}px;top:{Rr - 34}px;width:68px;height:68px;border-radius:34px;background:{R};box-shadow:0 0 0 12px #151515"></div></div>'
          f'<div style="position:absolute;left:{cx - 600}px;width:1200px;top:{cy + Rr + 70}px;height:170px;text-align:center">'
          f'<div id="cta" class="din" style="position:absolute;left:0;width:100%;font-size:150px;line-height:1">2:00 AM</div>'
          f'<div id="ctb" class="din" style="position:absolute;left:0;width:100%;font-size:150px;line-height:1;color:{Y};opacity:0">3:00 AM</div></div>')
    js += [f'tl.set("#csh",{{rotation:{6 * k}}},{k:.3f});' for k in range(1, int(D) + 1)]   # the second hand ticks
    js += [f'tl.fromTo("#cmh",{{rotation:0}},{{rotation:360,duration:{sp:.3f},ease:"power2.inOut"}},{td:.3f});',
           f'tl.fromTo("#chh",{{rotation:60}},{{rotation:90,duration:{sp:.3f},ease:"power2.inOut"}},{td:.3f});',
           f'tl.fromTo("#csec",{{strokeDashoffset:{C:.1f}}},{{strokeDashoffset:0,duration:{sp:.3f},ease:"power2.inOut"}},{td:.3f});',
           f'tl.fromTo("#clk",{{scale:1.05}},{{scale:1,duration:POP.dur,ease:POP.ease,immediateRender:false}},{td + sp:.3f});',
           f'tl.to("#cta",{{opacity:0,y:-50,duration:.2,ease:"power1.in"}},{td + sp - 0.1:.3f});',
           f'tl.fromTo("#ctb",{{opacity:0,y:50}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{td + sp:.3f});']
    # a normal week vs the week after, to honest scale: the red cap is the real share of the bar
    lab0, lab1 = ev.get("bar_labels", ["A normal week", "The week after we spring forward"])
    yb, hb, bw = 1600, 680, 430; xs = (2200, 2900); cap = round(hb * pct / 100); xm = (xs[0] + xs[1] + bw) // 2
    b += (f'<div id="bhd" class="din" style="position:absolute;left:{xm - 800}px;width:1600px;text-align:center;top:440px;font-size:120px">{esc(ev.get("bar_head", "Fatal car crashes"))}</div>'
          f'<div style="position:absolute;left:{xs[0] - 90}px;top:{yb}px;width:{xs[1] + bw - xs[0] + 180}px;height:8px;border-radius:4px;background:#9a9a9a"></div>')
    for k, (x, lab) in enumerate(zip(xs, (lab0, lab1))):
        b += (f'<div id="nb{k}" style="position:absolute;left:{x}px;top:{yb - hb}px;width:{bw}px;height:{hb}px;border-radius:24px 24px 0 0;'
              f'background:rgba(255,255,255,{.34 if k == 0 else .5})"></div>'
              f'<div class="avb" style="position:absolute;left:{x + bw // 2 - 330}px;width:660px;text-align:center;top:{yb + 40}px;font-size:62px;line-height:1.18;color:#e2e2e2">{esc(lab)}</div>')
    b += (f'<div id="ncap" style="position:absolute;left:{xs[1]}px;top:{yb - hb - cap}px;width:{bw}px;height:{cap}px;border-radius:24px 24px 0 0;'
          f'background:#ff4b42;box-shadow:0 0 50px rgba(255,75,66,.75);transform-origin:50% 100%;transform:scaleY(0)"></div>'
          f'<div id="nlab" class="din" style="position:absolute;left:{xs[1] + bw // 2 - 500}px;width:1000px;text-align:center;top:{yb - hb - cap - 300}px;'
          f'font-size:260px;line-height:1;color:#ff5a4f;text-shadow:0 10px 40px rgba(0,0,0,.45);opacity:0">{esc(pre)}<span id="nv0">{esc(n)}</span>{esc(post)}</div>')
    dec = len(n.split(".")[1]) if "." in n else 0
    js += [f'tl.fromTo("#ncap",{{scaleY:0}},{{scaleY:1,duration:BAR.dur,ease:BAR.ease}},{tv:.3f});',
           f'tl.to("#nb1",{{backgroundColor:"rgba(255,255,255,.72)",duration:.3,ease:"none"}},{tv:.3f});',
           f'tl.fromTo("#nlab",{{opacity:0,scale:.6,y:40}},{{opacity:1,scale:1,y:0,duration:POP.dur,ease:POP.ease}},{tv + 0.05:.3f});',
           f'tl.fromTo("#nv0",{{innerText:0}},{{innerText:{pct},snap:{{innerText:{10 ** -dec}}},duration:.7,ease:"power2.out",immediateRender:false}},{tv + 0.05:.3f});']
    return b + _src(ev), js


def _num_cut(ev, mock):
    """A day's calories as one bar; on the item's key the chunk at its end cracks and turns red, on "drop" it breaks off and
    falls away, a dashed ghost and ev["flag"] mark the new end, and ev["pills"] ([[text, icon, key], ...]) pop in under it."""
    D, it = ev["dur"], ev["items"][0]
    tv = T(ev, it[2], 0.6) if len(it) > 2 and it[2] else 0.6
    tb = max(T(ev, "drop", tv + 0.75), tv + 0.45)
    x0, y0, BW, BH = 480, 860, 2880, 300; cx = round(BW * (1 - ev.get("share", 0.2))); cw = BW - cx; z = 24
    zig = [(cx + (z if k % 2 == 0 else -z), round(BH * k / 6)) for k in range(7)]
    pts = lambda p: ",".join(f"{x}px {y}px" for x, y in p)
    fill = "linear-gradient(180deg,#ffe766 0%,#f7dc3a 55%,#e9be22 100%)"
    piece = lambda pid, clip, inner: (f'<div id="{pid}" style="position:absolute;left:0;top:0;width:{BW}px;height:{BH}px;border-radius:46px;'
                                      f'background:{fill};clip-path:polygon({clip});box-shadow:inset 0 -12px 0 rgba(0,0,0,.12)">{inner}</div>')
    big = lambda sid, txt, col, op: (f'<div class="din" style="position:absolute;left:{cx}px;width:{cw}px;top:0;height:{BH}px;display:flex;align-items:center;'
                                     f'justify-content:center;font-size:190px;line-height:1"><span id="{sid}" style="color:{col};opacity:{op};padding-top:16px">{txt}</span></div>')
    L = sum(((zig[k + 1][0] - zig[k][0]) ** 2 + (zig[k + 1][1] - zig[k][1]) ** 2) ** 0.5 for k in range(6))
    b = ('<div class="bg"></div>'
         f'<div id="cbar" style="position:absolute;left:{x0}px;top:{y0}px;width:{BW}px;height:{BH}px">'
         + piece("cl", pts([(0, 0)] + zig + [(0, BH)]),
                 f'<div class="avb" style="position:absolute;left:80px;top:0;height:{BH}px;display:flex;align-items:center;font-size:100px;color:#2a1d00">'
                 f'{esc(ev.get("bar_label", "Calories you burn in a day"))}</div>')
         + f'<div id="cgh" style="position:absolute;left:{cx}px;top:0;width:{cw}px;height:{BH}px;border:10px dashed #ff5a4f;border-left:none;border-radius:0 46px 46px 0;'
           f'opacity:0;display:flex;align-items:center;justify-content:center"><span class="din" style="font-size:170px;color:#ff5a4f;line-height:1;padding-top:14px">-{esc(it[0])}</span></div>'
         + piece("cr", pts(zig + [(BW, BH), (BW, 0)]),
                 f'<div id="cred" style="position:absolute;inset:0;background:#e53935;opacity:0"></div>'
                 + big("c500", esc(it[0]), "#1a1200", 1) + big("c500r", "-" + esc(it[0]), "#fff", 0))
         + f'<svg width="{BW}" height="{BH}" viewBox="0 0 {BW} {BH}" style="position:absolute;left:0;top:0;overflow:visible">'
           f'<polyline id="ccrk" points="{" ".join(f"{x},{y}" for x, y in zig)}" fill="none" stroke="#2a1d00" stroke-width="12" stroke-linejoin="round" '
           f'stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}"/></svg></div>'
         + f'<div id="cflag" style="position:absolute;left:{x0 + cx - 600}px;width:1200px;top:{y0 - 330}px;text-align:center;opacity:0">'
           f'<div class="din" style="font-size:150px;line-height:1;color:{Y}">{esc(ev.get("flag", "START HERE"))}</div>'
           f'<div style="width:0;height:0;margin:18px auto 0;border-left:56px solid transparent;border-right:56px solid transparent;border-top:70px solid {Y}"></div></div>'
         + f'<div id="ccap" class="center avb" style="top:{y0 + BH + 80}px;font-size:110px;color:#f2f2f2">{esc(it[0])} {esc(it[1])}</div>')
    js = [f'tl.fromTo("#ccrk",{{strokeDashoffset:{L:.0f}}},{{strokeDashoffset:0,duration:.28,ease:"power2.out"}},{tv:.3f});',
          f'tl.fromTo("#cred",{{opacity:0}},{{opacity:.92,duration:.25,ease:"none"}},{tv + 0.1:.3f});',
          f'tl.fromTo("#c500",{{opacity:1}},{{opacity:0,duration:.2,ease:"none"}},{tv + 0.1:.3f});',
          f'tl.fromTo("#c500r",{{opacity:0}},{{opacity:1,duration:.2,ease:"none"}},{tv + 0.1:.3f});',
          f'tl.fromTo("#cr",{{x:0}},{{x:14,duration:.05,ease:"none",yoyo:true,repeat:5,immediateRender:false}},{tb - 0.32:.3f});',   # it shakes loose
          f'tl.fromTo("#cr",{{x:0,y:0,rotation:0,opacity:1}},{{x:120,y:1150,rotation:24,transformOrigin:"{cx + cw // 2}px {BH // 2}px",duration:.95,'
          f'ease:"power2.in",immediateRender:false}},{tb:.3f});',
          f'tl.to("#cr",{{opacity:0,duration:.3,ease:"none"}},{tb + 0.65:.3f});',
          f'tl.to("#ccrk",{{opacity:0,duration:.15,ease:"none"}},{tb:.3f});',
          f'tl.fromTo("#cgh",{{opacity:0}},{{opacity:1,duration:.3,ease:"none"}},{tb + 0.45:.3f});',
          f'tl.fromTo("#cflag",{{opacity:0,y:-50}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{tb + 0.55:.3f});']
    pills = ev.get("pills", [])
    if pills:
        b += f'<div style="position:absolute;left:0;width:{W}px;top:{y0 + BH + 330}px;display:flex;justify-content:center;gap:80px">'
        for k, (txt, icn, key) in enumerate(pills):
            col = G if icn in ("check", "up") else Y
            b += (f'<div id="cp{k}" class="pill" style="position:relative;--c:{col};--g:{col}66;font-size:100px;padding:30px 58px 30px 40px;border-width:9px;gap:30px;opacity:.25">'
                  f'<svg id="cpi{k}" viewBox="0 0 24 24" style="width:96px;height:96px;opacity:0">{ICON.get(icn, ICON["dot"])}</svg>{esc(txt)}</div>')
            tp = T(ev, key, tb + 1.2 + 1.4 * k)   # on screen dim from the first frame (no empty slide), lit as he says it
            js += [f'tl.fromTo("#cp{k}",{{opacity:.25,scale:.94}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tp:.3f});',
                   f'tl.fromTo("#cpi{k}",{{opacity:0,scale:.4,transformOrigin:"50% 50%"}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tp + 0.06:.3f});']
        b += '</div>'
    return b + _src(ev), js


def _num_calc(ev, mock):
    """Weight x rate = grams, worked for one example: ev["weight"] (lb), ev["rate"] ([low, high] g per lb). The rate lights up on
    the item's key, the answer counts up on "res", ev["stamp"] lands on "stamp", ev["foods"] (asset paths) pop in under it."""
    D, it = ev["dur"], ev["items"][0]
    w = ev.get("weight", 180); lo, hi = ev.get("rate", [0.8, 1.0]); g0, g1 = w * lo, w * hi
    assert abs(g0 - round(g0)) < 1e-9 and abs(g1 - round(g1)) < 1e-9, "pick an example weight that gives whole grams"
    tv = T(ev, it[2], 0.6) if len(it) > 2 and it[2] else 0.6
    tr = max(T(ev, "res", tv + 1.3), tv + 0.5); ts = max(T(ev, "stamp", tr + 1.0), tr + 0.6)
    b, js = '<div class="bg"></div>', []
    if ev.get("title"):
        b += f'<div id="nt" class="center din" style="top:260px;font-size:150px">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#nt",{y:-30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    col = lambda cid, cap, val, color, op: (f'<div id="{cid}" style="display:flex;flex-direction:column;align-items:center;opacity:{op}">'
                                            f'<div class="avb" style="font-size:80px;color:#d8d8d8;margin-bottom:12px">{cap}</div>'
                                            f'<div class="din" style="font-size:280px;line-height:1;color:{color};white-space:nowrap">{val}</div></div>')
    sym = lambda sid, s: f'<div id="{sid}" class="din" style="font-size:220px;line-height:1;color:#a8a8a8;padding-bottom:26px;opacity:.3">{s}</div>'
    res = (f'<span style="position:relative;display:inline-block"><span id="rq" style="position:absolute;left:0;right:0;text-align:center">?</span>'
           f'<span id="rv" style="display:inline-block;opacity:0"><span id="rv0">{round(g0)}</span> to <span id="rv1">{round(g1)}</span> g</span></span>')
    b += (f'<div style="position:absolute;left:0;width:{W}px;top:{ev.get("row_top", 560)}px;display:flex;justify-content:center;align-items:flex-end;gap:80px">'
          + col("ca", esc(ev.get("cap_w", "You weigh")), f"{w} lb", "#fff", 1) + sym("cx", "x")
          + col("cb", esc(ev.get("cap_r", "Grams per lb")), f"{lo:g} to {hi:g}", Y, .3) + sym("ce", "=")
          + col("cc", esc(ev.get("cap_g", "Protein a day")), res, "#fff", .3) + '</div>')
    js += [f'tl.fromTo(["#cx","#cb"],{{opacity:.3}},{{opacity:1,duration:.2,ease:"none"}},{tv:.3f});',
           f'tl.fromTo("#cb",{{scale:.85}},{{scale:1,duration:POP.dur,ease:POP.ease,immediateRender:false}},{tv:.3f});',
           f'tl.fromTo(["#ce","#cc"],{{opacity:.3}},{{opacity:1,duration:.2,ease:"none"}},{tr:.3f});',
           f'tl.fromTo("#rq",{{opacity:1}},{{opacity:0,duration:.12,ease:"none"}},{tr:.3f});',
           f'tl.fromTo("#rv",{{opacity:0,scale:.8}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tr:.3f});',
           f'tl.fromTo("#rv0",{{innerText:0}},{{innerText:{round(g0)},snap:{{innerText:1}},duration:.8,ease:"power2.out",immediateRender:false}},{tr:.3f});',
           f'tl.fromTo("#rv1",{{innerText:0}},{{innerText:{round(g1)},snap:{{innerText:1}},duration:.8,ease:"power2.out",immediateRender:false}},{tr:.3f});']
    foods = ev.get("foods", [])
    if foods:
        nf, d, gap = len(foods), 330, 110; fx = (W - (nf * d + (nf - 1) * gap)) // 2; fy = ev.get("foods_top", 1460)
        for k, f in enumerate(foods):
            b += (f'<div id="cf{k}" style="position:absolute;left:{fx + k * (d + gap)}px;top:{fy}px;width:{d}px;height:{d}px;border-radius:50%;overflow:hidden;'
                  f'box-shadow:0 0 0 12px #fff,0 24px 60px rgba(0,0,0,.6);opacity:.28;filter:saturate(.2)">' + _img(f, "width:100%;height:100%;object-fit:cover") + '</div>')
            js.append(f'tl.fromTo("#cf{k}",{{opacity:.28,scale:.9,filter:"saturate(.2)"}},{{opacity:1,scale:1,filter:"saturate(1)",duration:POP.dur,ease:POP.ease}},{tr + 0.35 + 0.12 * k:.3f});')
    if ev.get("stamp"):
        b += (f'<div id="cst" style="position:absolute;left:{W // 2 - 900}px;width:1800px;top:{ev.get("stamp_top", 1110)}px;text-align:center;opacity:0">'
              f'<span class="din" style="display:inline-block;font-size:170px;line-height:1;color:#ff4b42;border:16px solid #ff4b42;border-radius:26px;'
              f'padding:30px 60px 10px;transform:rotate(-6deg);background:rgba(20,0,0,.28)">{esc(ev["stamp"])}</span></div>')
        js.append(f'tl.fromTo("#cst",{{opacity:0,scale:1.7}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ts:.3f});')
    return b + _src(ev), js


NUM_ANIM = {"clock": _num_clock, "cut": _num_cut, "calc": _num_calc}


# ------------------------------------------------------------------------------------------------ math
def math(ev, mock):
    """ev["lines"]: [[left, right, at-key], ...] built one by one (right side in yellow); ev["gauge"]: {"from", "to", "limit",
    "limit_label", "min", "max", "label", "at", "ticks": [[value, text], ...], "marks": [[value, at-key, colour?], ...]} a number line
    where the marker slides from->to; marks are fixed points that pop on as they're said."""
    D, lines = ev["dur"], ev["lines"]
    b, js = '<div class="bg"></div>', []
    top = 260 if ev.get("gauge") else 420
    if ev.get("title"):
        b += f'<div id="mt" class="din" style="position:absolute;left:300px;top:{top - 40}px;font-size:120px;color:#e8e8e8">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#mt",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);')
        top += 190
    dy = 250 if len(lines) <= 3 else 205
    fs = 180 if len(lines) <= 3 else 150
    # C4367 v4 (OB 10-20: "adding a photo of the bars themselves with the flavors to match would help, for the calories"): a line may
    # carry a 4th field, a photo tile (assets path, 2.65:1) that sits before it and lights up with it; ev["side_img"] puts one tile
    # beside the whole card (a card about one flavor)
    has_img = any(len(x) > 3 and x[3] for x in lines)
    IH = int(dy * 0.8); IW = int(IH * 2.65); tx = 300 + (IW + 56 if has_img else 0)
    for k, ln in enumerate(lines):
        l, r, key = ln[0], ln[1], ln[2]; img = ln[3] if len(ln) > 3 else None
        last = k == len(lines) - 1 and ev.get("total", True)
        # v3 (OB 10-20: no empty or static slides): the whole sum is on screen from the first frame, dimmed; each line lights
        # up and its answer pops in as he says it
        b += (f'<div id="ml{k}" class="din" style="position:absolute;left:{tx}px;top:{top + k * dy}px;font-size:{fs + (30 if last else 0)}px;white-space:nowrap">'
              f'<span id="mlL{k}" style="opacity:.26">{esc(l)}</span> <span id="mlR{k}" style="display:inline-block;color:{Y};opacity:0;transform-origin:0 60%">{esc(r)}</span></div>')
        t0 = T(ev, key, 0.15 + 0.8 * k) if key else 0.15 + 0.8 * k
        if img:
            b += (f'<img id="mi{k}" src="../assets/{img}" style="position:absolute;left:300px;top:{top + k * dy + (fs * 1.18 - IH) / 2:.0f}px;width:{IW}px;height:{IH}px;'
                  f'object-fit:cover;border-radius:16px;box-shadow:0 14px 40px rgba(0,0,0,.55);opacity:.3;transform-origin:50% 50%"/>')
            js.append(f'tl.fromTo("#mi{k}",{{opacity:.3,scale:.92}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t0:.3f});')
        js += [f'tl.fromTo("#mlL{k}",{{opacity:.26,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{t0:.3f});',
               f'tl.fromTo("#mlR{k}",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t0 + 0.12:.3f});']
    if ev.get("side_img"):
        b += (f'<img id="msi" src="../assets/{ev["side_img"]}" style="position:absolute;left:2440px;top:{ev.get("side_top", 400)}px;width:1100px;height:415px;object-fit:cover;'
              f'border-radius:22px;box-shadow:0 30px 90px rgba(0,0,0,.6);transform:rotate(-2deg);opacity:0"/>')
        js.append('tl.fromTo("#msi",{opacity:0,scale:.9,y:30},{opacity:1,scale:1,y:0,duration:POP.dur,ease:POP.ease},.1);')
    g = ev.get("gauge")
    if g:
        x0, x1, gy = 300, 3540, 1720
        X = lambda v: x0 + (v - g["min"]) / (g["max"] - g["min"]) * (x1 - x0)
        ticks = "".join(f'<div style="position:absolute;left:{X(v) - 3:.0f}px;top:{gy - 40}px;width:6px;height:80px;background:#9a9a9a"></div>'
                        f'<div class="av" style="position:absolute;left:{X(v) - 300:.0f}px;width:600px;text-align:center;top:{gy + 60}px;font-size:56px;color:#bdbdbd">{esc(t)}</div>'
                        for v, t in g.get("ticks", []))
        lim = (f'<div id="mlim" style="position:absolute;left:{X(g["limit"]) - 8:.0f}px;top:{gy - 300}px;width:16px;height:420px;'
               f'background:repeating-linear-gradient({R} 0 34px, transparent 34px 54px)"></div>'
               f'<div id="mliml" class="avb" style="position:absolute;left:{X(g["limit"]) + 40:.0f}px;width:1300px;top:{gy - 330}px;font-size:76px;color:{R}">{esc(g.get("limit_label", ""))}</div>') if "limit" in g else ""
        b += (f'<div id="mg" style="opacity:0"><div style="position:absolute;left:{x0}px;top:{gy - 6}px;width:{x1 - x0}px;height:12px;border-radius:6px;background:#5a5a5a"></div>'
              f'{ticks}{lim}'
              f'<div id="mpin" style="position:absolute;left:{X(g["from"]) - 44:.0f}px;top:{gy - 44}px;width:88px;height:88px;border-radius:44px;background:{Y};'
              f'box-shadow:0 0 0 10px rgba(247,220,58,.25)"></div>'
              f'<div id="mpl" class="din" style="position:absolute;left:{X(g["from"]) - 400:.0f}px;width:800px;text-align:center;top:{gy - 250}px;font-size:150px;color:{Y}">'
              f'<span id="mpv">{g["from"]}</span></div></div>')
        for j, mk in enumerate(g.get("marks", [])):   # fixed markers that pop onto the line on their words (C4367 reshoot: all four flavors)
            v, key = mk[0], mk[1]; col = mk[2] if len(mk) > 2 else "#fff"
            b += (f'<div id="mk{j}" style="position:absolute;left:{X(v) - 30:.0f}px;top:{gy - 30}px;width:60px;height:60px;border-radius:30px;background:{col};'
                  f'box-shadow:0 0 0 8px rgba(255,255,255,.18);opacity:0"></div>'
                  f'<div id="mkl{j}" class="din" style="position:absolute;left:{X(v) - 150:.0f}px;width:300px;text-align:center;top:{gy - 150 - 95 * (j % 2)}px;'
                  f'font-size:84px;color:{col};opacity:0">{v}</div>')
            tm = T(ev, key, D * 0.6) + 0.12 * j
            js += [f'tl.fromTo("#mk{j}",{{opacity:0,scale:.2}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tm:.3f});',
                   f'tl.fromTo("#mkl{j}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tm + 0.06:.3f});']
        tg = T(ev, g.get("at", "gauge"), D * 0.5)
        js += [f'tl.fromTo("#mg",{{opacity:0}},{{opacity:1,duration:.25,ease:"none"}},{max(0, tg - 0.9):.3f});',
               f'tl.to(["#mpin","#mpl"],{{x:{X(g["to"]) - X(g["from"]):.0f},duration:SLIDE.dur*1.6,ease:SLIDE.ease}},{tg:.3f});',
               f'tl.fromTo("#mpv",{{innerText:{g["from"]}}},{{innerText:{g["to"]},snap:{{innerText:1}},duration:SLIDE.dur*1.6,ease:SLIDE.ease,immediateRender:false}},{tg:.3f});']
    if ev.get("source"):
        b += f'<div class="av" style="position:absolute;left:300px;top:2040px;font-size:48px;color:#8f8f8f">{esc(ev["source"])}</div>'
    return b, js


# ------------------------------------------------------------------------------------------------ dose
def _dose_v1(ev, mock):
    """The EPG dose ladder (Davidson & Bechtel 2014: 139 people, 8 weeks, 10 / 25 / 40 g a day). A 0-60 g axis with the
    three trial doses as zones, then pins: ev["pins"] = [[grams, text, at-key, colour?], ...]; ev["show"] picks zones."""
    D = ev["dur"]; x0, x1, ay = 360, 3480, 1500   # v3: taller zones, lower axis (fills the frame)
    gmax = ev.get("gmax", 60)
    X = lambda g: x0 + g / gmax * (x1 - x0)
    zones = [(0, 10, G, "10 g", "“reasonably well tolerated”"), (10, 25, A_, "25 g", "more gut complaints"), (25, 40, R, "40 g", "the most complaints")]
    b = ('<div class="bg"></div>'
         f'<div id="dt" class="din" style="position:absolute;left:{x0}px;top:170px;font-size:170px">{esc(ev.get("title", "EPG per day"))}</div>'
         f'<div id="ds" class="av" style="position:absolute;left:{x0 + 4}px;top:380px;font-size:66px;color:#d0d0d0">{esc(ev.get("sub", "8-week trial, 139 people (Davidson & Bechtel 2014)"))}</div>'
         f'<div style="position:absolute;left:{x0}px;top:{ay}px;width:{x1 - x0}px;height:14px;border-radius:7px;background:#4a4a4a"></div>')
    js = ['tl.fromTo("#dt",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);']
    pinned = [p[0] for p in ev.get("pins", []) if isinstance(p[0], (int, float))]   # a pin on a tick says the value itself
    for g_ in range(0, gmax + 1, 10):
        if any(abs(g_ - v) < 1.5 for v in pinned): lab_ = ""
        else: lab_ = f"{g_} g"
        b += (f'<div class="av" style="position:absolute;left:{X(g_) - 150:.0f}px;width:300px;text-align:center;top:{ay + 60}px;font-size:56px;color:#9a9a9a">{lab_}</div>'
              f'<div style="position:absolute;left:{X(g_) - 3:.0f}px;top:{ay - 18}px;width:6px;height:50px;background:#7a7a7a"></div>')
    for k, (a, c, col, lab, txt) in enumerate(zones):
        zt = T(ev, f"z{k}", 0.3 + 0.5 * k)
        b += (f'<div id="dz{k}" style="position:absolute;left:{X(a):.0f}px;top:{ay - 560}px;width:{X(c) - X(a) - 10:.0f}px;height:530px;border-radius:28px 28px 0 0;'
              f'background:{col};opacity:.92;transform-origin:50% 100%"></div>'
              f'<div id="dl{k}" style="position:absolute;left:{X(a):.0f}px;width:{max(X(c) - X(a), 620):.0f}px;top:{ay - 880}px">'   # tops aligned; room for a two-line note above the bar
              f'<div class="din" style="font-size:150px;line-height:1.05;color:{col}">{lab}</div><div class="avb" style="font-size:62px;line-height:1.15;color:#f0f0f0">{esc(txt)}</div></div>')
        js += [f'tl.fromTo("#dz{k}",{{scaleY:.001}},{{scaleY:1,duration:BAR.dur,ease:BAR.ease}},{zt:.3f});',
               f'tl.fromTo("#dl{k}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{zt + 0.12:.3f});']
    for k, p in enumerate(ev.get("pins", [])):
        gr, txt, key = p[0], p[1], p[2]; col = p[3] if len(p) > 3 else "#fff"
        pt = T(ev, key, D * 0.5 + 0.6 * k)
        lo, hi = (gr if isinstance(gr, (int, float)) else gr[0]), (gr if isinstance(gr, (int, float)) else gr[1])
        xa, xb = X(lo), X(hi)
        span = (f'<div style="position:absolute;left:{xa:.0f}px;top:{ay + 170}px;width:{max(xb - xa, 12):.0f}px;height:24px;border-radius:12px;background:{col}"></div>')
        cx, half = (xa + xb) / 2, len(str(txt)) * 24   # ~half the label's width at 110 px DIN: keep it inside the frame
        lx, al = cx - 700, "center"
        if cx + half > W - 140: lx, al = W - 140 - 1400, "right"
        elif cx - half < 140: lx, al = 140, "left"
        b += (f'<div id="dp{k}" style="opacity:0">{span}'
              f'<div style="position:absolute;left:{(xa + xb) / 2 - 6:.0f}px;top:{ay + 26}px;width:12px;height:150px;background:{col}"></div>'
              f'<div class="din" style="position:absolute;left:{lx:.0f}px;width:1400px;text-align:{al};top:{ay + 200 + 140 * (k % 2)}px;'
              f'font-size:115px;color:{col}">{esc(txt)}</div></div>')
        js.append(f'tl.fromTo("#dp{k}",{{opacity:0,y:-40}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{pt:.3f});')
    if ev.get("sun"):
        st = T(ev, "sun", D * 0.6)
        b += (f'<svg id="dsun" style="position:absolute;left:3220px;top:180px" width="420" height="420" viewBox="0 0 24 24" fill="none" stroke="{Y}" '
              f'stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4.4" fill="{Y}"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1"/></svg>')
        js += [f'tl.fromTo("#dsun",{{scale:.001,rotation:-40,transformOrigin:"50% 50%"}},{{scale:1,rotation:0,duration:POP.dur,ease:POP.ease}},{st:.3f});',
               f'tl.to("#dsun",{{rotation:30,duration:{max(0.5, D - st):.3f},ease:"none"}},{st + 0.4:.3f});']
    return b, js


def dose(ev, mock):
    """The EPG dose ladder, v2 (OB 10-20 on the breakdown: "make a better animation and upgrade here as well, really search the web").
    Amounts as heights (the research: values as stacked units read without effort; Rosling's box-by-box): one column per trial dose
    (10 / 25 / 40 g a day, Davidson & Bechtel 2014), each built of 1 g slices, rising with its gram counter as he says it, its
    zone band lighting behind it; dashed outlines from frame one so the card is never empty. Pins: a number draws a line across the
    chart, a range draws a bracket; ev["chips"] = [[text, at-key, icon], ...] stack symptom chips on the bracket as he names them.
    ev["bars"] = [[count, at-key], ...] drops real David bars (photos/bar_*.jpg; 1 bar = 10 g on this axis, the estimate from the
    complaint's table) into a "your bars" column with free-fall and a squash; the 40 g line flashes red when the stack passes it."""
    if ev.get("style") == "v1": return _dose_v1(ev, mock)
    D = ev["dur"]; gmax = ev.get("gmax", 60)
    x0, x1, y0, ytop = 520, 3500, 1840, 640; pxg = (y0 - ytop) / gmax
    Yg = lambda g: y0 - g * pxg
    doses = [(10, G, "“reasonably well tolerated”"), (25, A_, "more gut complaints"), (40, R, "the most complaints")]
    bars = ev.get("bars") or []; chips = ev.get("chips") or []
    cw, gap, cx0 = 400, 110, x0 + 120
    CX = lambda k: cx0 + k * (cw + gap)
    bx = CX(3) + 90; bw = int(round(10 * pxg * 2.65))            # the bars column: one tile = 10 g tall
    lx = (bx + bw + 90) if bars else (CX(3) + 120)             # where pin labels and chips sit
    short = T(ev, "z0", 0.3) < 0.3
    b = ('<div class="bg"></div>'
         f'<div id="dt" class="din" style="position:absolute;left:{x0 - 220}px;top:120px;font-size:150px">{esc(ev.get("title", "EPG per day"))}</div>'
         + (f'<div id="ds" class="av" style="position:absolute;left:{x0 - 216}px;top:300px;font-size:60px;color:#d0d0d0">{esc(ev.get("sub", "8-week trial, 139 people (Davidson & Bechtel 2014)"))}</div>' if ev.get("sub", True) else ""))
    js = ['tl.fromTo("#dt",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);']
    # zone bands, gridlines, axis labels
    for k, (lo, hi, col) in enumerate(((0, 10, G), (10, 25, A_), (25, gmax, R))):
        b += f'<div id="dzb{k}" style="position:absolute;left:{x0}px;top:{Yg(hi):.0f}px;width:{x1 - x0}px;height:{(hi - lo) * pxg:.0f}px;background:{col};opacity:.07"></div>'
    for g_ in (10, 25, 40):
        b += (f'<div id="dln{g_}" style="position:absolute;left:{x0}px;top:{Yg(g_) - 2:.0f}px;width:{x1 - x0}px;height:0;border-top:5px dashed rgba(255,255,255,.42)"></div>')
    for g_, col in ((0, "#9a9a9a"), (10, G), (25, A_), (40, R), (gmax, "#9a9a9a")):
        b += f'<div class="din" style="position:absolute;left:{x0 - 330}px;width:300px;text-align:right;top:{Yg(g_) - 42:.0f}px;font-size:84px;color:{col}">{g_} g</div>'
    b += f'<div style="position:absolute;left:{x0}px;top:{y0 - 4}px;width:{x1 - x0}px;height:10px;border-radius:5px;background:#5a5a5a"></div>'
    # the trial's three columns
    for k, (g_, col, txt) in enumerate(doses):
        h = g_ * pxg; zt = T(ev, f"z{k}", 0.3 + 0.5 * k)
        b += (f'<div style="position:absolute;left:{CX(k)}px;top:{y0 - h:.0f}px;width:{cw}px;height:{h:.0f}px;border:5px dashed rgba(255,255,255,.28);border-bottom:0;'
              f'border-radius:22px 22px 0 0;box-sizing:border-box"></div>'
              f'<div id="dc{k}" style="position:absolute;left:{CX(k)}px;top:{y0 - h:.0f}px;width:{cw}px;height:{h:.0f}px;border-radius:22px 22px 0 0;'
              f'background:repeating-linear-gradient(to top,rgba(0,0,0,.2) 0 3px,rgba(0,0,0,0) 3px {pxg:.2f}px),linear-gradient({col},{col}cc);'
              f'box-shadow:0 0 60px {col}55;transform-origin:50% 100%"></div>'
              f'<div id="dcl{k}" class="din" style="position:absolute;left:{CX(k) - 100}px;width:{cw + 200}px;text-align:center;top:{y0 - h - 180:.0f}px;font-size:150px;color:{col};opacity:0">'
              f'<span id="dcv{k}">{g_}</span> g</div>'
              f'<div id="dcd{k}" class="avb" style="position:absolute;left:{CX(k) - 40}px;width:{cw + 80}px;text-align:center;top:{y0 + 34}px;font-size:54px;line-height:1.15;color:#e8e8e8;opacity:0">{esc(txt)}</div>')
        js += [f'tl.fromTo("#dc{k}",{{scaleY:{0.6 if short else 0.001}}},{{scaleY:1,duration:BAR.dur,ease:BAR.ease}},{zt:.3f});',
               f'tl.fromTo("#dcl{k}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{zt + 0.05:.3f});',
               f'tl.fromTo("#dcv{k}",{{innerText:0}},{{innerText:{g_},snap:{{innerText:1}},duration:.7,ease:"power2.out",immediateRender:false}},{zt + 0.05:.3f});',
               f'tl.fromTo("#dcd{k}",{{opacity:0}},{{opacity:1,duration:.3,ease:"none"}},{zt + 0.2:.3f});',
               f'tl.to("#dzb{k}",{{opacity:.2,duration:.4,ease:"none"}},{zt + 0.1:.3f});']
    # pins: a number = a line across the chart; a range = a bracket (with chips, when given)
    for k, p in enumerate(ev.get("pins", [])):
        gr, txt, key = p[0], p[1], p[2]; col = p[3] if len(p) > 3 else "#fff"; pt = T(ev, key, D * 0.5 + 0.6 * k)
        if isinstance(gr, (int, float)):
            yy = Yg(gr)
            b += (f'<div id="dp{k}" style="opacity:0"><div style="position:absolute;left:{x0}px;top:{yy - 5:.0f}px;width:{lx - x0 - 30}px;height:10px;border-radius:5px;background:{col};box-shadow:0 0 30px {col}88"></div>'
                  f'<div class="din" style="position:absolute;left:{lx}px;width:{W - lx - 120}px;top:{yy - 70:.0f}px;font-size:110px;line-height:1;text-wrap:balance;color:{col};text-shadow:0 6px 30px rgba(0,0,0,.6)">{esc(txt)}</div></div>')
            js += [f'tl.fromTo("#dp{k}",{{opacity:0,x:-60}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{pt:.3f});']
        else:
            ya, yb = Yg(gr[1]), Yg(gr[0]); bxk = lx - 60
            b += (f'<div id="dp{k}" style="opacity:0"><div style="position:absolute;left:{bxk}px;top:{ya:.0f}px;width:14px;height:{yb - ya:.0f}px;border-radius:7px;background:{col}"></div>'
                  f'<div style="position:absolute;left:{bxk - 30}px;top:{ya - 5:.0f}px;width:44px;height:10px;border-radius:5px;background:{col}"></div>'
                  f'<div style="position:absolute;left:{bxk - 30}px;top:{yb - 5:.0f}px;width:44px;height:10px;border-radius:5px;background:{col}"></div>')
            if not chips:
                b += f'<div class="din" style="position:absolute;left:{lx}px;width:{W - lx - 120}px;top:{(ya + yb) / 2 - 60:.0f}px;font-size:104px;line-height:1.02;text-wrap:balance;color:{col};text-shadow:0 6px 30px rgba(0,0,0,.6)">{esc(txt)}</div>'
            b += '</div>'
            js += [f'tl.fromTo("#dp{k}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{pt:.3f});']
    for j, c in enumerate(chips):
        ct = T(ev, c[1], D * 0.6 + 0.5 * j); top = Yg(gmax) + 40 + j * 175
        ico = {"wind": '<path d="M3 8h11a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h8"/>', "drop": '<path d="M12 3c-3.5 4.6-6 7.7-6 10.6a6 6 0 0 0 12 0C18 10.7 15.5 7.6 12 3z"/>'}.get(c[2] if len(c) > 2 else "", "")
        b += (f'<div id="dch{j}" style="position:absolute;left:{lx}px;top:{top:.0f}px;display:flex;align-items:center;gap:30px;padding:18px 48px 18px 34px;'
              f'background:rgba(10,10,10,.72);border-left:14px solid {R};border-radius:16px;opacity:0">'
              + (f'<svg width="84" height="84" viewBox="0 0 24 24" fill="none" stroke="#ff8a7a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ico}</svg>' if ico else "")
              + f'<span class="din" style="font-size:104px;line-height:1">{esc(c[0])}</span></div>')
        js.append(f'tl.fromTo("#dch{j}",{{opacity:0,x:70}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{ct - 0.05:.3f});')
    if chips and ev.get("shudder_at"):
        st = T(ev, ev["shudder_at"], D - 0.6)
        js.append(f'tl.fromTo([{",".join(chr(34) + f"#dch{j}" + chr(34) for j in range(len(chips)))}],{{x:0}},{{x:9,duration:.06,ease:"none",yoyo:true,repeat:5,immediateRender:false}},{st:.3f});')
    # bars dropping into "your bars"
    if bars:
        flav = ["photos/bar_blueberry.jpg", "photos/bar_cakebatter.jpg", "photos/bar_redvelvet.jpg", "photos/bar_pbchunk.jpg"]
        th = 10 * pxg; i = 0; crossed = False
        b += (f'<div class="avb" style="position:absolute;left:{bx - 60}px;width:{bw + 120}px;text-align:center;top:{y0 + 34}px;font-size:58px;color:{Y}">my bars a day</div>')
        for cnt, key in bars:
            t0 = T(ev, key, D * 0.5)
            for m in range(int(cnt)):
                top = y0 - (i + 1) * th; tl0 = t0 + 0.09 * m; tilt = (-1.4, 1.2, -0.8, 1.5, -1.1, 0.9)[i % 6]
                b += (f'<img id="db{i}" src="../assets/{flav[i % 4]}" style="position:absolute;left:{bx}px;top:{top:.0f}px;width:{bw}px;height:{th:.0f}px;object-fit:cover;'
                      f'border-radius:12px;box-shadow:0 10px 26px rgba(0,0,0,.5);transform-origin:50% 100%;transform:rotate({tilt}deg);opacity:0"/>')
                js += [f'tl.fromTo("#db{i}",{{y:{-(top + th + 120):.0f},opacity:1}},{{y:0,opacity:1,duration:.32,ease:"power2.in",immediateRender:false}},{tl0:.3f});',
                       f'tl.set("#db{i}",{{opacity:0}},0);',
                       f'tl.fromTo("#db{i}",{{scaleY:.9}},{{scaleY:1,duration:.18,ease:"power2.out",immediateRender:false}},{tl0 + 0.32:.3f});']
                i += 1
                if not crossed and i * 10 > 40:
                    crossed = True
                    js.append(f'tl.fromTo("#dln40",{{borderTopColor:"rgba(255,255,255,.42)"}},{{borderTopColor:"{R}",duration:.15,ease:"none",yoyo:true,repeat:3,immediateRender:false}},{tl0 + 0.32:.3f});')
    return b, js


# ------------------------------------------------------------------------------------------------ coins
def coins(ev, mock):
    """FACE VALUE (9 gold coins stack, one per calorie) vs WHAT YOUR BODY SPENDS (a 0.7 sliver).
    v3 (OB 10-20: no empty slides): the gold stack builds in the first second ("it looks and tastes like fat"), a dashed outline of
    one coin waits on the right, the 0.7 sliver drops into it on "pennies on the dollar" (at key body), "9 cal" lands on "face
    value" (at key face) with a pulse of the stack."""
    D = ev["dur"]; tf, tb = T(ev, "face", D * 0.85), T(ev, "body", max(1.2, D * 0.55)); t0 = 0.35
    cw, chh, dy = 620, 84, 112
    coin = lambda i, x, y, extra="": (f'<div class="cn" id="{i}" style="position:absolute;left:{x}px;top:{y}px;width:{cw}px;height:{chh}px;border-radius:{chh // 2}px / {chh // 3}px;'
                                      f'background:linear-gradient(#ffe680,#d4a514 60%,#a77d06);box-shadow:inset 0 -12px 0 rgba(0,0,0,.18),0 10px 22px rgba(0,0,0,.45){extra}"></div>')
    LX, RX, BASE = 960, 2260, 1660
    b = '<div class="bg"></div>'
    b += f'<div id="ct" class="center din" style="top:150px;font-size:170px">{esc(ev.get("title", "One gram of EPG"))}</div>'
    b += (f'<div style="position:absolute;left:{LX + cw // 2 - 700}px;top:400px;width:1400px;text-align:center"><div class="avb" style="font-size:88px;line-height:1.15;color:#f0f0f0">'
          f'{esc(ev.get("left_label", "The lawsuit counted it as"))}</div></div>'
          f'<div style="position:absolute;left:{RX + cw // 2 - 700}px;top:400px;width:1400px;text-align:center"><div class="avb" style="font-size:88px;line-height:1.15;color:#f0f0f0">'
          f'{esc(ev.get("right_label", "Your body gets about"))}</div></div>')
    js = ['tl.fromTo("#ct",{y:-30,opacity:0},{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease},0);']
    b += '<div id="stack" style="position:absolute;inset:0;transform-origin:%dpx %dpx">' % (LX + cw // 2, BASE)
    for k in range(9):
        b += coin(f"c{k}", LX, BASE - k * dy)
        js.append(f'tl.fromTo("#c{k}",{{y:-300,opacity:0}},{{y:0,opacity:1,duration:.3,ease:p=>p*p}},{t0 + 0.09 * k:.3f});')
    b += '</div>'
    b += (f'<div id="ghost" style="position:absolute;left:{RX}px;top:{BASE}px;width:{cw}px;height:{chh}px;border-radius:{chh // 2}px / {chh // 3}px;'
          f'border:8px dashed rgba(255,255,255,.45);box-sizing:border-box"></div>')
    js.append(f'tl.fromTo("#ghost",{{opacity:0}},{{opacity:1,duration:.4,ease:"none"}},{t0 + 0.6:.3f});')
    b += coin("cs", RX, BASE, ";clip-path:inset(0 30% 0 0)")   # 0.7 of one coin
    b += (f'<div id="cv1" class="din" style="position:absolute;left:{LX + cw // 2 - 600}px;width:1200px;text-align:center;top:{BASE + 130}px;font-size:220px;color:{Y};opacity:0">9 cal</div>'
          f'<div id="cv2" class="din" style="position:absolute;left:{RX + cw // 2 - 600}px;width:1200px;text-align:center;top:{BASE + 130}px;font-size:220px;color:{Y};opacity:0">0.7 cal</div>')
    js += [f'tl.fromTo("#cs",{{y:-320,opacity:0}},{{y:0,opacity:1,duration:.34,ease:p=>p*p}},{tb:.3f});',
           f'tl.fromTo("#cv2",{{opacity:0,scale:.8}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tb + 0.3:.3f});',
           f'tl.fromTo("#cv1",{{opacity:0,scale:.8}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tf:.3f});',
           f'tl.fromTo("#stack",{{scale:1}},{{scale:1.05,duration:.22,ease:"power2.out",yoyo:true,repeat:1,immediateRender:false}},{tf:.3f});']
    if ev.get("source"):
        b += f'<div class="av" style="position:absolute;left:200px;top:2060px;font-size:46px;color:#8f8f8f">{esc(ev["source"])}</div>'
    return b, js


# ------------------------------------------------------------------------------------------------ timeline
def timeline(ev, mock):
    """ev["points"]: [[year, title, sub, at-key, photo?], ...] along a line drawn left to right."""
    D, pts = ev["dur"], ev["points"]; n = len(pts); x0, x1, ly = 780, 3060, 1240
    X = lambda k: x0 + (x1 - x0) * (k / max(n - 1, 1))
    b = ('<div class="bg"></div>'
         + (f'<div id="tlt" class="center din" style="top:{200 if any(len(p) > 4 and p[4] for p in pts) else 380}px;font-size:160px">{esc(ev["title"])}</div>' if ev.get("title") else "")
         + f'<div id="tll" style="position:absolute;left:{x0}px;top:{ly - 7}px;width:{x1 - x0}px;height:14px;border-radius:7px;background:{Y};transform-origin:0 50%"></div>')
    js = [f'tl.fromTo("#tll",{{scaleX:.001}},{{scaleX:1,duration:{max(1.2, min(D - 0.6, T(ev, pts[-1][3], D * 0.7) + 0.2)):.3f},ease:"none"}},0);']
    for k, p in enumerate(pts):
        yr, title, sub, key = p[0], p[1], p[2], p[3]
        t0 = T(ev, key, 0.2 + 0.9 * k) if key else 0.2 + 0.9 * k
        ph = (f'<div style="width:520px;height:520px;margin:0 auto 30px;border-radius:36px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.6);background:#fff">'
              + _img(_asset(p[4]), "width:100%;height:100%;object-fit:cover") + '</div>') if len(p) > 4 and p[4] else ""
        top = ly - (900 if ph else 360)
        b += (f'<div id="td{k}" style="position:absolute;left:{X(k) - 46:.0f}px;top:{ly - 46}px;width:92px;height:92px;border-radius:46px;background:{Y};'
              f'box-shadow:0 0 0 14px rgba(247,220,58,.22)"></div>'
              f'<div id="tp{k}" style="position:absolute;left:{X(k) - 560:.0f}px;width:1120px;text-align:center;top:{top}px">{ph}'
              f'<div class="din" style="font-size:170px;line-height:1;color:{Y}">{esc(yr)}</div></div>'
              f'<div id="tq{k}" style="position:absolute;left:{X(k) - 560:.0f}px;width:1120px;text-align:center;top:{ly + 110}px">'
              f'<div class="din" style="font-size:120px;line-height:1.05">{esc(title)}</div>'
              f'<div class="avb" style="font-size:62px;color:#d6d6d6;margin-top:16px">{esc(sub)}</div></div>')
        js += [f'tl.fromTo("#td{k}",{{scale:.001}},{{scale:1,duration:POP.dur,ease:POP.ease}},{t0:.3f});',
               f'tl.fromTo(["#tp{k}","#tq{k}"],{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{t0 + 0.05:.3f});']
    return b, js


# ------------------------------------------------------------------------------------------------ title
def title(ev, mock):
    D = ev["dur"]
    chips = "".join(f'<div class="ch" id="ch{k}" style="display:flex;align-items:center;gap:22px;background:rgba(0,0,0,.78);border:4px solid {Y};'
                    f'border-radius:22px;padding:20px 36px;white-space:nowrap"><span class="din" style="font-size:76px;color:{Y}">{k + 1}</span>'
                    f'<span class="avb" style="font-size:58px">{esc(c)}</span></div>' for k, c in enumerate(ev.get("chips", [])))
    img = (f'<div id="tim" style="position:absolute;left:2380px;top:430px;width:1260px;height:1260px;border-radius:40px;overflow:hidden;box-shadow:0 40px 120px rgba(0,0,0,.55)">'
           + _img(_asset(ev["image"]), "width:100%;height:100%;object-fit:cover") + '</div>') if ev.get("image") else ""
    b = (f'<div style="position:absolute;inset:0;background:radial-gradient(circle at 30% 30%,#ffe9a3 0%,#e2b43a 35%,#b07d12 70%,#6e4a05 100%)"></div>'
         f'<div id="gl" style="position:absolute;left:-1600px;top:0;width:1200px;height:{H}px;background:linear-gradient(100deg,rgba(255,255,255,0),rgba(255,255,255,.38),rgba(255,255,255,0));transform:skewX(-14deg)"></div>'
         f'{img}'
         f'<div id="tt" style="position:absolute;left:240px;top:470px;width:2100px;color:#111">'
         f'<div class="din" style="font-size:250px;line-height:.95">{esc(ev["line1"])}</div>'
         f'<div class="din" style="font-size:150px;line-height:1.02;margin-top:40px">{esc(ev["line2"])}</div></div>'
         f'<div id="chips" style="position:absolute;left:240px;top:1520px;width:3400px;display:flex;flex-wrap:wrap;gap:30px">{chips}</div>')
    js = ['tl.fromTo("#tt",{y:50},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
          f'tl.fromTo("#gl",{{x:0}},{{x:{W + 2400},duration:{min(1.6, D):.3f},ease:"none"}},0.1);']
    if ev.get("image"): js.append('tl.fromTo("#tim",{scale:.92,rotation:3},{scale:1,rotation:0,duration:POP.dur,ease:POP.ease},0);')
    for k in range(len(ev.get("chips", []))):
        js.append(f'tl.fromTo("#ch{k}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{0.35 + 0.18 * k:.3f});')
    return b, js


# ------------------------------------------------------------------------------------------------ disclaimer
def disclaimer(ev, mock):
    b = (f'<div class="bg"></div>'   # the stage background (OB's frame, blurred warm) shows through; no flat black (OB 10-20)
         f'<div id="dc" class="center" style="top:900px"><div class="avb" style="font-size:78px;color:#fff;text-shadow:0 4px 28px rgba(0,0,0,.65)">{esc(ev["text"])}</div>'
         f'<div class="av" style="font-size:56px;color:#e8dccd;margin-top:30px;text-shadow:0 3px 22px rgba(0,0,0,.7)">{esc(ev.get("sub", ""))}</div></div>')
    return b, ['tl.fromTo("#dc",{opacity:0},{opacity:1,duration:.3,ease:"none"},0);']


FN = {"clip": clip, "photo_full": photo_full, "num": num, "math": math, "dose": dose, "coins": coins,
      "timeline": timeline, "title": title, "disclaimer": disclaimer}
TYPES = set(FN)


# ------------------------------------------------------------------------------------------------ insert
def insert(ev, mock):
    """Full-bleed footage for a beat (Johnny Harris style: a short cut-in on a noun, often over a look-down). Muted.
    ev["broll"]: asset id (assets/broll/ID.mp4 + .jpg, made by story/prep_broll.py); ev["focal"]: [x, y] push-in centre;
    ev["archival"]: True (warm, faded) or "bw", with grain, gate weave and a vignette; ev["tag"]/ev["sub"]: small source credit;
    ev["annot"]: [{"at": key|seconds, "cx", "cy", "rx", "ry", "label", "lx", "ly"}] red ellipses drawn on as he says it (4K coords)."""
    D, key = ev["dur"], ev["broll"]; fx, fy = ev.get("focal", [0.5, 0.5]); arch = ev.get("archival")
    media = (f'<img src="../assets/broll/{key}.jpg" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover;display:block"/>' if mock else
             f'<video class="media clip" src="../assets/broll/{key}.mp4" muted playsinline data-start="0" data-duration="{D:.3f}" data-track-index="0" '
             f'style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover"></video>')
    filt = {"bw": "filter:grayscale(1) contrast(1.18) brightness(.92);", True: "filter:sepia(.42) saturate(.75) contrast(1.1) brightness(.95);"}.get(arch, "")
    b = (f'<div class="bg"></div><div id="ins" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;overflow:hidden;{filt}'
         f'transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%">{media}</div>')
    # red circles ride on their own layer that zooms with the footage (so they stay on their words) but skips the archive filter
    # (so they stay red); built here, appended after the film layers below (C4367 v2.1)
    ann = f'<div id="insa" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%">'
    js = [f'tl.fromTo(["#ins","#insa"],{{scale:1}},{{scale:{ev.get("zoom", 1.07)},duration:{D:.3f},ease:"none"}},0);']
    if arch:   # film: grain that changes every other frame, a soft vignette, a dark gate with rounded corners, a little weave
        b += ('<div id="grn" style="position:absolute;inset:0;background:url(../assets/grain.png);background-size:768px 768px;mix-blend-mode:overlay;opacity:.42"></div>'
              '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 55%,rgba(0,0,0,.55) 100%)"></div>'
              '<div style="position:absolute;inset:0;box-shadow:inset 0 0 0 46px #050505;border-radius:90px"></div>')
        k, t = 0, 0.0
        while t < D:
            js.append(f'tl.set("#grn",{{backgroundPosition:"{(k * 397) % 768}px {(k * 211) % 768}px"}},{t:.3f});'); k += 1; t += 2 / 29.97
        js.append(f'tl.to("#ins",{{x:3,y:-2,duration:.18,ease:"steps(1)",repeat:{max(1, int(D / .18))},yoyo:true}},0);')
    for j, a in enumerate(ev.get("annot", [])):
        ta = T(ev, a["at"], 0.4) if isinstance(a.get("at"), str) else float(a.get("at", 0.4))
        if a.get("style") == "select":
            svg, sjs = _select_svg(j, a, "an"); ann += svg; js += sjs(ta)
            if a.get("label"):
                h, hj = _hand_label(f"anl{j}", a, a.get("lx", a["cx"] - a["rx"]), a.get("ly", a["cy"] - a["ry"] - 190), ta) if a.get("hand") else (
                    f'<div id="anl{j}" class="din" style="position:absolute;left:{a.get("lx", a["cx"] - a["rx"])}px;top:{a.get("ly", a["cy"] - a["ry"] - 200)}px;'
                    f'font-size:{a.get("size", 140)}px;color:#fff;text-shadow:0 6px 30px rgba(0,0,0,.85);opacity:0;white-space:nowrap">{esc(a["label"])}</div>',
                    [f'tl.fromTo("#anl{j}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{ta + 0.25:.3f});'])
                ann += h; js += hj
            continue
        L = 3.1416 * (3 * (a["rx"] + a["ry"]) - ((3 * a["rx"] + a["ry"]) * (a["rx"] + 3 * a["ry"])) ** 0.5) * 1.05   # ellipse perimeter (Ramanujan), a little extra
        ann += (f'<svg style="position:absolute;left:0;top:0;overflow:visible" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
              f'<ellipse id="an{j}" cx="{a["cx"]}" cy="{a["cy"]}" rx="{a["rx"]}" ry="{a["ry"]}" fill="none" stroke="{R}" stroke-width="16" '
              f'stroke-linecap="round" stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}" transform="rotate(-4 {a["cx"]} {a["cy"]})"/></svg>')
        js.append(f'tl.to("#an{j}",{{strokeDashoffset:0,duration:.45,ease:"power2.out"}},{ta:.3f});')
        if a.get("label"):
            ann += (f'<div id="anl{j}" class="din" style="position:absolute;left:{a.get("lx", a["cx"] - 600)}px;top:{a.get("ly", a["cy"] + a["ry"] + 40)}px;'
                  f'width:1200px;text-align:center;font-size:110px;color:#fff;text-shadow:0 6px 30px rgba(0,0,0,.85);opacity:0">{esc(a["label"])}</div>')
            js.append(f'tl.fromTo("#anl{j}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{ta + 0.25:.3f});')
    b += ann + "</div>"
    if ev.get("caption"):   # a line of his, big over the footage ("Processed? Extremely.")
        c = ev["caption"]; tcap = T(ev, c["at"], 0.3) if isinstance(c.get("at"), str) else float(c.get("at", 0.3))
        txt = esc(c["text"])
        if c.get("box"):   # a dark backing for a caption over a bright frame (C4367 v4: white lawsuit pages)
            txt = f'<span style="display:inline-block;background:rgba(0,0,0,.6);padding:22px 56px 12px;border-radius:22px">{txt}</span>'
        b += (f'<div id="icap" class="center din" style="top:{c.get("y", 1480)}px;font-size:{c.get("size", 240)}px;line-height:1;'
              f'text-shadow:0 10px 50px rgba(0,0,0,.9),0 0 8px rgba(0,0,0,.6);opacity:0">{txt}</div>')
        js.append(f'tl.fromTo("#icap",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tcap:.3f});')
    if ev.get("tag"):
        # news footage carries its own lower third (NBC, GMA, Fox, CBS): the credit sits top left there; archival keeps it in the gate
        b += (f'<div id="itag" style="position:absolute;left:{120 if arch else 70}px;top:{H - 190 if arch else 64}px;display:flex;align-items:baseline;gap:22px;'
              f'background:rgba(255,255,255,.94);color:#111;border-radius:18px;padding:16px 32px 18px;white-space:nowrap">'
              f'<span class="avb" style="font-size:50px">{esc(ev["tag"])}</span><span class="av" style="font-size:40px;color:#666">{esc(ev.get("sub", ""))}</span></div>')
        js.append('tl.fromTo("#itag",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},.05);')
    return b, js


# ------------------------------------------------------------------------------------------------ wall
def wall(ev, mock):
    """A grid of stills (clip frames or photos) popping in as they're said. ev["items"]: [[asset path under assets/, tag, sub, at-key], ...]."""
    D, items = ev["dur"], ev["items"]; n = len(items); cols = ev.get("cols", min(n, 3 if n <= 6 else 4))
    rows = (n + cols - 1) // cols; top = 300 if ev.get("title") else 160
    cw = (W - 400 - 70 * (cols - 1)) // cols; ch = min((H - top - 140 - 70 * (rows - 1)) // rows, int(cw * (16 / 9 if ev.get("portrait") else 9 / 16)))
    if ev.get("portrait"): cw = min(cw, int(ch * 9 / 16))
    x0 = (W - (cols * cw + 70 * (cols - 1))) // 2
    b, js = '<div class="bg"></div>', []
    if ev.get("title"):
        b += f'<div id="wt" class="center din" style="top:110px;{ev.get("title_css", "font-size:130px")}">{ev["title"]}</div>'   # title_css: match a banner it hands over to
        js.append('tl.fromTo("#wt",{y:-30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    if ev.get("carousel"):   # 2026-10-20, decoded from Payton Kaleiwahea's reel (the "signature moments" cards on the Justin
        # Jefferson site by Cameron Duncalfe): tall cards step left one per spoken item; the card in focus grows and lights up while
        # the others dim and tilt; big index numbers; a huge title drifts behind; optional ev["quote"] slams in as the row leaves.
        th = ev.get("card_h", 1480); tw = round(th * 9 / 16) if ev.get("portrait", True) else round(th * 16 / 9); g = 120
        cy = H // 2 + 70; step = tw + g; cx0 = (W - tw) // 2
        ts = [T(ev, it[3], 0.15 + 0.9 * k) if len(it) > 3 and it[3] else 0.15 + 0.9 * k for k, it in enumerate(items)]
        tq = (T(ev, ev["quote_at"], D - 1.4) if isinstance(ev.get("quote_at"), str) else float(ev.get("quote_at", D - 1.4))) if ev.get("quote") else None
        if n > 1:   # one card per beat across the whole card: anchors bunched up front (a grid's pop-ins) get spread out; later ones win
            end = (tq - 1.1) if tq is not None else (D - 1.1)   # the last card gets a full beat in focus before the exit
            ts = [round(max(ts[k], ts[0] + k * (end - ts[0]) / (n - 1)), 3) for k in range(n)]
        big = ev.get("title")
        if big:   # the giant title behind the cards: cropped by the frame, drifting slower than the cards (depth)
            b += (f'<div id="wbig" class="din" style="position:absolute;left:0;top:{cy - 560}px;white-space:nowrap;font-size:{ev.get("title_size", 700)}px;'
                  f'line-height:1;color:{ev.get("title_color", R)};opacity:.92;text-transform:uppercase;letter-spacing:-6px">{esc(big)}</div>')
            js.append(f'tl.fromTo("#wbig",{{x:{ev.get("title_x0", 120)}}},{{x:{ev.get("title_x0", 120) - 700},duration:{D:.3f},ease:"none"}},0);')
            js = [j for j in js if '"#wt"' not in j]; b = b.replace('<div id="wt"', '<div id="wt" hidden')
        b += f'<div id="wdrift" style="position:absolute;inset:0"><div id="wrow" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">'
        for k, it in enumerate(items):
            x = cx0 + k * step
            b += (f'<div id="w{k}" style="position:absolute;left:{x}px;top:{cy - th // 2}px;width:{tw}px;height:{th}px;border-radius:34px;overflow:hidden;'
                  f'box-shadow:0 0 0 8px rgba(255,255,255,.9),0 40px 110px rgba(0,0,0,.7);background:#111;transform-origin:50% 55%">'
                  f'<img src="../assets/{it[0]}" style="width:100%;height:100%;object-fit:cover"/>'
                  f'<div class="din" style="position:absolute;left:44px;top:30px;font-size:190px;line-height:1;color:#fff;text-shadow:0 8px 40px rgba(0,0,0,.8)">{k + 1:02d}</div>'
                  f'<div style="position:absolute;left:0;right:0;bottom:0;padding:40px 44px;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.92))">'
                  f'<div class="avb" style="font-size:66px">{esc(it[1])}</div><div class="din" style="font-size:118px;color:{Y};line-height:1.05">{esc(it[2])}</div></div>'
                  f'<div id="wd{k}" style="position:absolute;inset:0;background:#000;opacity:0"></div></div>')
        b += '</div></div>'
        js.append(f'tl.fromTo("#wdrift",{{x:0}},{{x:-{round(40 * D)},duration:{D:.3f},ease:"none"}},0);')   # never still: a slow drift under the steps
        for k in range(n):   # frame one is a finished picture: card 0 in focus, the rest dimmed and tilted
            js.append(f'tl.set("#w{k}",{{scale:{1.12 if k == 0 else .84},rotation:{0 if k == 0 else 4},immediateRender:true}},0);')
            js.append(f'tl.set("#wd{k}",{{opacity:{0 if k == 0 else .55},immediateRender:true}},0);')
        for k in range(1, n):
            t0 = max(ts[k] - 0.18, ts[k - 1] + 0.3)
            js += [f'tl.to("#wrow",{{x:{-k * step},duration:SLIDE.dur,ease:SLIDE.ease}},{t0:.3f});',
                   f'tl.to("#w{k}",{{scale:1.12,rotation:0,duration:POP.dur,ease:POP.ease}},{t0 + 0.08:.3f});',
                   f'tl.to("#wd{k}",{{opacity:0,duration:.25,ease:"none"}},{t0 + 0.05:.3f});',
                   f'tl.to("#w{k - 1}",{{scale:.84,rotation:-4,duration:SLIDE.dur,ease:SLIDE.ease}},{t0:.3f});',
                   f'tl.to("#wd{k - 1}",{{opacity:.55,duration:.3,ease:"none"}},{t0:.3f});']
        if tq is not None:   # the run resolves into one line: the row leaves left, the quote slams in
            b += (f'<div id="wq" class="center din" style="top:{cy - ev.get("quote_size", 520) // 2 - 40}px;font-size:{ev.get("quote_size", 520)}px;line-height:1;'
                  f'color:{ev.get("quote_color", "#fff")};text-shadow:0 18px 70px rgba(0,0,0,.75);opacity:0">{esc(ev["quote"])}</div>')
            js += [f'tl.to("#wrow",{{x:"-={W}",opacity:0,duration:SLIDE.dur,ease:SLIDE.ease}},{tq - 0.3:.3f});',
                   f'tl.to("#wbig",{{opacity:.25,duration:.4,ease:"none"}},{tq - 0.3:.3f});' if big else "",
                   f'tl.fromTo("#wq",{{opacity:0,scale:1.35}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tq:.3f});']
        return b, [j for j in js if j]
    if ev.get("portrait") and n > 3:   # v3 (OB 10-20): a scrolling feed of big tiles, three on screen at a time
        th = 1640 if ev.get("title") else 1800; tw = round(th * 9 / 16); g = 90; top = 330 if ev.get("title") else (H - th) // 2
        row = n * tw + (n - 1) * g; x_start = (W - (3 * tw + 2 * g)) // 2; x_end = W - x_start - row
        b += f'<div id="wrow" style="position:absolute;left:0;top:{top}px;width:{row}px;height:{th}px">'
        for k, it in enumerate(items):
            b += (f'<div id="w{k}" style="position:absolute;left:{k * (tw + g)}px;top:0;width:{tw}px;height:{th}px;border-radius:30px;overflow:hidden;'
                  f'box-shadow:0 0 0 10px #fff,0 30px 90px rgba(0,0,0,.65);background:#111"><img src="../assets/{it[0]}" style="width:100%;height:100%;object-fit:cover"/>'
                  f'<div style="position:absolute;left:0;right:0;bottom:0;padding:34px 38px;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.9))">'
                  f'<div class="avb" style="font-size:66px">{esc(it[1])}</div><div class="din" style="font-size:120px;color:{Y};line-height:1.05">{esc(it[2])}</div></div></div>')
        b += '</div>'
        js += [f'tl.fromTo("#wrow",{{x:{x_start}}},{{x:{x_end},duration:{D:.3f},ease:"power1.inOut"}},0);']
        for k in range(min(3, n)):
            js.append(f'tl.fromTo("#w{k}",{{scale:.86,opacity:0}},{{scale:1,opacity:1,duration:POP.dur,ease:POP.ease}},{0.05 + 0.15 * k:.3f});')
        return b, js
    for k, it in enumerate(items):
        r_, c_ = divmod(k, cols); x, y = x0 + c_ * (cw + 70), top + r_ * (ch + 70)
        b += (f'<div id="w{k}" style="position:absolute;left:{x}px;top:{y}px;width:{cw}px;height:{ch}px;border-radius:24px;overflow:hidden;'
              f'box-shadow:0 0 0 8px #fff,0 26px 70px rgba(0,0,0,.65);background:#111"><img src="../assets/{it[0]}" style="width:100%;height:100%;object-fit:cover;'
              f'object-position:{it[4] if len(it) > 4 and it[4] else "50% 50%"}"/>'   # it[4]: where a portrait still's face sits (C4372 wall: "50% 28%")
              f'<div style="position:absolute;left:0;right:0;bottom:0;padding:22px 26px;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.85))">'
              f'<div class="avb" style="font-size:52px">{esc(it[1])}</div><div class="av" style="font-size:42px;color:#ddd">{esc(it[2])}</div></div></div>')
        t0 = T(ev, it[3], 0.1 + 0.25 * k) if len(it) > 3 and it[3] else 0.1 + 0.25 * k
        js.append(f'tl.fromTo("#w{k}",{{scale:.82,opacity:0}},{{scale:1,opacity:1,duration:POP.dur,ease:POP.ease}},{t0:.3f});')
    return b, js


# ------------------------------------------------------------------------------------------------ versus
def versus(ev, mock):
    """Side-by-side panels: ev["items"]: [[asset path under assets/ or "", big text, label, at-key], ...]; ev["mid"]: "=", "vs" or ""."""
    D, items = ev["dur"], ev["items"]; n = len(items)
    pw = 1260 if n == 2 else 980; gap = 380 if n == 2 else 140; x0 = (W - (n * pw + gap * (n - 1))) // 2
    img_any = any(it[0] for it in items)
    if img_any: top, tt = (330 if ev.get("title") else 200), 120
    else:   # words only: the block (title + numbers + labels, ~480 px) sits on the optical centre
        tt = (H - ((300 if ev.get("title") else 0) + 480)) // 2 - 60; top = tt + (300 if ev.get("title") else 0)
    b, js = '<div class="bg"></div>', []
    if ev.get("title"):
        b += f'<div id="vt" class="center din" style="top:{tt}px;font-size:130px">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#vt",{y:-30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    for k, it in enumerate(items):
        x = x0 + k * (pw + gap)
        img = (f'<div style="width:{pw}px;height:{pw * 3 // 4}px;border-radius:30px;overflow:hidden;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.55)">'
               + _img(it[0], f'width:100%;height:100%;object-fit:{"contain" if ev.get("contain") else "cover"}') + '</div>') if it[0] else ""
        b += (f'<div id="v{k}" style="position:absolute;left:{x}px;top:{top}px;width:{pw}px;text-align:center">{img}'
              f'<div class="din" style="font-size:{200 if img else 330}px;line-height:1;margin-top:46px;color:{Y if k == len(items) - 1 else "#fff"}">{esc(it[1])}</div>'
              f'<div class="avb" style="font-size:70px;color:#e6e6e6;margin-top:18px">{esc(it[2])}</div></div>')
        t0 = T(ev, it[3], 0.1 + 0.9 * k) if len(it) > 3 and it[3] else 0.1 + 0.9 * k
        if k == 0 and n == 2: t0 = min(t0, 0.05)   # v3: the subject is on screen from the start, never a title alone
        js.append(f'tl.fromTo("#v{k}",{{y:50,opacity:0}},{{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease}},{t0:.3f});')
    # v3 (OB 10-20: "only half the screen"): when the second panel lands well after the first, the first holds the frame
    # centred and a little bigger, then slides into its half as the second arrives
    tv = [T(ev, it[3], 0.1 + 0.9 * k) if len(it) > 3 and it[3] else 0.1 + 0.9 * k for k, it in enumerate(items)]
    if n == 2: tv[0] = min(tv[0], 0.05)
    if n == 2 and tv[1] - tv[0] > 1.2:
        dx0 = (W - pw) // 2 - x0
        js += [f'tl.set("#v0",{{x:{dx0},scale:1.12,transformOrigin:"50% 40%",immediateRender:true}},0);',
               f'tl.to("#v0",{{x:0,scale:1,duration:SLIDE.dur,ease:SLIDE.ease}},{max(tv[0] + 0.4, tv[1] - 0.2):.3f});']
    if ev.get("mid") and n == 2:
        my = top + pw * 3 // 8 - 120 if img_any else top + 46 + 165 - 144   # level with the image centre, or with the big numbers
        b += f'<div id="vm" class="din" style="position:absolute;left:{x0 + pw}px;width:{gap}px;text-align:center;top:{my}px;font-size:240px;color:{Y}">{esc(ev["mid"])}</div>'
        tm = T(ev, items[1][3], 1.0) if len(items[1]) > 3 and items[1][3] else 1.0
        js.append(f'tl.fromTo("#vm",{{scale:.001}},{{scale:1,duration:POP.dur,ease:POP.ease}},{max(0.05, tm - 0.15):.3f});')
    if ev.get("source"):
        b += f'<div class="av" style="position:absolute;left:200px;top:2050px;font-size:46px;color:#8f8f8f">{esc(ev["source"])}</div>'
    return b, js


# ------------------------------------------------------------------------------------------------ checklist
ICON = {"check": f'<circle cx="12" cy="12" r="10" fill="{G}"/><path d="M7 12.4l3.2 3.2L17 9" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
        "x": f'<circle cx="12" cy="12" r="10" fill="{R}"/><path d="M8.2 8.2l7.6 7.6M15.8 8.2l-7.6 7.6" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>',
        "down": f'<circle cx="12" cy="12" r="10" fill="{A_}"/><path d="M12 6.5v11M7.5 13l4.5 4.5 4.5-4.5" stroke="#111" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
        "up": f'<circle cx="12" cy="12" r="10" fill="{G}"/><path d="M12 17.5v-11M7.5 11l4.5-4.5 4.5 4.5" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
        "eq": '<circle cx="12" cy="12" r="10" fill="#9a9a9a"/><path d="M7.5 10h9M7.5 14h9" stroke="#111" stroke-width="2.4" stroke-linecap="round"/>',
        "sun": f'<circle cx="12" cy="12" r="4.6" fill="{Y}"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" stroke="{Y}" stroke-width="2" stroke-linecap="round"/>',
        "dot": f'<circle cx="12" cy="12" r="6" fill="{Y}"/>'}


def checklist(ev, mock):
    """Rows that tick in as they're said: ev["rows"]: [[text, sub, at-key, icon], ...]; optional ev["image"] (assets path) on the right.
    The title and rows form one left-aligned block, centred in the frame (or in the space left of the image); type scales with the row count."""
    D, rows = ev["dur"], ev["rows"]; n = len(rows)
    img_w = 1200 if ev.get("image") else 0
    fs = 160 if n <= 2 else (136 if n == 3 else (120 if n == 4 else 100))
    sfs, ic, gap = (66, 176, 84) if n <= 4 else (56, 140, 56)
    area = W - (img_w + 240 + 80 if img_w else 0)
    b, js = '<div class="bg"></div>', []
    if img_w:
        ih = img_w * 5 // 4
        b += (f'<div id="cli" style="position:absolute;left:{W - img_w - 240}px;top:{(H - ih) // 2}px;width:{img_w}px;height:{ih}px;border-radius:36px;overflow:hidden;'
              f'background:#fff;box-shadow:0 30px 90px rgba(0,0,0,.6)">' + _img(ev["image"], "width:100%;height:100%;object-fit:cover") + '</div>')
        js.append('tl.fromTo("#cli",{scale:.92,rotation:2},{scale:1,rotation:0,duration:POP.dur,ease:POP.ease},0);')
    b += (f'<div style="position:absolute;left:0;top:0;width:{area}px;height:{H - 100}px;display:flex;align-items:center;justify-content:center">'
          f'<div style="display:flex;flex-direction:column;gap:{gap}px;max-width:{area - 360}px">')
    if ev.get("title"):
        b += f'<div id="clt" class="din" style="font-size:130px;line-height:1;color:{Y};margin-bottom:{gap // 3}px">{esc(ev["title"])}</div>'
        js.append('tl.fromTo("#clt",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);')
    for k, r in enumerate(rows):
        txt, sub, key = r[0], r[1], r[2]; icn = r[3] if len(r) > 3 else "check"
        t0 = T(ev, key, 0.2 + 0.7 * k) if key else 0.2 + 0.7 * k
        # v3 (OB 10-20: no title-only slides): every row is on screen from the first frame, dimmed and without its icon;
        # as he says it the row lights up and its icon pops in
        b += (f'<div id="cr{k}" style="display:flex;align-items:center;gap:{ic // 3}px;opacity:.28">'
              f'<svg id="cri{k}" width="{ic}" height="{ic}" viewBox="0 0 24 24" style="flex:none;opacity:0">{ICON[icn]}</svg>'
              f'<div><div class="din" style="font-size:{fs}px;line-height:1.02">{esc(txt)}</div>'
              + (f'<div class="avb" style="font-size:{sfs}px;color:#cfcfcf;margin-top:10px">{esc(sub)}</div>' if sub else "") + '</div></div>')
        js += [f'tl.fromTo("#cr{k}",{{opacity:.28,x:-24}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{t0:.3f});',
               f'tl.fromTo("#cri{k}",{{opacity:0,scale:.4,transformOrigin:"50% 50%"}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t0 + 0.08:.3f});']
    b += '</div></div>'
    if ev.get("source"):
        b += f'<div class="av" style="position:absolute;left:260px;top:2050px;font-size:46px;color:#8f8f8f">{esc(ev["source"])}</div>'
    return b, js


# ------------------------------------------------------------------------------------------------ scissors
def _molecule(mid, x, y, shielded=False, label="", k=1.5):
    """A triglyceride drawn simply, scaled by k: a glycerol backbone (3 nodes) and three fatty-acid zigzags. Shielded = EPG
    (the cut spots capped with yellow propoxyl 'shields'). Bond i (the cut spot) sits at local (-30, 170 i)."""
    zig = lambda yy: "M0,{0} ".format(yy) + " ".join(f"L{60 + 70 * i},{yy + (26 if i % 2 == 0 else -26)}" for i in range(9))
    chains = "".join(f'<g id="{mid}c{i}"><path d="{zig(i * 170)}" fill="none" stroke="#f1d37a" stroke-width="18" stroke-linejoin="round" stroke-linecap="round"/></g>'
                     for i in range(3))
    bonds = "".join(f'<circle id="{mid}b{i}" cx="-30" cy="{i * 170}" r="22" fill="#fff"/>' for i in range(3))
    shields = "".join(f'<rect id="{mid}s{i}" x="-66" y="{i * 170 - 62}" width="72" height="124" rx="22" fill="{Y}" stroke="#111" stroke-width="7"/>'
                      for i in range(3)) if shielded else ""
    nodes = "".join(f'<circle cx="-115" cy="{i * 170}" r="36" fill="#9a9a9a"/>' for i in range(3))
    return (f'<g id="{mid}" transform="translate({x},{y})"><g transform="scale({k})"><rect x="-152" y="-55" width="74" height="450" rx="37" fill="#cfcfcf"/>'
            f'{nodes}{chains}{bonds}{shields}</g>'
            f'<text x="{-150 * k:.0f}" y="{460 * k:.0f}" font-family="DINC" font-size="96" fill="#e8e8e8">{esc(label)}</text></g>')


SCISSORS = ('<g id="{id}"><g transform="scale(1.7)"><g id="{id}A"><path d="M0,0 L230,-26 L236,0 Z" fill="#e6e6e6" stroke="#111" stroke-width="5"/><circle cx="-70" cy="-48" r="44" fill="none" '
            'stroke="#E53935" stroke-width="18"/></g><g id="{id}B"><path d="M0,0 L230,26 L236,0 Z" fill="#d0d0d0" stroke="#111" stroke-width="5"/>'
            '<circle cx="-70" cy="48" r="44" fill="none" stroke="#E53935" stroke-width="18"/></g><circle cx="0" cy="0" r="12" fill="#111"/></g></g>')


def scissors(ev, mock):
    """The lipase explainer. at keys: fat (molecule up), snip (lipase cuts the three chains, pieces absorbed), epg (EPG with
    blocked spots), slide (the scissors glance off), pass (EPG passes through), mouth (taste + texture), body (barely any calories)."""
    D = ev["dur"]; K = 1.5; so = bool(ev.get("snip_only"))   # snip_only: the recap (lipase cuts normal fat), one panel, centred
    t = {k: T(ev, k, d) for k, d in (("fat", 0.15), ("snip", 1.2), ("epg", D * 0.4), ("slide", D * 0.5), ("pass", D * 0.62), ("mouth", D * 0.75), ("body", D * 0.85))}
    FX, FY, EX, EY = (1569 if so else 620), 560, 2440, 560
    bond = lambda X0, Y0, i: (X0 - 30 * K, Y0 + 170 * K * i)   # where blade tips meet: the bond between backbone and chain i
    svg = lambda inner: f'<svg style="position:absolute;left:0;top:0;overflow:visible" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{inner}</svg>'
    b = ('<div class="bg"></div>'
         + (f'<div id="sct" class="center din" style="top:150px;font-size:140px">' if so else f'<div id="sct" class="din" style="position:absolute;left:260px;top:150px;font-size:140px">')
         + f'{esc(ev.get("title", "How your body handles fat"))}</div>'
         + ('' if so else f'<div id="dvd" style="position:absolute;left:1918px;top:520px;width:4px;height:1240px;background:rgba(255,255,255,.18);opacity:0"></div>'))
    if so:
        b += (svg(_molecule("mf", FX, FY, False, "Normal fat", K) + SCISSORS.format(id="sc"))
              + f'<div id="lab1" class="center din" style="top:1500px;font-size:120px;color:{Y};opacity:0">Lipase = the scissors</div>'
              f'<div id="abs" class="center din" style="top:1680px;font-size:130px;color:{G};opacity:0">✓ cut small enough to absorb</div>')
    else:   # v3 (OB 10-20: "only half the screen, so much black space"): normal fat starts big and centred, and slides into the
        #     left half only when EPG arrives on the right
        b += (f'<div id="pL" style="position:absolute;inset:0;transform-origin:975px 1090px">'
              + svg(_molecule("mf", FX, FY, False, "Normal fat", K) + SCISSORS.format(id="sc"))
              + f'<div id="lab1" class="din" style="position:absolute;left:400px;top:1440px;font-size:100px;color:{Y};opacity:0">Lipase = the scissors</div>'
              f'<div id="abs" class="din" style="position:absolute;left:400px;top:1580px;font-size:110px;color:{G};opacity:0">✓ cut small enough to absorb</div>'
              f'<div id="mo" style="position:absolute;left:400px;top:1820px;opacity:0"><div class="din" style="font-size:100px;background:{G};color:#111;border-radius:20px;padding:18px 40px">Mouth: taste + texture ✓</div></div>'
              '</div><div id="pR" style="position:absolute;inset:0">'
              + svg(_molecule("me", EX, EY, True, "EPG", K))
              + f'<div id="lab2" class="din" style="position:absolute;left:2220px;top:1440px;font-size:100px;color:{Y};opacity:0">Cutting spots blocked</div>'
              f'<div id="pss" class="din" style="position:absolute;left:2220px;top:1580px;font-size:110px;color:#fff;opacity:0">↓ most of it passes through</div>'
              f'<div id="bo" style="position:absolute;left:2220px;top:1820px;opacity:0"><div class="din" style="font-size:100px;background:{R};color:#fff;border-radius:20px;padding:18px 40px">Body: barely any calories</div></div>'
              '</div>')
    js = ['tl.fromTo("#sct",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);',
          'tl.set("#me",{opacity:0,immediateRender:true},0);' if not so else '',
          f'tl.set("#sc",{{x:{FX - 420},y:1330,rotation:-30,opacity:1,immediateRender:true}},0);',
          f'tl.fromTo("#mf",{{opacity:0,x:{FX - 80}}},{{opacity:1,x:{FX},duration:SNAP.dur,ease:SNAP.ease}},{t["fat"]:.3f});']
    ts = t["snip"]
    js.append(f'tl.fromTo("#lab1",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{ts:.3f});')
    for i in range(3):
        bx, by = bond(FX, FY, i); tc = ts + 0.5 + 0.5 * i
        js += [f'tl.to("#sc",{{x:{bx - 30:.0f},y:{by:.0f},rotation:0,duration:.32,ease:"power2.out"}},{tc - 0.34:.3f});',
               f'tl.fromTo("#scA",{{rotation:-14,svgOrigin:"0 0"}},{{rotation:0,svgOrigin:"0 0",duration:.1,ease:"none",yoyo:true,repeat:1}},{tc:.3f});',
               f'tl.fromTo("#scB",{{rotation:14,svgOrigin:"0 0"}},{{rotation:0,svgOrigin:"0 0",duration:.1,ease:"none",yoyo:true,repeat:1}},{tc:.3f});',
               f'tl.to("#mfc{i}",{{x:160,y:{70 + 20 * i},rotation:{6 - 6 * i},svgOrigin:"0 {170 * i}",opacity:.55,duration:SOFT.dur,ease:SOFT.ease}},{tc + 0.08:.3f});']
    js.append(f'tl.fromTo("#abs",{{opacity:0,y:30}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{ts + 1.9:.3f});')
    if so:   # the scissors leave; the cut molecule and the two lines stay
        js += [f'tl.to("#sc",{{x:{FX + 1250},y:1150,rotation:-30,opacity:0,duration:SLIDE.dur,ease:SLIDE.ease}},{ts + 2.1:.3f});',
               f'tl.fromTo("#mf",{{y:{FY}}},{{y:{FY - 14},duration:1.2,ease:"sine.inOut",yoyo:true,repeat:{max(1, int(D / 1.2))}}},{t["fat"] + 0.4:.3f});']
        return b, js
    js.append(f'tl.to("#sc",{{x:{FX + 1080},y:380,rotation:0,duration:SLIDE.dur,ease:SLIDE.ease}},{ts + 2.1:.3f});')   # parked above the molecules, clear of the cut chains
    te, tsl, tp = t["epg"], t["slide"], t["pass"]
    tsplit = max(ts + 2.4, te - 0.55)   # the centred panel makes room just before EPG is named
    js += ['tl.set("#pL",{x:945,scale:1.22,immediateRender:true},0);',
           f'tl.to("#pL",{{x:0,scale:1,duration:SLIDE.dur,ease:SLIDE.ease}},{tsplit:.3f});',
           f'tl.fromTo("#dvd",{{opacity:0}},{{opacity:1,duration:.4,ease:"none"}},{tsplit + 0.25:.3f});']
    js += [f'tl.fromTo("#me",{{opacity:0,x:{EX + 80}}},{{opacity:1,x:{EX},duration:SNAP.dur,ease:SNAP.ease}},{te:.3f});',
           f'tl.fromTo("#lab2",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{te + 0.2:.3f});']
    for i in range(3):
        js.append(f'tl.fromTo("#mes{i}",{{scale:.001,svgOrigin:"-30 {i * 170}"}},{{scale:1,svgOrigin:"-30 {i * 170}",duration:POP.dur,ease:POP.ease}},{te + 0.35 + 0.15 * i:.3f});')
    bx, by = bond(EX, EY, 1)
    js += [f'tl.to("#sc",{{x:{bx - 40:.0f},y:{by:.0f},rotation:0,duration:SLIDE.dur,ease:SLIDE.ease}},{max(te + 0.6, tsl - 0.5):.3f});',
           f'tl.fromTo("#scA",{{rotation:-14,svgOrigin:"0 0"}},{{rotation:-4,svgOrigin:"0 0",duration:.1,ease:"none",yoyo:true,repeat:1}},{tsl:.3f});',
           f'tl.to("#sc",{{x:{bx + 260:.0f},y:{by + 520:.0f},rotation:44,duration:.55,ease:"power2.out"}},{tsl + 0.2:.3f});',
           f'tl.to("#sc",{{opacity:0,duration:.3}},{tsl + 0.7:.3f});',   # gone once it has glanced off: parked, it sat on the labels
           f'tl.to("#me",{{x:{EX + 420},y:{EY + 90},opacity:.35,duration:1.4,ease:"power1.inOut"}},{tp:.3f});',
           f'tl.fromTo("#pss",{{opacity:0,y:30}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{tp:.3f});',
           f'tl.fromTo("#mo",{{opacity:0,y:40}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{t["mouth"]:.3f});',
           f'tl.fromTo("#bo",{{opacity:0,y:40}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{t["body"]:.3f});',
           f'tl.fromTo("#mf",{{y:{FY}}},{{y:{FY - 14},duration:1.2,ease:"sine.inOut",yoyo:true,repeat:{max(1, int(D / 1.2))}}},{t["fat"] + 0.4:.3f});']
    return b, js


# ------------------------------------------------------------------------------------------------ detector
def detector(ev, mock):
    """A metal detector sweeping a beach: it beeps for gold, a bottle cap and EPG alike. at keys: gold, cap, epg, total."""
    D = ev["dur"]; t = {k: T(ev, k, d) for k, d in (("gold", 0.4), ("cap", 1.6), ("epg", 2.8), ("total", D - 1.6))}
    gx = {"gold": 1100, "cap": 1920, "epg": 2740}
    objs = (f'<g id="og" transform="translate({gx["gold"]},1500)"><circle r="95" fill="#f5c542" stroke="#a97c06" stroke-width="14"/><text y="22" text-anchor="middle" font-family="DINC" font-size="80" fill="#7a5a00">AU</text></g>'
            f'<g id="oc" transform="translate({gx["cap"]},1500)"><circle r="90" fill="#bdbdbd" stroke="#777" stroke-width="14" stroke-dasharray="18 10"/><circle r="56" fill="#9e9e9e"/></g>'
            f'<g id="oe" transform="translate({gx["epg"]},1500)"><path d="M0,-110 C70,-20 90,30 90,60 A90,90 0 0 1 -90,60 C-90,30 -70,-20 0,-110 Z" fill="#fff3c4" stroke="{Y}" stroke-width="12"/>'
            f'<text y="72" text-anchor="middle" font-family="DINC" font-size="76" fill="#6b5600">EPG</text></g>')
    det = ('<g id="dt"><rect x="-14" y="-760" width="28" height="700" rx="14" fill="#555"/><rect x="-60" y="-780" width="120" height="70" rx="20" fill="#333"/>'
           f'<ellipse cx="0" cy="-40" rx="170" ry="54" fill="none" stroke="{Y}" stroke-width="22"/></g>')
    b = ('<div class="bg"></div>'
         f'<div id="dtt" class="din" style="position:absolute;left:260px;top:150px;font-size:140px">{esc(ev.get("title", "The lab’s fat test"))}</div>'
         f'<div class="av" style="position:absolute;left:264px;top:320px;font-size:58px;color:#bdbdbd">{esc(ev.get("sub", "AOAC 945.44: it measures whatever dissolves like fat"))}</div>'
         f'<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
         f'<rect x="0" y="1380" width="{W}" height="780" fill="#3a2f1d"/><rect x="0" y="1380" width="{W}" height="40" fill="#5a4a2c"/>'
         f'{objs}<g transform="translate(0,1420)">{det}</g></svg>')
    js = ['tl.fromTo("#dtt",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);', 'tl.set("#dt",{x:400,immediateRender:true},0);']
    for k in ("gold", "cap", "epg"):
        x = gx[k]; tk = t[k]; oid = {"gold": "og", "cap": "oc", "epg": "oe"}[k]
        word = {"gold": "Gold", "cap": "Bottle cap", "epg": "EPG"}[k]
        b += (f'<div id="bp{k}" class="din" style="position:absolute;left:{x - 400}px;width:800px;text-align:center;top:980px;font-size:150px;color:{Y};opacity:0">BEEP</div>'
              f'<div id="bl{k}" class="avb" style="position:absolute;left:{x - 400}px;width:800px;text-align:center;top:1700px;font-size:70px;opacity:0">{word}</div>')
        js += [f'tl.to("#dt",{{x:{x},duration:SLIDE.dur,ease:SLIDE.ease}},{max(0, tk - 0.45):.3f});',
               f'tl.fromTo("#bp{k}",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tk:.3f});',
               f'tl.fromTo("#bl{k}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tk:.3f});',
               f'tl.fromTo("#{oid}",{{scale:1}},{{scale:1.18,duration:.15,yoyo:true,repeat:1,ease:"power1.out"}},{tk:.3f});']
    b += (f'<div id="dtot" class="din" style="position:absolute;left:0;width:{W}px;text-align:center;top:1870px;font-size:120px;opacity:0">'
          f'{esc(ev.get("total_text", "All counted as fat: 13.52 g"))}</div>')
    js.append(f'tl.fromTo("#dtot",{{opacity:0,y:30}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{t["total"]:.3f});')
    return b, js


# ------------------------------------------------------------------------------------------------ find
def find(ev, mock):
    """Searching the complaint: a page, a find bar that types the query, and the result count. ev["queries"]: [[word, type-at, result-at], ...]."""
    D = ev["dur"]
    lines = "".join(f'<div style="height:22px;width:{1500 - (k * 137) % 520}px;background:#d9d9d9;border-radius:11px;margin:30px 0"></div>' for k in range(22))
    b = ('<div class="bg"></div>'
         f'<div id="pg" style="position:absolute;left:520px;top:180px;width:1850px;height:2200px;background:#fff;border-radius:16px;box-shadow:0 40px 120px rgba(0,0,0,.6);'
         f'padding:110px 150px;color:#222;transform-origin:50% 0">'
         f'<div style="font-family:Times New Roman,serif;font-size:58px;text-align:center;font-weight:bold">UNITED STATES DISTRICT COURT<br/>SOUTHERN DISTRICT OF NEW YORK</div>'
         f'<div style="font-family:Times New Roman,serif;font-size:50px;margin-top:70px">Lopez, et al. v. Linus Technologies, Inc. d/b/a David Protein</div>'
         f'<div style="font-family:Times New Roman,serif;font-size:50px;margin-top:20px;font-weight:bold">CLASS ACTION COMPLAINT</div>{lines}</div>'
         f'<div id="pgs" class="avb" style="position:absolute;left:560px;top:2040px;font-size:56px;color:#bdbdbd">46 pages</div>'
         f'<div id="fb" style="position:absolute;left:2470px;top:300px;width:1150px;background:#2b2b2b;border:4px solid #555;border-radius:26px;padding:40px 46px;box-shadow:0 30px 80px rgba(0,0,0,.6)">'
         f'<div class="av" style="font-size:52px;color:#aaa">Find in document</div>'
         f'<div style="margin-top:24px;background:#fff;border-radius:16px;padding:26px 34px;color:#111;font-family:Menlo,monospace;font-size:74px;height:140px"><span id="fq"></span><span id="fcur">|</span></div>'
         f'<div id="fr" class="din" style="margin-top:30px;font-size:120px;color:{R}">&nbsp;</div></div>'
         f'<div id="fz" class="din" style="position:absolute;left:2470px;width:1150px;text-align:center;top:1100px;font-size:520px;line-height:1;color:{R};opacity:0">0</div>'
         f'<div id="fzl" class="avb" style="position:absolute;left:2470px;width:1150px;text-align:center;top:1640px;font-size:80px;opacity:0">&nbsp;</div>'
         f'<div class="av" style="position:absolute;left:560px;top:2090px;font-size:40px;color:#8f8f8f">{esc(ev.get("source", "Search run on the filed complaint, Lopez v. Linus Technologies, 1:26-cv-00635 (SDNY)"))}</div>')
    js = ['tl.fromTo("#pg",{y:60},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
          f'tl.to("#pg",{{y:-160,duration:{D:.3f},ease:"none"}},0.4);',
          'tl.fromTo("#fb",{x:60},{x:0,duration:SNAP.dur,ease:SNAP.ease},0.1);']
    for qi, (word, k_type, k_res) in enumerate(ev["queries"]):
        tt, tr = T(ev, k_type, 0.4 + 2.5 * qi), T(ev, k_res, 1.5 + 2.5 * qi)
        for j in range(len(word) + 1):
            js.append(f'tl.set("#fq",{{textContent:{word[:j]!r}}},{tt + 0.07 * j:.3f});')
        js += [f'tl.set("#fr",{{textContent:"0 results"}},{tr:.3f});',
               f'tl.fromTo("#fr",{{scale:.7}},{{scale:1,duration:POP.dur,ease:POP.ease}},{tr:.3f});',
               f'tl.set("#fzl",{{textContent:{("for “" + word + "”")!r}}},{tr:.3f});',
               f'tl.fromTo(["#fz","#fzl"],{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tr + 0.1:.3f});']
        if qi + 1 < len(ev["queries"]):
            tn = T(ev, ev["queries"][qi + 1][1], tr + 2.0)
            js += [f'tl.to(["#fz","#fzl"],{{opacity:0,duration:.2}},{tn - 0.25:.3f});', f'tl.set("#fr",{{textContent:" "}},{tn - 0.05:.3f});']
    return b, js


# ------------------------------------------------------------------------------------------------ slider
def slider(ev, mock):
    """POISON <-> MIRACLE: the knob swings to each end as they're said, then lands in the middle. at keys: left, right, mid."""
    D = ev["dur"]; tl_, tr_, tm = T(ev, "left", 0.4), T(ev, "right", 1.4), T(ev, "mid", D * 0.6)
    x0, x1, y = 560, 3280, 1180
    b = ('<div class="bg"></div>'
         f'<div id="slt" class="center din" style="top:250px;font-size:140px">{esc(ev.get("title", "What the internet tells you"))}</div>'
         f'<div style="position:absolute;left:{x0}px;top:{y - 18}px;width:{x1 - x0}px;height:36px;border-radius:18px;background:linear-gradient(90deg,{R},#666 50%,{G})"></div>'
         f'<div class="din" style="position:absolute;left:{x0 - 300}px;width:600px;text-align:center;top:{y + 110}px;font-size:150px;color:{R}">{esc(ev.get("left_label", "POISON"))}</div>'
         f'<div class="din" style="position:absolute;left:{x1 - 300}px;width:600px;text-align:center;top:{y + 110}px;font-size:150px;color:{G}">{esc(ev.get("right_label", "MIRACLE"))}</div>'
         f'<div id="knob" style="position:absolute;left:{(x0 + x1) // 2 - 110}px;top:{y - 110}px;width:220px;height:220px;border-radius:110px;background:#fff;box-shadow:0 0 0 18px rgba(255,255,255,.18),0 20px 60px rgba(0,0,0,.6)"></div>'
         f'<div id="mid" class="din" style="position:absolute;left:{(x0 + x1) // 2 - 900}px;width:1800px;text-align:center;top:{y - 520}px;font-size:170px;color:{Y};opacity:0">{esc(ev.get("mid_label", "THE ANSWER: A NUMBER"))}</div>')
    span = (x1 - x0) // 2
    js = ['tl.fromTo("#slt",{y:-30},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
          f'tl.to("#knob",{{x:-{span},duration:SLIDE.dur,ease:SLIDE.ease}},{tl_:.3f});',
          f'tl.to("#knob",{{x:{span},duration:SLIDE.dur*1.3,ease:SLIDE.ease}},{tr_:.3f});',
          f'tl.to("#knob",{{x:0,duration:SOFT.dur*1.6,ease:SOFT.ease}},{tm:.3f});',
          f'tl.fromTo("#mid",{{opacity:0,y:30}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{tm + 0.3:.3f});']
    return b, js


FN.update({"wall": wall, "versus": versus, "checklist": checklist, "scissors": scissors, "detector": detector, "find": find, "slider": slider, "insert": insert})
TYPES = set(FN)


def body(ev, mock):
    return FN[ev["type"]](ev, mock)


def settle(ev):
    """When a breakdown mock should be shot: after the last timed element lands."""
    ts = list((ev.get("at_t") or {}).values())
    if ev["type"] == "clip": ts.append(ev.get("quote_at", 0) or 0)
    return min(ev["dur"] - 0.1, max(ts + [0.6]) + 0.9 + (0.6 if ev["type"] == "num" and ev.get("count", True) else 0))
