"""The protein bowl being built, as a code-drawn motion graphic (no AI imagery, OB's rule). Used by cards.py for "bowl" events.

An event names the bowl's state when its card slides in (start_state) and the steps that happen on screen, each at its
own spoken anchor (steps_t from resolve_events.py). Steps: yogurt (pours in and fills), whey (scoop tips in), mix
(swirl, powder disappears, the base turns peanut-butter cream), psyllium (husk sprinkles down), berries, kiwi.
Coordinates are the side panel's card area (2820 x 2160 before the panel scale). Motion: springs from cards.py
(POP / SNAP / SOFT / COUNT) and true free fall (y = g t^2: a custom ease, not a stock curve) for anything dropped.
"""
import math, random

Y = "#F7DC3A"
YOG, YOG_MIX, WHEY, SPECK = "#f7f4ec", "#efe1c6", "#e6d1a7", ("#c8ad7f", "#a98a5c", "#d9c39b")
PROTEIN = {"yogurt": 20, "whey": 50}   # OB's own numbers: ~20 g from the yogurt, +30 g from one scoop of whey
CX, CY = 500, 318                      # yogurt surface centre in the SVG (viewBox 1000 x 640)


def _pts(seed, n, rx, ry, cx=CX, cy=CY, left=None):
    """Points scattered inside the surface ellipse (deterministic, so every render matches the mockup)."""
    r, out = random.Random(seed), []
    while len(out) < n:
        x, y = r.uniform(-1, 1), r.uniform(-1, 1)
        if x * x + y * y > 1 or (left is True and x > 0.15) or (left is False and x < -0.05): continue
        out.append((cx + x * rx, cy + y * ry))
    return out


def svg(state):
    """Bowl SVG. Elements a step animates start hidden unless `state` (ingredients already in) shows them."""
    has = set(state)
    yog_fill = YOG_MIX if "mix" in has else YOG
    show = lambda k: "1" if k in has else "0"
    specks = "".join(f'<rect class="sp" x="{x - 6:.1f}" y="{y - 2:.1f}" width="12" height="4.5" rx="2" fill="{SPECK[i % 3]}" '
                     f'transform="rotate({(i * 37) % 180} {x:.1f} {y:.1f})" opacity="{show("psyllium")}"/>'
                     for i, (x, y) in enumerate(_pts(7, 110, 275, 68)))
    berries = ""
    for i, (x, y) in enumerate(_pts(11, 10, 225, 52, left=True)):
        if i % 3 == 2:   # raspberry: a cluster of drupelets
            dr = "".join(f'<circle cx="{x + dx:.1f}" cy="{y + dy:.1f}" r="12" fill="{c}"/>' for dx, dy, c in
                         ((-11, 4, "#c2185b"), (11, 4, "#d81b60"), (0, -8, "#e91e63"), (0, 9, "#ad1457"), (-6, -2, "#ec407a"), (7, -3, "#d81b60")))
            berries += (f'<g class="fr" id="be{i}" opacity="{show("berries")}"><ellipse cx="{x + 4:.1f}" cy="{y + 20:.1f}" rx="27" ry="8" fill="#000" opacity=".22"/>'
                        f'{dr}<circle cx="{x - 8:.1f}" cy="{y - 8:.1f}" r="4.4" fill="#fff" opacity=".55"/></g>')
        else:            # blueberry with its little crown
            berries += (f'<g class="fr" id="be{i}" opacity="{show("berries")}"><ellipse cx="{x + 4:.1f}" cy="{y + 21:.1f}" rx="26" ry="8" fill="#000" opacity=".22"/>'
                        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="24" fill="#2f3d7a"/><circle cx="{x:.1f}" cy="{y:.1f}" r="24" fill="url(#gBerry)"/>'
                        f'<circle cx="{x - 8:.1f}" cy="{y - 10:.1f}" r="6" fill="#fff" opacity=".5"/>'
                        f'<path d="M{x - 6:.1f},{y - 17:.1f} l6,4 l6,-4" stroke="#1a2244" stroke-width="3" fill="none"/></g>')
    kiwis = ""
    for i, (x, y) in enumerate(((612, 296), (705, 326), (590, 352), (676, 362))):
        seeds = "".join(f'<ellipse cx="{x + 23 * math.cos(a * 0.4488):.1f}" cy="{y + 15 * math.sin(a * 0.4488):.1f}" '
                        f'rx="3.4" ry="2.1" fill="#1b1b1b"/>' for a in range(14))
        kiwis += (f'<g class="kw" id="kw{i}" opacity="{show("kiwi")}"><ellipse cx="{x + 5}" cy="{y + 21}" rx="58" ry="14" fill="#000" opacity=".22"/>'
                  f'<ellipse cx="{x}" cy="{y}" rx="58" ry="38" fill="#7a5a2e"/><ellipse cx="{x}" cy="{y}" rx="52" ry="33" fill="#8cc63f"/>'
                  f'<ellipse cx="{x}" cy="{y}" rx="36" ry="23" fill="#b4dc5f"/>{seeds}<ellipse cx="{x}" cy="{y}" rx="13" ry="8.5" fill="#f3f8dc"/></g>')
    puffs = "".join(f'<circle class="pf" cx="{CX + 18 + dx}" cy="{CY - 18 + dy}" r="16" fill="{WHEY}" opacity="0"/>'
                    for dx, dy in ((-60, -10), (-25, -40), (20, -30), (60, -8), (-35, 10), (40, 12)))
    return f"""<svg id="bowl" viewBox="0 0 1000 640" width="2500" height="1600" style="position:absolute;left:160px;top:330px;overflow:visible">
<defs>
 <linearGradient id="gBody" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#f1efea"/><stop offset="1" stop-color="#c9c4bb"/></linearGradient>
 <linearGradient id="gShade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient>
 <linearGradient id="gIn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6f675d"/><stop offset=".55" stop-color="#a59d91"/><stop offset="1" stop-color="#d6d0c6"/></linearGradient>
 <radialGradient id="gBerry" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#6b7fc4" stop-opacity=".7"/><stop offset="1" stop-color="#1c2550" stop-opacity="0"/></radialGradient>
 <filter id="blur8"><feGaussianBlur stdDeviation="9"/></filter>
 <clipPath id="cav"><ellipse cx="500" cy="300" rx="343" ry="95"/></clipPath>
</defs>
<ellipse cx="500" cy="600" rx="330" ry="28" fill="#000" opacity=".5" filter="url(#blur8)"/>
<path d="M150,300 C150,470 290,585 500,585 C710,585 850,470 850,300 Z" fill="url(#gBody)"/>
<path d="M150,300 C150,470 290,585 500,585 C710,585 850,470 850,300 Z" fill="url(#gShade)"/>
<ellipse cx="500" cy="583" rx="128" ry="17" fill="#cdc7be"/>
<ellipse cx="500" cy="300" rx="350" ry="100" fill="url(#gIn)"/>
<g clip-path="url(#cav)">
 <ellipse id="yog" cx="{CX}" cy="{CY}" rx="322" ry="84" fill="{yog_fill}" style="fill:{yog_fill}"/>
 <ellipse id="yogHi" cx="420" cy="296" rx="130" ry="24" fill="#fff" opacity="{'.45' if 'yogurt' in has else '0'}"/>
 <path id="swirl" d="M500,318 m-6,0 a6,4 0 1,1 12,0 a18,10 0 1,1 -30,0 a34,18 0 1,1 62,0 a52,27 0 1,1 -96,0 a72,36 0 1,1 132,0" fill="none" stroke="#d9be8d" stroke-width="7" stroke-linecap="round" opacity="0"/>
</g>
<ellipse cx="500" cy="300" rx="350" ry="100" fill="none" stroke="#faf9f6" stroke-width="9"/>
<g id="whey"><ellipse cx="{CX + 18}" cy="{CY + 4}" rx="118" ry="30" fill="#d9c294"/><path d="M{CX - 92},{CY + 4} C{CX - 70},{CY - 62} {CX + 106},{CY - 62} {CX + 128},{CY + 4} Z" fill="{WHEY}"/></g>
<ellipse id="wheyTop" cx="{CX + 2}" cy="{CY - 30}" rx="52" ry="13" fill="#f3e6c8"/>
{puffs}
<g id="psy">{specks}</g>
{berries}{kiwis}
<rect id="stream" x="482" y="-40" width="36" height="358" rx="18" fill="{YOG}"/>
<g id="scoop">
 <path d="M650,95 h150 a16,16 0 0 1 16,16 v34 a72,62 0 0 1 -182,0 v-34 a16,16 0 0 1 16,-16 z" fill="#e8ecef"/>
 <path d="M650,95 h150 a16,16 0 0 1 16,16 v10 h-182 v-10 a16,16 0 0 1 16,-16 z" fill="#ffffff"/>
 <ellipse cx="725" cy="112" rx="80" ry="12" fill="{WHEY}"/>
 <rect x="808" y="104" width="170" height="26" rx="13" fill="#cfd8dc"/>
</g>
</svg>"""


def html(ev):
    steps = ev["steps"]; start = ev.get("start_state", [])
    p0 = max([PROTEIN.get(s, 0) for s in start] + [0])
    labels = "".join(f'<div class="bl din" id="bl{i}" style="position:absolute;left:0;width:2820px;top:120px;text-align:center;font-size:132px;opacity:0">{lab}</div>'
                     for i, (_, lab, _) in enumerate(steps))
    if ev.get("start_label"):   # what's already in the bowl, until the first step's label takes over
        labels += f'<div class="bl din" id="bls" style="position:absolute;left:0;width:2820px;top:120px;text-align:center;font-size:132px;opacity:0">{ev["start_label"]}</div>'
    return (f'<style>#bcnt::before{{counter-reset:n var(--n);content:counter(n)}}</style>{labels}{svg(start)}'
            f'<div style="position:absolute;left:0;width:2820px;top:1930px;text-align:center">'
            f'<span class="avb" style="font-size:84px;color:#d8d8d8;margin-right:34px">Protein</span>'
            f'<span id="bcnt" class="din" style="font-size:190px;color:{Y};--n:{p0}"></span><span class="din" style="font-size:150px;color:{Y}"> g</span></div>')


def js(ev):
    steps, ts = ev["steps"], ev.get("steps_t") or [0.3 + 2.0 * k for k in range(len(ev["steps"]))]
    start = ev.get("start_state", [])
    p = max([PROTEIN.get(s, 0) for s in start] + [0])
    out = ['const FALL = p => p * p;   // free fall: distance grows with t squared',
           *([f'tl.fromTo("#bls",{{opacity:0,y:24}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},.3);'] if ev.get("start_label") else []),
           f'tl.set("#yog",{{scale:{1 if "yogurt" in start else 0.001},svgOrigin:"{CX} {CY}",immediateRender:true}},0);',
           f'tl.set(["#whey","#wheyTop"],{{scale:{1 if ("whey" in start and "mix" not in start) else 0.001},svgOrigin:"{CX + 18} {CY + 20}",immediateRender:true}},0);',
           'tl.set("#stream",{scaleY:0.001,svgOrigin:"500 -40",immediateRender:true},0);',
           'tl.set("#scoop",{x:520,y:-420,rotation:0,svgOrigin:"730 150",immediateRender:true},0);',
           f'tl.set("#swirl",{{opacity:0,rotation:0,svgOrigin:"{CX} {CY}",immediateRender:true}},0);']
    for i, ((kind, _, _), t) in enumerate(zip(steps, ts)):
        t = max(t, 0.35)   # let the panel land first
        out.append(f'tl.fromTo("#bl{i}",{{opacity:0,y:24}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{t + 0.02:.3f});')
        if i: out.append(f'tl.to("#bl{i-1}",{{opacity:0,duration:.16,ease:"none"}},{max(t - 0.18, 0):.3f});')
        elif ev.get("start_label"): out.append(f'tl.to("#bls",{{opacity:0,duration:.16,ease:"none"}},{max(t - 0.18, 0):.3f});')
        if kind == "yogurt":
            out += [f'tl.fromTo("#stream",{{scaleY:0.001,svgOrigin:"500 -40"}},{{scaleY:1,svgOrigin:"500 -40",duration:.32,ease:FALL}},{t:.3f});',
                    f'tl.fromTo("#yog",{{scale:.12,svgOrigin:"{CX} {CY}"}},{{scale:1,svgOrigin:"{CX} {CY}",duration:SOFT.dur,ease:SOFT.ease,immediateRender:false}},{t + .25:.3f});',
                    f'tl.to("#stream",{{opacity:0,duration:.3,ease:"none"}},{t + 1.05:.3f});',
                    f'tl.fromTo("#yogHi",{{opacity:0}},{{opacity:.45,duration:SOFT.dur,ease:SOFT.ease}},{t + .9:.3f});']
        elif kind == "whey":
            out += [f'tl.fromTo("#scoop",{{x:520,y:-420,rotation:0}},{{x:0,y:0,rotation:0,duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});',
                    f'tl.to("#scoop",{{rotation:-118,duration:SNAP.dur,ease:SNAP.ease}},{t + .5:.3f});',
                    f'tl.fromTo(["#whey","#wheyTop"],{{scale:0.001,svgOrigin:"{CX + 18} {CY + 20}"}},{{scale:1,svgOrigin:"{CX + 18} {CY + 20}",duration:POP.dur,ease:POP.ease}},{t + .72:.3f});',
                    f'tl.fromTo(".pf",{{opacity:.9,scale:.4}},{{opacity:0,scale:2.2,duration:.9,ease:"none",stagger:.04}},{t + .78:.3f});',
                    f'tl.to("#scoop",{{x:560,y:-460,rotation:-60,duration:SNAP.dur,ease:SNAP.ease}},{t + 1.15:.3f});']
        elif kind == "mix":
            out += [f'tl.fromTo("#swirl",{{opacity:0,rotation:0,svgOrigin:"{CX} {CY}"}},{{opacity:.9,rotation:300,svgOrigin:"{CX} {CY}",duration:.6,ease:"none"}},{t:.3f});',
                    f'tl.to("#swirl",{{opacity:0,rotation:620,svgOrigin:"{CX} {CY}",duration:.9,ease:"none"}},{t + .6:.3f});',
                    f'tl.to(["#whey","#wheyTop"],{{scale:0.001,svgOrigin:"{CX + 18} {CY + 20}",duration:SOFT.dur,ease:SOFT.ease}},{t + .15:.3f});',
                    f'tl.to("#yog",{{fill:"{YOG_MIX}",duration:1.2,ease:"none"}},{t:.3f});']
        elif kind == "psyllium":
            out.append(f'tl.fromTo(".sp",{{opacity:0,y:i => -260 - (i * 53) % 220}},{{opacity:1,y:0,duration:.5,ease:FALL,stagger:.012}},{t:.3f});')
        elif kind == "berries":
            out += [f'tl.fromTo(".fr",{{opacity:0,y:-560}},{{opacity:1,y:0,duration:.46,ease:FALL,stagger:.11}},{t:.3f});',
                    f'tl.fromTo(".fr",{{scaleY:.86,transformOrigin:"50% 100%"}},{{scaleY:1,duration:POP.dur,ease:POP.ease,stagger:.11}},{t + .46:.3f});']
        elif kind == "kiwi":
            out += [f'tl.fromTo(".kw",{{opacity:0,y:-600,rotation:-24,transformOrigin:"50% 50%"}},{{opacity:1,y:0,rotation:0,duration:.5,ease:FALL,stagger:.16}},{t:.3f});',
                    f'tl.fromTo(".kw",{{scaleY:.84}},{{scaleY:1,duration:POP.dur,ease:POP.ease,stagger:.16}},{t + .5:.3f});']
        if kind in PROTEIN and PROTEIN[kind] != p:
            out.append(f'tl.fromTo("#bcnt",{{"--n":{p}}},{{"--n":{PROTEIN[kind]},duration:COUNT.dur,ease:COUNT.ease,snap:{{"--n":1}}}},{t + .6:.3f});')
            p = PROTEIN[kind]
    out.append(f'tl.fromTo("#bowl",{{scale:1}},{{scale:1.035,duration:{max(ev["dur"] - 0.6, 1):.3f},ease:"none",transformOrigin:"50% 60%"}},.3);')
    return out
