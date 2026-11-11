#!/usr/bin/env python3
"""Animated diagrams for the night reels (Reset, Losers). OB 2026-10-16: "add better graphics to be better
visual or animations rather than just text overlays and pop ups".

  python3 lecture_viz.py EDL.json PROJECT_DIR NAME [--mock | --overlay]

Same base as lecture_cards.py (frame-1 hook, 3-word captions with the live word in yellow), but each text card
becomes a code-drawn diagram that acts out the line: a baseline chart that spikes and snaps back, a calendar with
confetti, a week strip, a habit grid, a draining hope battery, an anchor, a potential bar, the 5-people ring, a
group chat. Every move is keyed to the spoken word: Whisper DTW times on the edit's own voice track
(spec["viz"]["words"]); captions use the same times.
Motion: closed-form springs (POP/SNAP/SOFT/STAMP), constant speed for draws, ballistic arcs for confetti.
  --mock    one <img id="bg"> under the graphics, swapped per shot by viz_shots.js
  --overlay transparent page, graphics + captions only (preview frames composited over the cut by ffmpeg)
sfx_events(spec, proj) -> [(kind, t)] for lecture_render.py ("pop_2" = variant file pop_2.wav, same gain as pop).
"""
import difflib, json, math, os, random, re, sys
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecture_cards import CSS as BASE_CSS, SPRINGS, esc, W, H, Y, R   # noqa: E402

G, BL, GR, INK = "#34C759", "#0A84FF", "#8E8E93", "#121212"
J = json.dumps
# settle time of each spring, read from the same JS the page runs (m = 1: T = ln(1000) / (z * w0) when underdamped)
SPR = {n: (2 * math.log(1000) / c if c < 2 * math.sqrt(k) else 1.6 * math.log(1000) / math.sqrt(k))
       for n, k, c in ((n, int(k), int(c)) for n, k, c in re.findall(r"(\w+) = spring\((\d+), (\d+)\)", SPRINGS))}


def norm(w):
    return re.sub(r"[^a-z0-9%]", "", w.lower().replace("’", "'").replace("'", ""))


class Words:
    def __init__(self, path):
        self.w = json.load(open(path))
        for x in self.w:
            x["n"] = norm(x["w"]); x["t"] = x["dtw"] if x.get("dtw") is not None else x["t0"]

    def t(self, word, n=1):
        k = 0
        for x in self.w:
            if x["n"] == norm(word):
                k += 1
                if k == n: return x["t"]
        raise KeyError(f"word '{word}' #{n} is not in the voice track")


class Viz:
    """Collects page parts and GSAP lines. Every SVG element GSAP moves has no transform attribute of its own
    (positioning lives on an outer <g>), so GSAP's scale/rotation never fight a baked-in transform."""
    def __init__(self, proj):
        self.html, self.svg, self.defs, self.js, self.sfx = [], [], [], [], []
        self.font = lambda name, size: ImageFont.truetype(f"{proj}/assets/fonts/{name}.ttf", size)
        self.ent, self.bad = {}, []      # entrance springs per selector; exits that land inside one

    def a(self, s): self.js.append(s)
    def s(self, kind, t): self.sfx.append((kind, round(float(t), 3)))
    def _d(self, dur, sp): return (f"{dur:.3f}" if dur is not None else f"{sp}.dur"), ('"none"' if sp == "LIN" else f"{sp}.ease")

    def _in(self, sel, t, sp): self.ent.setdefault(sel, []).append((t, t + SPR[sp]))

    def _out(self, sel, t, dur):
        """An exit fade that finishes while the element's entrance spring is still settling gets undone frame by frame
        (GSAP stops re-rendering a finished tween, the spring keeps rendering): the element comes back and stays.
        Fade a wrapper instead."""
        for a, b in self.ent.get(sel, []):
            if a - 1e-3 <= t and t + dur < b:
                self.bad.append(f"{sel}: exit {t:.2f}-{t + dur:.2f} s ends inside its entrance spring {a:.2f}-{b:.2f} s")

    def fin(self, sel, t, dy=40, sp="SOFT", dx=0):
        self._in(sel, t, sp)
        self.a(f'tl.fromTo({J(sel)},{{opacity:0,y:{dy},x:{dx}}},{{opacity:1,y:0,x:0,duration:{sp}.dur,ease:{sp}.ease}},{t:.3f});')

    def fout(self, sel, t, dy=-30, sp="SOFT", dx=0):
        self._out(sel, t, SPR[sp])
        self.a(f'tl.to({J(sel)},{{opacity:0,y:{dy},x:{dx},duration:{sp}.dur,ease:{sp}.ease}},{t:.3f});')

    def xout(self, sel, t, dur=0.16):
        """Segment exit: a quick straight fade, no movement, so the next visual never crosses it."""
        self._out(sel, t, dur)
        self.a(f'tl.to({J(sel)},{{opacity:0,duration:{dur},ease:"none"}},{t:.3f});')

    def pop(self, sel, t, s0=0.4, sp="POP", r0=0, r1=0, origin="50% 50%"):
        self._in(sel, t, sp)
        self.a(f'tl.fromTo({J(sel)},{{opacity:0,scale:{s0},rotation:{r0},transformOrigin:{J(origin)}}},'
               f'{{opacity:1,scale:1,rotation:{r1},duration:{sp}.dur,ease:{sp}.ease}},{t:.3f});')

    def set(self, sel, props, t): self.a(f'tl.set({J(sel)},{props},{t:.3f});')

    def to(self, sel, props, t, dur=None, sp="SOFT"):
        d, e = self._d(dur, sp); self.a(f'tl.to({J(sel)},{{{props},duration:{d},ease:{e}}},{t:.3f});')

    def draw(self, sel, t, dur=None, sp="SOFT"):
        d, e = self._d(dur, sp); self.a(f'DRAW({J(sel)},{t:.3f},{d},{e});')

    def follow(self, sel, pts, ax="cx", ay="cy", dy=0.0):
        """Constant-speed path following: linear attr tweens between dense samples [(t, x, y)]."""
        t0, x0, y0 = pts[0]
        self.set(sel, f"{{attr:{{{ax}:{x0:.1f},{ay}:{y0 + dy:.1f}}}}}", t0)
        for (ta, _, _), (tb, xb, yb) in zip(pts, pts[1:]):
            if tb - ta > 1e-3:
                self.a(f'tl.to({J(sel)},{{attr:{{{ax}:{xb:.1f},{ay}:{yb + dy:.1f}}},duration:{tb - ta:.3f},ease:"none"}},{ta:.3f});')

    def label(self, id_, text, t, color=Y, x=110, y=990, size=60, center=False, t_out=None):
        pos = f"left:0;width:{W}px;text-align:center;" if center else f"left:{x}px;"
        self.html.append(f'<div class="vlab" id="{id_}" style="{pos}top:{y}px;font-size:{size}px;color:{color}">{esc(text)}</div>')
        self.fin(f"#{id_}", t, dy=24)
        if t_out is not None: self.fout(f"#{id_}", t_out)

    def chip(self, id_, text, cx, top, bg, t, color="#fff", size=44):
        self.html.append(f'<div class="chip" id="{id_}" style="left:{cx}px;top:{top}px;background:{bg};color:{color};font-size:{size}px">{esc(text)}</div>')
        self.a(f'gsap.set("#{id_}",{{xPercent:-50}});')
        self.pop(f"#{id_}", t, s0=0.3)


def sample(kf, yf, step=6):
    """Reveal keyframes [(t, x)] + curve y(x) -> dense [(t, x, y)] at constant speed inside each interval."""
    pts = []
    for (ta, xa), (tb, xb) in zip(kf, kf[1:]):
        n = max(1, int(abs(xb - xa) / step))
        for i in range(n):
            f = i / n; pts.append((ta + (tb - ta) * f, xa + (xb - xa) * f, yf(xa + (xb - xa) * f)))
    pts.append((kf[-1][0], kf[-1][1], yf(kf[-1][1])))
    return pts


def poly(xs, yf):
    return "M" + " L".join(f"{x:.1f},{yf(x):.1f}" for x in xs)


def rng(a, b, step):
    out, x = [], a
    while x < b: out.append(x); x += step
    return out + [b]


def person(id_, x, y, s=1.0, fill=GR):
    """Contacts-style person glyph centred at (x, y); GSAP animates the inner group."""
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})"><g id="{id_}" style="opacity:0">'
            f'<circle cx="0" cy="-22" r="21" fill="{fill}"/><path d="M-36,36 C-36,4 36,4 36,36 Z" fill="{fill}"/></g></g>')


def check_path(x, y, s=1.0):
    return f"M{x - 22 * s:.1f},{y + 1 * s:.1f} L{x - 7 * s:.1f},{y + 16 * s:.1f} L{x + 23 * s:.1f},{y - 15 * s:.1f}"


def wrap(font, text, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


# ------------------------------------------------------------------------------------------------ RESET
def reset_seq(V, T, D):
    f1_out = 2.5
    # 0. reset arrow beside the frame-1 hook: draws in, then spins once on "reset"
    cx, cy, r = 122, 928, 42
    p = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (sx, sy), (ex, ey) = p(-60), p(232)
    dx, dy = -math.sin(math.radians(232)), math.cos(math.radians(232))      # travel direction (clockwise) at the end
    nx, ny = -dy, dx
    tip = (ex + dx * 20, ey + dy * 20); b1 = (ex + nx * 15 - dx * 4, ey + ny * 15 - dy * 4); b2 = (ex - nx * 15 - dx * 4, ey - ny * 15 - dy * 4)
    V.svg.append(f'<g id="rsG" style="opacity:0"><g id="rsI"><path id="rsA" d="M{sx:.1f},{sy:.1f} A{r},{r} 0 1 1 {ex:.1f},{ey:.1f}" '
                 f'stroke="{Y}" stroke-width="13" fill="none" stroke-linecap="round"/>'
                 f'<path id="rsH" d="M{tip[0]:.1f},{tip[1]:.1f} L{b1[0]:.1f},{b1[1]:.1f} L{b2[0]:.1f},{b2[1]:.1f} Z" fill="{Y}" '
                 f'stroke="{Y}" stroke-width="6" stroke-linejoin="round" style="opacity:0"/></g></g>')
    V.set("#rsG", "{opacity:1}", 0.0)
    V.draw("#rsA", 0.03, sp="SOFT"); V.pop("#rsH", 0.30, s0=0.2)
    V.a(f'tl.to("#rsI",{{rotation:360,svgOrigin:"{cx} {cy}",duration:SNAP.dur,ease:SNAP.ease}},{T("reset") - 0.06:.3f});')
    V.s("tick", T("reset") - 0.06)
    V.fout("#rsG", f1_out)

    # 1. the baseline chart: flat, a dip that snaps back on "baseline", a green spike on "best", a red one on
    #    "worst", then a yellow run at "your most productive level"
    X0, X1, YB, A = 110, 980, 1235, 140
    def yf(x):
        if 270 <= x <= 430: return YB + 95 * math.sin(math.pi * (x - 270) / 160)
        if 560 <= x <= 700: return YB - A * math.sin(math.pi * (x - 560) / 140)
        if 730 <= x <= 870: return YB + A * math.sin(math.pi * (x - 730) / 140)
        return YB
    t_in, t_out = T("the", 1), T("can", 3) - 0.28
    kf = [(t_in + 0.15, 110), (T("can", 1) - 0.10, 270), (T("right", 1) + 0.04, 350), (T("baseline", 1), 430),
          (T("best") - 0.25, 560), (T("best") + 0.12, 630), (T("world") + 0.05, 700), (T("worst") - 0.08, 730),
          (T("worst") + 0.30, 800), (T("get", 2), 870), (T("level"), 980)]
    segs = [(110, 560, "#fff", ""), (560, 700, G, ""), (700, 730, "#fff", ""), (730, 870, R, ""), (870, 980, Y, ' filter="url(#glow)"')]
    V.defs.append(f'<clipPath id="chClip"><rect id="chCR" x="{X0 - 16}" y="900" width="0" height="700"/></clipPath>')
    paths = "".join(f'<path d="{poly(rng(a, b, 4), yf)}" stroke="{c}" stroke-width="14" fill="none" stroke-linecap="round" '
                    f'stroke-linejoin="round"{f}/>' for a, b, c, f in segs)
    V.svg.append(f'<g id="chG" style="opacity:0">'
                 f'<line id="chBL" x1="{X0}" y1="{YB}" x2="{X1}" y2="{YB}" stroke="#fff" stroke-opacity=".35" stroke-width="4" stroke-dasharray="14 12"/>'
                 f'<text id="chBT" x="{X0}" y="{YB - 20}" class="svl" fill="#fff" fill-opacity=".62">BASELINE</text>'
                 f'<g clip-path="url(#chClip)">{paths}</g>'
                 f'<circle id="chD" cx="{X0}" cy="{YB}" r="14" fill="{Y}" filter="url(#glow)" style="opacity:0"/></g>')
    V.label("chL", "BACK TO BASELINE", t_in)
    V.set("#chG", "{opacity:1}", t_in)
    V.a(f'tl.fromTo("#chBL",{{scaleX:0,transformOrigin:"0% 50%"}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{t_in:.3f});')
    V.fin("#chBT", t_in + 0.1, dy=10)
    for (ta, xa), (tb, xb) in zip(kf, kf[1:]):
        V.a(f'tl.to("#chCR",{{attr:{{width:{xb - X0 + 32}}},duration:{tb - ta:.3f},ease:"none"}},{ta:.3f});')
    V.set("#chD", "{opacity:1}", kf[0][0]); V.follow("#chD", sample(kf, yf))
    V.chip("chBest", "BEST DAY", 630, YB - A - 74, G, T("best") + 0.05)
    V.chip("chWorst", "WORST DAY", 800, YB + A + 26, R, T("worst") + 0.28)
    for t in (T("baseline", 1), T("get", 2)):
        V.set("#chBL", f'{{stroke:"{Y}",strokeOpacity:1}}', t); V.set("#chBL", '{stroke:"#fff",strokeOpacity:.35}', t + 0.5)
    V.set("#chBL", f'{{stroke:"{Y}",strokeOpacity:.9}}', T("productive")); V.set("#chBT", f'{{fill:"{Y}",fillOpacity:1}}', T("productive"))
    for sel in ("#chG", "#chL", "#chBest", "#chWorst"): V.xout(sel, t_out)
    V.s("whoosh", t_in); V.s("tick", T("baseline", 1)); V.s("pop", T("best") + 0.05); V.s("pop_2", T("worst") + 0.28)
    V.s("tick_2", T("get", 2)); V.s("tick_3", T("productive"))

    # 2. celebrate the win: calendar page with a trophy, confetti on "wins", a 1 DAY badge, then the page flips to
    #    NEXT DAY / BASELINE on "go right back"
    t_c, t_flip, t_c_out = T("celebrate") - 0.15, T("go") + 0.10, T("can", 4) - 0.20
    trophy = (f'<svg class="tro" viewBox="-100 -100 200 200" width="190" height="190">'
              f'<path d="M-62,-36 C-104,-36 -100,22 -48,22" stroke="{Y}" stroke-width="12" fill="none" stroke-linecap="round"/>'
              f'<path d="M62,-36 C104,-36 100,22 48,22" stroke="{Y}" stroke-width="12" fill="none" stroke-linecap="round"/>'
              f'<path d="M-62,-66 H62 V-24 C62,22 32,44 0,44 C-32,44 -62,22 -62,-24 Z" fill="{Y}"/>'
              f'<rect x="-11" y="42" width="22" height="26" fill="{Y}"/><rect x="-46" y="66" width="92" height="20" rx="7" fill="{Y}"/>'
              f'<path d="M0,-50 L9,-30 L31,-28 L14,-14 L19,8 L0,-3 L-19,8 L-14,-14 L-31,-28 L-9,-30 Z" fill="#fff" fill-opacity=".9"/></svg>')
    flat = (f'<svg class="tro" viewBox="-100 -100 200 200" width="190" height="190">'
            f'<line x1="-82" y1="0" x2="82" y2="0" stroke="#111" stroke-width="8" stroke-dasharray="14 10" stroke-linecap="round"/>'
            f'<circle cx="0" cy="0" r="17" fill="{Y}" stroke="#111" stroke-width="5"/></svg>')
    V.html.append(f'<div id="cal" class="cal" style="left:390px;top:1028px">'
                  f'<div class="face" id="calF"><div class="calh" style="background:{R}">TODAY</div>{trophy.replace("<svg class", "<svg id=\"calT\" class", 1)}</div>'
                  f'<div class="face" id="calB"><div class="calh" style="background:#3A3A3C">NEXT DAY</div>{flat}<div class="calt">BASELINE</div></div>'
                  f'<div id="calBW" style="position:absolute;inset:0"><div id="calBadge" class="badge">1 DAY</div></div></div>')
    V.pop("#cal", t_c, s0=0.55); V.set("#calB", "{rotationX:-90,transformPerspective:1400}", 0); V.set("#calF", "{transformPerspective:1400}", 0)
    V.set("#calT", '{transformOrigin:"50% 70%"}', 0)
    V.a(f'tl.to("#calT",{{keyframes:[{{rotation:-9,duration:.09}},{{rotation:7,duration:.12}},{{rotation:0,duration:SOFT.dur,ease:SOFT.ease}}]}},{T("wins"):.3f});')
    rnd = random.Random(7); cols = [Y, G, "#fff", R, BL]
    ox, oy, grav, life = 540, 1068, 2600.0, 1.3
    parts = []
    for i in range(44):
        vx, vy = rnd.uniform(-640, 640), rnd.uniform(-1300, -720); ta = -vy / grav; ya = -vy * vy / (2 * grav)
        yb = ya + 0.5 * grav * (life - ta) ** 2; w, h = rnd.choice([(12, 20), (14, 14), (10, 24)])
        parts.append(f'<g transform="translate({ox},{oy})"><rect id="cf{i}" x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="3" fill="{cols[i % 5]}" style="opacity:0"/></g>')
        t0 = T("wins") + rnd.uniform(0, 0.06)
        V.set(f"#cf{i}", "{opacity:1}", t0)
        V.a(f'tl.to("#cf{i}",{{x:{vx * life:.1f},rotation:{rnd.choice([-1, 1]) * rnd.uniform(360, 900):.0f},transformOrigin:"50% 50%",duration:{life},ease:"none"}},{t0:.3f});')
        V.a(f'tl.to("#cf{i}",{{y:{ya:.1f},duration:{ta:.3f},ease:UP}},{t0:.3f});')
        V.a(f'tl.to("#cf{i}",{{y:{yb:.1f},duration:{life - ta:.3f},ease:DOWN}},{t0 + ta:.3f});')
        V.a(f'tl.to("#cf{i}",{{opacity:0,duration:.35,ease:"none"}},{t0 + life - 0.35:.3f});')
    V.svg.append(f'<g id="cfG">{"".join(parts)}</g>')
    V.pop("#calBadge", T("one"), s0=0.2, sp="STAMP", r0=-30, r1=8)
    V.to("#calBW", "opacity:0", t_flip - 0.04, dur=0.12, sp="LIN")
    V.to("#calF", "rotationX:90", t_flip, dur=0.16, sp="LIN")
    V.to("#calB", "rotationX:0", t_flip + 0.16, sp="SNAP")
    V.xout("#cal", t_c_out)
    V.s("pop", t_c); V.s("pop_3", T("wins")); V.s("tick", T("wins") + 0.05); V.s("tick_2", T("one")); V.s("whoosh_2", t_flip)

    # 3. the week: two green days, a red X on "off", a yellow arrow on "baseline" (3rd), green the next day,
    #    then a ghost row shows the week spiral that DOESN'T happen and gets struck out
    t_w, t_w_out = t_c_out + 0.12, T("it's", 1) - 0.25
    xs = [150 + k * 130 for k in range(7)]; yc, rr = 1160, 48
    g = [f'<text x="{x}" y="1088" class="svd" text-anchor="middle">{d}</text>' for x, d in zip(xs, "MTWTFSS")]
    g += [f'<circle cx="{x}" cy="{yc}" r="{rr}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="5"/>' for x in xs]
    for k, x in enumerate(xs):
        if k == 2:
            g.append(f'<g id="wd{k}" style="opacity:0"><circle cx="{x}" cy="{yc}" r="{rr}" fill="{R}"/>'
                     f'<path d="M{x - 18},{yc - 18} L{x + 18},{yc + 18} M{x + 18},{yc - 18} L{x - 18},{yc + 18}" stroke="#fff" stroke-width="10" stroke-linecap="round"/></g>')
        else:
            g.append(f'<g id="wd{k}" style="opacity:0"><circle cx="{x}" cy="{yc}" r="{rr}" fill="{G}"/></g>'
                     f'<path id="wc{k}" d="{check_path(x, yc)}" stroke="#fff" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    ax0, ax1 = xs[2], xs[3]
    g.append(f'<path id="wArr" d="M{ax0 + 6},{yc + rr + 8} C{ax0 + 30},{yc + rr + 62} {ax1 - 30},{yc + rr + 62} {ax1 - 8},{yc + rr + 12}" '
             f'stroke="{Y}" stroke-width="9" fill="none" stroke-linecap="round"/>')
    hx, hy = ax1 - 8, yc + rr + 12
    g.append(f'<path id="wArrH" d="M{hx - 2},{hy - 6} L{hx - 20},{hy + 12} L{hx + 6},{hy + 16} Z" fill="{Y}" stroke="{Y}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>')
    g.append(f'<text id="wNext" x="{ax1}" y="{yc + rr + 92}" class="svl" text-anchor="middle" fill="#fff" style="opacity:0">NEXT DAY</text>')
    gy, gr = 1372, 26
    ghost = [f'<text x="110" y="{gy + 12}" class="svl" fill="{R}">WEEK SPIRAL</text>']
    for k in range(2, 7):
        x = xs[k]
        ghost.append(f'<circle cx="{x}" cy="{gy}" r="{gr}" fill="none" stroke="#fff" stroke-opacity=".25" stroke-width="4"/>'
                     f'<g id="gx{k}" style="opacity:0"><circle cx="{x}" cy="{gy}" r="{gr}" fill="{R}" fill-opacity=".85"/>'
                     f'<path d="M{x - 10},{gy - 10} L{x + 10},{gy + 10} M{x + 10},{gy - 10} L{x - 10},{gy + 10}" stroke="#fff" stroke-width="6" stroke-linecap="round"/></g>')
    ghost.append(f'<line id="gStrike" x1="96" y1="{gy}" x2="{xs[6] + 40}" y2="{gy}" stroke="{R}" stroke-width="12" stroke-linecap="round"/>')
    V.svg.append(f'<g id="wkG" style="opacity:0">{"".join(g)}<g id="ghG" style="opacity:0">{"".join(ghost)}</g></g>')
    V.label("wkL", "FELL OFF PLAN?", T("fall"))
    V.fin("#wkG", t_w, dy=30)
    V.draw("#wArr", -1, dur=0.001, sp="LIN")          # registers the dash (hidden) at load; drawn for real below
    for k in (0, 1, 3, 4, 5, 6): V.draw(f"#wc{k}", -1, dur=0.001, sp="LIN")
    def day_ok(k, t, big=False):
        V.pop(f"#wd{k}", t, s0=0.3 if big else 0.5, sp="POP" if big else "SNAP")
        V.a(f'tl.fromTo("#wc{k}",{{strokeDashoffset:CL("#wc{k}")}},{{strokeDashoffset:0,duration:.22,ease:"none",immediateRender:false}},{t + 0.08:.3f});')
    day_ok(0, t_w + 0.10); day_ok(1, t_w + 0.26)
    V.pop("#wd2", T("off"), s0=0.3, sp="POP")
    V.a(f'tl.to("#wd2",{{keyframes:[{{x:-10,duration:.05}},{{x:9,duration:.06}},{{x:-6,duration:.06}},{{x:0,duration:.08}}]}},{T("off") + 0.12:.3f});')
    V.a(f'tl.fromTo("#wArr",{{strokeDashoffset:CL("#wArr")}},{{strokeDashoffset:0,duration:SOFT.dur,ease:SOFT.ease,immediateRender:false}},{T("baseline", 3):.3f});')
    V.pop("#wArrH", T("baseline", 3) + 0.30, s0=0.2)
    day_ok(3, T("next"), big=True)
    V.fin("#wNext", T("next") + 0.10, dy=14)
    for j, k in enumerate((4, 5, 6)): day_ok(k, T("doesn't", 2) + 0.05 + j * 0.14)
    V.fin("#ghG", T("turn"), dy=16)
    for j, k in enumerate(range(2, 7)): V.pop(f"#gx{k}", T("turn") + 0.12 + j * 0.11, s0=0.4, sp="SNAP")
    V.draw("#gStrike", T("spiral") + 0.22, dur=0.24, sp="LIN")
    V.to("#ghG", "opacity:.28", T("spiral") + 0.50)
    V.xout("#wkG", t_w_out); V.xout("#wkL", t_w_out)
    V.s("whoosh_3", t_w); V.s("tick", t_w + 0.10); V.s("tick_2", t_w + 0.26); V.s("thud", T("off")); V.s("tick_3", T("baseline", 3))
    V.s("pop", T("next")); V.s("tick_4", T("doesn't", 2) + 0.05)
    for j in range(5): V.s(f"tick_{1 + j % 4}" if j else "tick", T("turn") + 0.12 + j * 0.11)
    V.s("thud_2", T("spiral") + 0.22)

    # 4. IT'S NOT ABOUT / PERFECTION, struck out in red
    t_p, t_p_out = T("it's", 1) - 0.02, T("it's", 2) - 0.15
    V.label("pfL", "IT'S NOT ABOUT", t_p, center=True)
    V.html.append('<div class="big" id="pfW" style="top:1072px">PERFECTION</div>')
    V.pop("#pfW", T("about", 1), s0=0.6, sp="SNAP")
    V.svg.append(f'<line id="pfS" x1="150" y1="1162" x2="930" y2="1162" stroke="{R}" stroke-width="16" stroke-linecap="round"/>')
    V.draw("#pfS", -1, dur=0.001, sp="LIN")
    V.a(f'tl.fromTo("#pfS",{{strokeDashoffset:CL("#pfS")}},{{strokeDashoffset:0,duration:.18,ease:"none",immediateRender:false}},{T("perfection") + 0.12:.3f});')
    for sel in ("#pfL", "#pfW", "#pfS"): V.xout(sel, t_p_out)
    V.s("pop_4", T("about", 1)); V.s("thud", T("perfection") + 0.12)

    # 5. IT'S ABOUT / CONSISTENCY: a 4 x 16 habit grid fills column by column (a few misses) to "consistent"
    V.label("csL", "IT'S ABOUT", T("it's", 2) + 0.06, center=True)
    V.html.append('<div class="big" id="csW" style="top:1068px;font-size:120px">CONSISTENCY</div>')
    V.pop("#csW", T("consistency") - 0.05, s0=0.6, sp="SNAP")
    sq, gap, nc, nr = 42, 10, 16, 4
    gx0, gy0 = (W - (nc * (sq + gap) - gap)) // 2, 1216
    miss = {(1, 3), (3, 6), (0, 9), (2, 13)}
    cells = [f'<rect id="hg{c}_{r}" x="{gx0 + c * (sq + gap)}" y="{gy0 + r * (sq + gap)}" width="{sq}" height="{sq}" rx="9" fill="#2a2a2d"/>'
             for c in range(nc) for r in range(nr)]
    V.svg.append(f'<g id="hgG" style="opacity:0">{"".join(cells)}</g>')
    V.fin("#hgG", T("it's", 2) + 0.30, dy=20)
    f0, f1 = T("consistency") + 0.15, T("consistent") + 0.30
    for c in range(nc):
        tc = f0 + (f1 - f0) * c / (nc - 1)
        for r in range(nr):
            if (r, c) in miss: continue
            V.set(f"#hg{c}_{r}", f'{{fill:"{G}"}}', tc + r * 0.02)
            V.a(f'tl.fromTo("#hg{c}_{r}",{{scale:.55,transformOrigin:"50% 50%"}},{{scale:1,duration:SNAP.dur,ease:SNAP.ease,immediateRender:false}},{tc + r * 0.02:.3f});')
        if c % 4 == 0: V.s(f"tick_{1 + (c // 4) % 4}", tc)
    V.s("pop_2", T("consistency") - 0.05); V.s("pop", f1)
    return f1_out, T("the", 1) - 0.05     # hook out, scrim in


# ------------------------------------------------------------------------------------------------ LOSERS
def bubbles_panel(V, pid, x, top, w, h, header, msgs, color, t_in, t_out, font, extra=""):
    """Chat panel; msgs [(text, t)] stack up from the bottom, older ones pushed up (clipped under the header)."""
    area_top, gap, pad = 104, 14, 26
    lines = [wrap(font, m, w - 2 * pad - 2 * 28 - 50) for m, _ in msgs]
    hs = [len(L) * 52 + 38 for L in lines]
    area_h = h - area_top - 12
    out = [f'<div class="panel" id="{pid}" style="left:{x}px;top:{top}px;width:{w}px;height:{h}px">{header}'
           f'<div class="area" style="top:{area_top}px;height:{area_h}px">']
    for k, ((m, t), L, hk) in enumerate(zip(msgs, lines, hs)):
        bw = max(font.getlength(s) for s in L) + 2 * 28 + 10
        out.append(f'<div class="bub" id="{pid}b{k}" style="left:{pad}px;top:{area_h - 16 - hk}px;width:{bw:.0f}px;height:{hk}px;background:{color}">'
                   + "<br>".join(esc(s) for s in L) + "</div>")
    out.append(extra + "</div></div>")
    V.html.append("".join(out))
    V.fin(f"#{pid}", t_in, dy=0, dx=120)
    for j, (_, t) in enumerate(msgs):
        V.pop(f"#{pid}b{j}", t, s0=0.6, sp="SNAP", origin="0% 100%")
        for k in range(j):
            shift = -(sum(hs[k + 1:j + 1]) + (j - k) * gap)
            V.to(f"#{pid}b{k}", f"y:{shift}", t, sp="SNAP")
    if t_out is not None: V.xout(f"#{pid}", t_out)
    return hs


def losers_seq(V, T, D):
    f1_out = min(2.5, T("get", 2) + 0.15)      # the hook clears as the second "Get away" starts (10-16 tighter cut)
    font = V.font("AvenirNext-DemiBold", 42)

    # 1. "no-hopers": a HOPE battery drains green -> yellow -> red to 0%, NO-HOPERS stamps on
    t_b, t_b_out = f1_out + 0.25, T("they", 1) - 0.08
    V.svg.append(f'<g id="btG" style="opacity:0"><rect x="330" y="1112" width="380" height="180" rx="30" fill="none" stroke="#fff" stroke-width="12"/>'
                 f'<rect x="716" y="1166" width="24" height="72" rx="8" fill="#fff"/>'
                 f'<rect id="btF" x="350" y="1132" width="340" height="140" rx="16" fill="{G}"/>'
                 f'<text x="520" y="1226" class="svb" text-anchor="middle" fill="#fff">HOPE</text>'
                 + "".join(f'<text id="btP{v}" x="520" y="1368" class="svp" text-anchor="middle" fill="{"#fff" if v >= 30 else R}" style="opacity:0">{v}%</text>'
                           for v in range(100, -1, -10)) + "</g>")
    V.fin("#btG", t_b, dy=30)
    d0, d1 = t_b + 0.30, T("hopers") + 0.05
    V.to("#btF", "attr:{width:0}", d0, dur=d1 - d0, sp="LIN")
    V.set("#btF", f'{{fill:"{Y}"}}', d0 + (d1 - d0) * 0.5); V.set("#btF", f'{{fill:"{R}"}}', d0 + (d1 - d0) * 0.8)
    marks = [(v, d0 + (d1 - d0) * (1 - v / 100) - (0.25 if v == 100 else 0)) for v in range(100, -1, -10)]
    for (v, t), nxt in zip(marks, marks[1:] + [(None, None)]):
        V.set(f"#btP{v}", "{opacity:1}", t)
        if nxt[1] is not None: V.set(f"#btP{v}", "{opacity:0}", nxt[1])
    for k in range(3):
        V.set("#btP0", "{opacity:.15}", d1 + 0.16 + k * 0.16); V.set("#btP0", "{opacity:1}", d1 + 0.24 + k * 0.16)
    V.html.append('<div class="stamp2" id="nhS">NO-HOPERS</div>')
    V.a('gsap.set("#nhS",{xPercent:-50});')
    V.pop("#nhS", T("no"), s0=2.2, sp="STAMP", r0=-16, r1=-6)
    V.xout("#btG", t_b_out); V.xout("#nhS", t_b_out)
    V.s("whoosh", t_b); V.s("tick", d0); V.s("tick_2", (d0 + d1) / 2); V.s("thud", T("no"))

    # 2. "drag you down to their expectations": the YOU bar shoots up, gets dragged down onto the dashed
    #    THEIR EXPECTATIONS line and goes grey
    t_d, t_d_out = T("they", 1) + 0.06, T("they're") - 0.05
    base, top_hi, top_lo = 1430, 1080, 1332
    V.svg.append(f'<g id="dgG" style="opacity:0">'
                 f'<g id="dgE" style="opacity:0"><line x1="120" y1="{top_lo}" x2="960" y2="{top_lo}" stroke="{GR}" stroke-width="5" stroke-dasharray="16 12"/>'
                 f'<text x="120" y="{top_lo - 18}" class="svl" fill="#c7c7cc" style="font-size:44px">THEIR EXPECTATIONS</text></g>'
                 f'<rect id="dgB" x="470" y="{base}" width="140" height="0" rx="14" fill="{Y}"/>'
                 f'<text id="dgY" x="540" y="{base + 62}" class="svb" text-anchor="middle" fill="{INK}" style="font-size:56px;opacity:0">YOU</text>'
                 + "".join(f'<path id="dgC{k}" d="M500,{1006 + k * 26} L540,{1030 + k * 26} L580,{1006 + k * 26}" stroke="{GR}" stroke-width="9" fill="none" '
                           f'stroke-linecap="round" stroke-linejoin="round" style="opacity:0"/>' for k in range(3)) + "</g>")
    V.label("dgL", "THEY DRAG YOU DOWN", t_d)
    V.set("#dgG", "{opacity:1}", t_d)
    V.to("#dgB", f"attr:{{y:{top_hi},height:{base - top_hi}}}", t_d + 0.05, sp="SOFT")
    V.to("#dgY", f"attr:{{y:{top_hi + 62}}}", t_d + 0.05, sp="SOFT")
    V.to("#dgY", "opacity:1", t_d + 0.12, dur=0.12, sp="LIN")      # shows once the bar is tall enough to hold it
    for k in range(3): V.fin(f"#dgC{k}", T("drag", 1) + k * 0.08, dy=-20, sp="SNAP")
    V.fin("#dgE", T("drag", 1) + 0.25, dy=0)
    t_sink = T("down", 1)
    V.to("#dgB", f"attr:{{y:{top_lo},height:{base - top_lo}}}", t_sink, sp="SNAP")
    V.to("#dgY", f"attr:{{y:{top_lo + 62}}}", t_sink, sp="SNAP")
    for k in range(3): V.to(f"#dgC{k}", f"y:{top_lo - top_hi},opacity:0", t_sink, sp="SNAP")
    V.set("#dgB", f'{{fill:"{GR}"}}', T("expectations"))
    V.xout("#dgG", t_d_out); V.xout("#dgL", t_d_out)
    V.s("tick", t_d + 0.05); V.s("whoosh_2", t_sink); V.s("thud", T("expectations"))

    # 3. the anchor: drops into the water on "anchor", swings, the chain flashes on "tied", sinks on "drag you down
    #    to the bottom of the ocean" with bubbles rising and the water darkening
    t_a, t_a_out = T("they're") + 0.08, T("so", 1) - 0.12          # out just before "so many people" (the soft "And" is cut)
    wl = 120
    wave = "M-200,1158 " + " ".join(f"Q{x + wl / 4:.0f},{1158 - 12 if (i % 2 == 0) else 1158 + 12} {x + wl / 2:.0f},1158" for i, x in enumerate(range(-200, 1300, wl // 2))) + " L1300,1480 L-200,1480 Z"
    V.defs.append('<linearGradient id="wGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d4f86" stop-opacity=".88"/>'
                  '<stop offset="1" stop-color="#031526" stop-opacity=".96"/></linearGradient>'
                  '<clipPath id="wClip"><rect x="70" y="1120" width="940" height="352" rx="44"/></clipPath>'
                  '<clipPath id="aClip"><rect x="0" y="975" width="1080" height="505"/></clipPath>')
    anc = (f'<g id="anI"><line id="anCh" x1="540" y1="700" x2="540" y2="1150" stroke="#cfcfcf" stroke-width="8" stroke-dasharray="15 9"/>'
           f'<circle cx="540" cy="1170" r="20" fill="none" stroke="#fff" stroke-width="12"/>'
           f'<line x1="540" y1="1190" x2="540" y2="1330" stroke="#fff" stroke-width="15" stroke-linecap="round"/>'
           f'<line x1="492" y1="1222" x2="588" y2="1222" stroke="#fff" stroke-width="14" stroke-linecap="round"/>'
           f'<path d="M462,1286 Q540,1376 618,1286" stroke="#fff" stroke-width="15" fill="none" stroke-linecap="round"/>'
           f'<path d="M462,1286 L448,1252 L482,1270 Z" fill="#fff" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>'
           f'<path d="M618,1286 L632,1252 L598,1270 Z" fill="#fff" stroke="#fff" stroke-width="6" stroke-linejoin="round"/></g>')
    bub = "".join(f'<circle id="anB{k}" cx="{520 + (k * 13) % 44}" cy="1300" r="{6 + k % 3 * 3}" fill="none" stroke="#bfe3ff" stroke-width="3" style="opacity:0"/>' for k in range(8))
    crest = wave.split(" L1300")[0]
    V.svg.append(f'<g id="anG" style="opacity:0"><g clip-path="url(#wClip)"><path id="anW" d="{wave}" fill="url(#wGrad)"/>'
                 f'<path id="anWc" d="{crest}" fill="none" stroke="#7cc4ff" stroke-opacity=".7" stroke-width="5"/>'
                 f'<rect id="anDk" x="70" y="1120" width="940" height="360" fill="#000" style="opacity:0"/></g>'
                 f'<ellipse id="anR1" cx="540" cy="1160" rx="24" ry="7" fill="none" stroke="#fff" stroke-width="4" style="opacity:0"/>'
                 f'<ellipse id="anR2" cx="540" cy="1160" rx="24" ry="7" fill="none" stroke="#fff" stroke-width="3" style="opacity:0"/>'
                 f'<g clip-path="url(#aClip)"><g id="anM">{anc}</g></g>{bub}</g>')
    V.label("anL", "LIKE AN ANCHOR", t_a)
    V.fin("#anG", t_a, dy=20)
    V.to("#anW,#anWc", f"x:{-2 * wl}", t_a, dur=t_a_out - t_a + 0.6, sp="LIN")
    hit = T("anchor") + 0.16
    V.a(f'tl.fromTo("#anM",{{y:-420}},{{y:0,duration:{hit - (T("anchor") - 0.22):.3f},ease:DOWN}},{T("anchor") - 0.22:.3f});')
    V.a(f'tl.fromTo("#anI",{{rotation:16,svgOrigin:"540 975"}},{{rotation:0,svgOrigin:"540 975",duration:POP.dur,ease:POP.ease,immediateRender:false}},{hit:.3f});')
    for k, (rx, ry) in enumerate(((170, 32), (110, 22))):
        V.a(f'tl.fromTo("#anR{k + 1}",{{opacity:1,attr:{{rx:24,ry:7}}}},{{opacity:0,attr:{{rx:{rx},ry:{ry}}},duration:.7,ease:SOFT.ease,immediateRender:false}},{hit + k * 0.1:.3f});')
    V.set("#anCh", f'{{stroke:"{Y}"}}', T("tied")); V.set("#anCh", '{stroke:"#cfcfcf"}', T("leg") + 0.35)
    t_sk = T("drag", 2)
    V.to("#anM", "y:70", t_sk, dur=T("ocean") + 0.25 - t_sk, sp="LIN")
    V.to("#anDk", "opacity:.38", t_sk, dur=T("ocean") + 0.25 - t_sk, sp="LIN")
    for k in range(8):
        tb = t_sk + k * 0.15
        V.a(f'tl.fromTo("#anB{k}",{{opacity:0,y:0}},{{opacity:.9,y:-60,duration:.25,ease:"none",immediateRender:false}},{tb:.3f});')
        V.a(f'tl.to("#anB{k}",{{opacity:0,y:-150,duration:.5,ease:"none"}},{tb + 0.25:.3f});')
    V.xout("#anG", t_a_out); V.xout("#anL", t_a_out)
    V.s("whoosh", T("anchor") - 0.22); V.s("thud", hit); V.s("tick", T("tied")); V.s("whoosh_3", t_sk)

    # 4 + 16. FULL POTENTIAL bar with a lock at 100%: fills on "full potential", yanked down red on
    #    "brought down", three grey people appear on "the people they are around"; back at the end, stuck
    def potential(pid, t_in, t_out, start_pct=0.0, start_col=Y):
        tw = 860
        lock = ('<svg class="lock" viewBox="0 0 40 48" width="34" height="41"><path d="M10,22 V14 a10,10 0 0 1 20,0 V22" stroke="#fff" '
                'stroke-width="5" fill="none"/><rect x="4" y="21" width="32" height="25" rx="6" fill="#fff"/></svg>')
        V.html.append(f'<div class="pot" id="{pid}"><div class="potl">FULL POTENTIAL</div><div class="pot100">100%</div>'
                      f'<div class="pott"><div class="potf" id="{pid}f" style="width:{tw * start_pct:.0f}px;background:{start_col}"></div>'
                      f'<div class="potk" id="{pid}k">{lock}</div></div></div>')
        V.fin(f"#{pid}", t_in, dy=30)
        if t_out is not None: V.xout(f"#{pid}", t_out)
        return tw
    tw = potential("pt1", T("so", 1) + 0.02, T("people", 3) - 0.30)
    V.set("#pt1k", '{transformOrigin:"50% 50%"}', 0)
    V.a(f'tl.to("#pt1k",{{keyframes:[{{rotation:-14,duration:.06}},{{rotation:12,duration:.07}},{{rotation:-6,duration:.07}},{{rotation:0,duration:.09}}]}},{T("never", 1):.3f});')
    V.to("#pt1f", f"width:{tw * 0.7:.0f}", T("full", 1), sp="SOFT")
    V.to("#pt1f", f"width:{tw * 0.24:.0f}", T("brought"), sp="SNAP"); V.set("#pt1f", f'{{backgroundColor:"{R}"}}', T("brought"))
    V.svg.append('<g id="ptpG">' + person("ptp0", 200, 1330, 0.9) + person("ptp1", 290, 1330, 0.9) + person("ptp2", 380, 1330, 0.9) + "</g>")
    for k in range(3):
        V.pop(f"#ptp{k}", T("people", 2) + k * 0.12, s0=0.3, sp="SNAP")
    V.xout("#ptpG", T("people", 3) - 0.30)
    V.s("tick", T("never", 1)); V.s("whoosh_2", T("full", 1)); V.s("thud", T("brought"))
    for k in range(3): V.s(f"tick_{k + 2}", T("people", 2) + k * 0.12)

    # 5. "the product of the five people": YOU in the middle, five grey people fan out around it with spokes,
    #    the spokes glow yellow on "most time with"
    t_f, t_f_out = T("people", 3) - 0.12, T("so", 2) - 0.06
    ccx, ccy, rad = 540, 1330, 232
    angs = (-100, -50, 0, 50, 100)
    pts = [(ccx + rad * math.sin(math.radians(a)), ccy - rad * math.cos(math.radians(a))) for a in angs]
    spokes = "".join(f'<line id="fvS{k}" x1="{x:.0f}" y1="{y:.0f}" x2="{ccx}" y2="{ccy}" stroke="#fff" stroke-opacity=".35" stroke-width="5"/>'
                     for k, (x, y) in enumerate(pts))
    ppl = "".join(person(f"fvP{k}", x, y, 1.0) for k, (x, y) in enumerate(pts))
    V.svg.append(f'<g id="fvG" style="opacity:0">{spokes}{ppl}<g transform="translate({ccx},{ccy})"><g id="fvY" style="opacity:0">'
                 f'<circle r="70" fill="{Y}"/><text y="18" class="svb" text-anchor="middle" fill="{INK}" style="font-size:54px">YOU</text></g></g></g>')
    V.label("fvL", "YOU'RE THE PRODUCT OF", t_f, center=True)
    V.set("#fvG", "{opacity:1}", t_f)
    for k in range(5): V.draw(f"#fvS{k}", -1, dur=0.001, sp="LIN")
    V.pop("#fvY", T("you're", 1), s0=0.3, sp="POP")
    for k in range(5):
        tk = T("five") + k * 0.12
        V.pop(f"#fvP{k}", tk, s0=0.3, sp="SNAP")
        V.a(f'tl.fromTo("#fvS{k}",{{strokeDashoffset:CL("#fvS{k}")}},{{strokeDashoffset:0,duration:.25,ease:"none",immediateRender:false}},{tk:.3f});')
        V.s(f"tick_{1 + k % 4}" if k else "tick", tk)
    for k in range(5): V.set(f"#fvS{k}", f'{{stroke:"{Y}",strokeOpacity:.9}}', T("most", 1) + k * 0.04)
    V.xout("#fvG", t_f_out); V.xout("#fvL", t_f_out)
    V.s("pop", T("you're", 1))

    # 6. the no-hopers group chat: each line he quotes lands as a grey bubble, MUTED stamps on during the 95% line
    t_ch, t_ch_out = T("so", 2) + 0.08, T("or") - 0.04
    av = "".join(f'<div class="av" style="left:{26 + k * 30}px;background:{c}"></div>' for k, c in enumerate(("#48484a", "#636366", "#8e8e93")))
    hdr = (f'<div class="hdr">{av}<div class="hn" style="left:130px">No-hopers</div><div class="hs" style="left:130px">3 people</div>'
           f'<div class="mute" id="chM">MUTED</div></div>')
    msgs = [("Be realistic.", T("be", 1) - 0.06), ("You can't do that.", T("can't") - 0.10), ("Don't do this!", T("don't") - 0.04),
            ("Oh, you picked up your fitness hobby?", T("oh", 1) - 0.04), ("Didn't you fail last time?", T("didn't") - 0.04),
            ("Oh, those never worked.", T("oh", 2) - 0.04)]
    bubbles_panel(V, "cp", 150, 992, 780, 478, hdr, msgs, "#2C2C2E", t_ch, t_ch_out, font)
    V.pop("#chM", T("regain") - 0.05, s0=2.0, sp="STAMP", r0=-18, r1=-8)
    for k in range(len(msgs)): V.to(f"#cpb{k}", "opacity:.45", T("regain") + 0.05, sp="SOFT")
    V.s("whoosh_2", t_ch)
    for k, (_, t) in enumerate(msgs): V.s(f"pop_{1 + k % 4}" if k else "pop", t)
    V.s("thud", T("regain") - 0.05)

    # 7. the friend: one blue bubble "Oh, I'll do that with you." and a heart tapback
    t_fr, t_fr_out = T("or") + 0.10, T("partner") - 0.30
    fmsg = "Oh, I'll do that with you."
    hdr2 = (f'<div class="hdr"><div class="av" style="left:26px;background:#1c1c1e;border:4px solid {G}"></div>'
            f'<div class="hn" style="left:100px">Friend</div><div class="hs" style="left:100px;color:{G}">online</div></div>')
    fh = 250
    heart = (f'<svg viewBox="0 0 24 24" width="30" height="30"><path d="M12 21s-7.5-4.6-9.6-9.2C1 8.4 3.2 5 6.6 5c2 0 3.4 1.1 4.2 2.4h2.4'
             f'C14 6.1 15.4 5 17.4 5 20.8 5 23 8.4 21.6 11.8 19.5 16.4 12 21 12 21z" fill="{R}"/></svg>')
    bw_f = max(font.getlength(s) for s in wrap(font, fmsg, 622)) + 66
    area_h = fh - 104 - 12; h1 = len(wrap(font, fmsg, 780 - 2 * 26 - 2 * 28 - 50)) * 52 + 38
    tap = f'<div class="tap" id="fpH" style="left:{26 + bw_f - 34:.0f}px;top:{area_h - 16 - h1 - 26:.0f}px">{heart}</div>'
    bubbles_panel(V, "fp", 150, 992, 780, fh, hdr2, [(fmsg, T("oh", 3) - 0.04)], BL, t_fr, t_fr_out, font, extra=tap)
    V.pop("#fpH", T("with", 3) + 0.20, s0=0.2, sp="STAMP")
    V.s("pop", T("oh", 3) - 0.04); V.s("tick_2", T("with", 3) + 0.20)

    # 8. the journey: YOU (yellow) and a PARTNER (blue) travel a road together; on "fall off" YOU drops into a dip,
    #    the partner stops at the rim and a green SUPPORT arrow pulls YOU out, then both carry on
    t_j, t_j_out = T("partner") - 0.18, T("oh", 4) - 0.10
    yl = lambda x: 1384 - (x - 80) * (170 / 880) + 115 * math.exp(-((x - 700) / 58) ** 2)
    road = poly(rng(80, 960, 6), yl)
    V.defs.append('<clipPath id="jClip"><rect id="jCR" x="50" y="900" width="0" height="700"/></clipPath>')
    t1, t2, t3, t4 = T("partner"), T("support") - 0.05, T("fall", 1), T("off", 1)
    t5 = t_j_out - 0.05
    you_kf = [(t1, 150), (t2, 600), (t3, 700), (t3 + 0.22, 700), (t4 + 0.30, 775), (t5, 900)]
    par_kf = [(t1, 90), (t2, 540), (t3, 628), (t3 + 0.22, 628), (t4 + 0.30, 712), (t5, 840)]
    px, yx = 628, 700
    arrow = f"M{px + 14},{yl(px) - 30:.0f} Q{(px + yx) / 2:.0f},{yl(px) - 120:.0f} {yx - 6},{yl(yx) - 40:.0f}"
    hx, hy = yx - 6, yl(yx) - 40
    V.svg.append(f'<g id="jnG" style="opacity:0"><g clip-path="url(#jClip)">'
                 f'<path d="{road}" stroke="#fff" stroke-opacity=".07" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
                 f'<path d="{road}" stroke="#fff" stroke-opacity=".6" stroke-width="12" stroke-dasharray="1 24" stroke-linecap="round" fill="none"/></g>'
                 f'<path id="jnA" d="{arrow}" stroke="{G}" stroke-width="9" fill="none" stroke-linecap="round"/>'
                 f'<path id="jnAH" d="M{hx - 16},{hy - 14} L{hx + 6},{hy + 10} L{hx + 14},{hy - 18} Z" fill="{G}" stroke="{G}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>'
                 f'<circle id="jnP" cx="90" cy="{yl(90):.0f}" r="26" fill="{BL}"/><circle id="jnY" cx="150" cy="{yl(150):.0f}" r="26" fill="{Y}" filter="url(#glow)"/>'
                 f'<text id="jnPt" x="90" y="{yl(90) + 68:.0f}" class="svl" text-anchor="middle" fill="#8ec5ff" style="font-size:38px">PARTNER</text>'
                 f'<text id="jnYt" x="150" y="{yl(150) - 44:.0f}" class="svl" text-anchor="middle" fill="{Y}" style="font-size:38px">YOU</text>'
                 f'<text id="jnSt" x="830" y="{yl(830) - 74:.0f}" class="svb" text-anchor="middle" fill="{G}" style="font-size:58px;opacity:0">SUPPORT</text></g>')
    V.label("jnL", "WHAT YOU NEED", t_j)
    V.fin("#jnG", t_j, dy=20)
    V.to("#jCR", "attr:{width:960}", t_j, dur=0.9, sp="LIN")
    V.draw("#jnA", -1, dur=0.001, sp="LIN")
    V.follow("#jnY", sample(you_kf, yl)); V.follow("#jnP", sample(par_kf, yl))
    V.follow("#jnYt", sample(you_kf, yl), ax="x", ay="y", dy=-44); V.follow("#jnPt", sample(par_kf, yl), ax="x", ay="y", dy=68)
    V.a(f'tl.fromTo("#jnA",{{strokeDashoffset:CL("#jnA")}},{{strokeDashoffset:0,duration:.22,ease:"none",immediateRender:false}},{t3 + 0.02:.3f});')
    V.pop("#jnAH", t3 + 0.22, s0=0.2, sp="SNAP")
    V.pop("#jnSt", t3 + 0.04, s0=0.4, sp="POP")
    V.xout("#jnG", t_j_out); V.xout("#jnL", t_j_out)
    V.s("whoosh_3", t_j); V.s("thud_3", t3); V.s("pop_2", t3 + 0.04)

    # 9. "I knew that would happen": a grey bubble, slashed with a red X on "happen"
    t_k, t_k_out = T("oh", 4) + 0.04, T("you'll") - 0.02
    L = wrap(font, "I knew that would happen.", 700)
    bw = max(font.getlength(s) for s in L) + 56 + 10
    V.html.append(f'<div class="bub solo" id="knB" style="left:{(W - bw) / 2:.0f}px;top:1130px;width:{bw:.0f}px;height:90px;background:#2C2C2E">'
                  f'{esc(L[0])}</div><div class="av" id="knA" style="left:{(W - bw) / 2 - 70:.0f}px;top:1150px;background:#636366;position:absolute;opacity:0"></div>')
    V.pop("#knB", t_k, s0=0.6, sp="SNAP", origin="0% 100%"); V.pop("#knA", t_k, s0=0.4, sp="SNAP")
    x0, x1 = (W - bw) / 2 - 10, (W + bw) / 2 + 10
    V.html.append(f'<svg class="vz" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><path id="knX" d="M{x0:.0f},1112 L{x1:.0f},1238 M{x1:.0f},1112 L{x0:.0f},1238" '
                  f'stroke="{R}" stroke-width="15" stroke-linecap="round" fill="none"/></svg>')   # above the bubble
    V.draw("#knX", T("happen") - 0.15, dur=0.18, sp="LIN")
    for sel in ("#knB", "#knA", "#knX"): V.xout(sel, t_k_out)
    V.s("pop_3", t_k); V.s("thud_2", T("happen") - 0.15)

    # 10. the end: back to the potential bar, stuck at 24% red; the lock rattles on "never", the bar tries on
    #     "full potential" and falls back on "around those people"
    tw = potential("pt2", T("you'll") + 0.10, None, start_pct=0.24, start_col=R)
    V.set("#pt2k", '{transformOrigin:"50% 50%"}', 0)
    V.a(f'tl.to("#pt2k",{{keyframes:[{{rotation:-14,duration:.06}},{{rotation:12,duration:.07}},{{rotation:-6,duration:.07}},{{rotation:0,duration:.09}}]}},{T("never", 2):.3f});')
    V.to("#pt2f", f"width:{tw * 0.46:.0f}", T("full", 2), sp="SOFT"); V.set("#pt2f", f'{{backgroundColor:"{Y}"}}', T("full", 2))
    V.to("#pt2f", f"width:{tw * 0.2:.0f}", T("around", 2), sp="SNAP"); V.set("#pt2f", f'{{backgroundColor:"{R}"}}', T("around", 2))
    V.s("tick", T("never", 2)); V.s("whoosh", T("full", 2)); V.s("thud_3", T("around", 2))
    return f1_out, f1_out


# ------------------------------------------------------------------------------------------------ REACT (C4356)
PX, PY, PW, PH = 170, 700, 740, 840          # the card zone (receipts, before/afters, proof)
CX, CY, CW, CH = 224, 796, 632, 1124         # the clip box = lecture_render.PANEL_W x PANEL_H: OB's 1230/0719 reels' 9:16 box,
                                             # bottom-anchored, the whole clip (OB 10-21: not "a square", "a normal frame like my others")
RECEIPT = {65.5: "MOVED OUT", 82.45: "STARTED READING", 47.2: "TAKING CARE OF HIS HEALTH", 65.6: "NEW PLACE"}


def react_seq(V, T, D):
    rows = V.spec["rows"]
    f1_out = T("look") + 0.30
    end = lambda r: r["edit_out"] + r.get("gap", 0)
    def runs(key):
        out, cur = [], None
        for r in rows:
            v = r.get(key)
            if v is not None and cur and cur[0] == v and abs(cur[2] - r["edit_in"]) < 0.02: cur[2] = end(r)
            elif v is not None: cur = [v, r["edit_in"], end(r)]; out.append(cur)
            else: cur = None
        return out
    # 1. the clip panel (its video is a separate track, frame-exact with the edit; black where hidden)
    pruns = []
    for r in rows:
        if r.get("panel_in") is None: continue
        if pruns and abs(pruns[-1][1] - r["edit_in"]) < 0.02: pruns[-1][1] = end(r)
        else: pruns.append([r["edit_in"], end(r)])
    media = ('<img id="panelimg" src="" style="width:100%;height:100%;object-fit:cover;display:block"/>' if V.mode == "mock" else
             f'<video id="panelv" class="clip" src="../assets/{V.name}_clip.mp4" muted playsinline data-start="0" data-duration="{D:.3f}" '
             f'data-track-index="1" style="width:100%;height:100%;object-fit:cover;display:block"></video>' if V.mode == "render" else "")
    V.html.append(f'<div id="panel" class="rpanel" style="left:{CX}px;top:{CY}px;width:{CW}px;height:{CH}px">{media}</div>')
    for k, (a, b) in enumerate(pruns):
        if a < 0.05: V.set("#panel", "{opacity:1,scale:1}", 0)
        else: V.pop("#panel", a, s0=0.86, sp="SNAP"); V.s("whoosh", a)
        if b < D - 0.1: V.xout("#panel", b - 0.02, dur=0.14)
    # receipt tags on the panel (OB's own words for what each shot shows)
    for i, r in enumerate(rows):
        lab = RECEIPT.get(r.get("panel_in"))
        if not lab: continue
        V.html.append(f'<div class="rtag" id="rt{i}" style="left:{CX + 22}px;top:{CY + 22}px"><b>&#10003;</b>{esc(lab)}</div>')
        V.pop(f"#rt{i}", r["edit_in"] + 0.08, s0=0.4, sp="STAMP", r0=-8, r1=0)
        V.xout(f"#rt{i}", end(r) - 0.02, dur=0.1); V.s("tick", r["edit_in"] + 0.08)
    # 2. cards (same zone as the panel), one per run of rows
    for kind, a, b in runs("card"):
        cid = f"cd_{kind}"
        if kind == "tim_ba":
            V.html.append(f'<div class="rcard bare" id="{cid}" style="left:{PX}px;top:{PY + 70}px;width:{PW}px;height:640px">'
                          f'<div class="tile" id="tb0" style="left:0;top:0;width:360px;height:640px"><img src="../assets/react/t_before.jpg"/><i class="ba">BEFORE</i></div>'
                          f'<div class="tile" id="tb1" style="left:380px;top:0;width:360px;height:640px"><img src="../assets/react/t_after.jpg"/><i class="ba g">AFTER</i></div></div>')
            V.set(f"#{cid}", "{opacity:1}", a)
            V.pop("#tb0", a + 0.02, s0=0.8, sp="SNAP"); V.s("pop", a + 0.02)
            t1 = max(a + 0.5, T("lost", 1) - 0.1)
            V.a(f'tl.fromTo("#tb1",{{opacity:0,x:120}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{t1:.3f});'); V.s("whoosh_2", t1)
        elif kind == "client_m_ba":
            tw, th, g = 300, 358, 20
            x0 = PX + (PW - 2 * tw - g) // 2
            tiles = [("m_fb", 0, 0, "BEFORE", ""), ("m_fa", 1, 0, "AFTER", " g"), ("m_bb", 0, 1, "", ""), ("m_ba", 1, 1, "", " g")]
            h = "".join(f'<div class="tile" id="mt{n}" style="left:{c * (tw + g)}px;top:{rr * (th + g)}px;width:{tw}px;height:{th}px">'
                        f'<img src="../assets/react/{f}.jpg"/>' + (f'<i class="ba{cl}">{lab}</i>' if lab else "") + '</div>'
                        for n, (f, c, rr, lab, cl) in enumerate(tiles))
            V.html.append(f'<div class="rcard bare" id="{cid}" style="left:{x0}px;top:{PY + 64}px;width:{2 * tw + g}px;height:{2 * th + g}px">{h}</div>'
                          f'<div class="vlab" id="{cid}L" style="left:0;width:{W}px;text-align:center;top:{PY + 6}px;font-size:52px;color:{Y}">MY CLIENT CLIENT M</div>')
            V.set(f"#{cid}", "{opacity:1}", a); V.fin(f"#{cid}L", a, dy=20)
            t0 = max(a + 0.05, T("client") - 0.15); t1 = max(t0 + 0.6, T("rapid") - 0.15)
            for n, t in ((0, t0), (1, t0 + 0.35), (2, t1), (3, t1 + 0.35)):
                if n % 2 == 0: V.pop(f"#mt{n}", t, s0=0.85, sp="SNAP")
                else: V.a(f'tl.fromTo("#mt{n}",{{opacity:1,clipPath:"inset(0% 100% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:.42,ease:"none",immediateRender:false}},{t:.3f});')
                V.set(f"#mt{n}", "{opacity:0}", 0) if n % 2 else None
                V.s("pop" if n % 2 == 0 else "whoosh_3", t)
            V.xout(f"#{cid}L", b - 0.02, dur=0.12)
        elif kind in ("commission", "fitness_text"):
            meta = V.cards["commission" if kind == "commission" else "fitness"]
            img = "commission.png" if kind == "commission" else "fitness.png"
            ch = meta["h"] + 40; top = PY + 64; cx = (W - meta["w"] - 40) // 2
            hl = "".join(f'<div class="hl" id="{cid}h{j}" style="left:{20 + x0}px;top:{20 + y0}px;width:{x1 - x0}px;height:{y1 - y0}px"></div>'
                         for j, (x0, y0, x1, y1) in enumerate(meta["hl"]))
            V.html.append(f'<div class="rcard paper" id="{cid}" style="left:{cx}px;top:{top}px;width:{meta["w"] + 40}px;height:{ch}px">'
                          f'<img src="../assets/react/{img}" style="position:absolute;left:20px;top:20px;width:{meta["w"]}px;height:{meta["h"]}px"/>{hl}</div>'
                          f'<div class="vlab" id="{cid}L" style="left:0;width:{W}px;text-align:center;top:{PY + 6}px;font-size:52px;color:{Y}">CLIENT M&#8217;S TEXT</div>')
            V.pop(f"#{cid}", a + 0.02, s0=0.9, sp="SNAP"); V.fin(f"#{cid}L", a + 0.02, dy=20); V.s("pop_2", a + 0.02)
            t_hl = T("commission") - 0.05 if kind == "commission" else T("every", 1) - 0.25
            for j in range(len(meta["hl"])):
                V.a(f'tl.fromTo("#{cid}h{j}",{{scaleX:0,transformOrigin:"0% 50%"}},{{scaleX:1,duration:.26,ease:"none",immediateRender:false}},{t_hl + j * 0.28:.3f});')
                V.set(f"#{cid}h{j}", "{scaleX:0,transformOrigin:\"0% 50%\"}", 0)
                V.s("tick_2" if j else "tick", t_hl + j * 0.28)
            V.xout(f"#{cid}L", b - 0.02, dur=0.12)
            if kind == "commission":    # the commission card stays up under the three chips
                b = max(b, next((rb for kd, ra, rb in runs("card") if kd == "chips"), b))
        elif kind == "chips":   # one wrapper fades out: ENERGIZED lands 0.5 s before the exit, its spring still settling
            words = [("CONFIDENT", T("confident")), ("MOTIVATED", T("motivated")), ("ENERGIZED", T("energized"))]
            ctop = PY + 64 + V.cards["commission"]["h"] + 40 + 34
            V.html.append('<div id="chG" style="position:absolute;inset:0">' + "".join(
                f'<div class="rchip" id="ch{j}" style="left:{PX + j * 250}px;top:{ctop}px">{wd}</div>' for j, (wd, _) in enumerate(words)) + '</div>')
            for j, (wd, t) in enumerate(words):
                V.pop(f"#ch{j}", t - 0.05, s0=0.3, sp="STAMP", r0=-10, r1=0); V.s(f"tick_{j + 1}", t - 0.05)
            V.xout("#chG", b - 0.02, dur=0.12)
            continue
        V.xout(f"#{cid}", b - 0.02, dur=0.14)
    return f1_out, 0.0


# ------------------------------------------------------------------------------------------------ ADFX (ads, 2026-10-18)
# OB's "what if fat loss is easy" Meta ad look (T7 backup "fat loss is easy.mp4", $7,035 spend): 2-word white captions,
# hard cuts to a sky-blue card (#7EC4FA) with an icon tile and huge tight white words that land as he says them, and
# stacks of white outlined pills with an icon breaking out of the right edge. Everything comes from the EDL:
#   row["fx"] = {"card": {"icon", "start": "row"|<word>, "lines": [[text, s|m|l|xl], ...]}}
#             | {"pills": {"group", "on": "card"|"lower", "items": [{"text", "icon", "mark": "x"|"check", "at": <word>}]}}
#             | {"dm": {"at": <word>}}
AD_SIZES = {"s": 74, "m": 104, "l": 128, "xl": 170}


def _fit(text, size, room, em=0.56):
    return int(min(size, room / (em * max(1, len(text)))))


def adfx_seq(V, T, D):
    rows = V.spec["rows"]
    cap, times = caption_times(rows, Words(V.spec["viz"]["words"]))
    end = lambda r: r["edit_out"] + r.get("gap", 0)
    def row_words(i): return [(norm(w), t) for (ri, w), t in zip(cap, times) if ri == i]
    def at(i, word):
        for w, t in row_words(i):
            if w == norm(word): return t
        raise KeyError(f"row {i}: no '{word}' in '{rows[i]['caption']}'")
    V.nocap, V.css = [], AD_CSS
    fps = V.spec.get("fps", 30000 / 1001)
    # A cover that starts with its row must already be up on the row's first frame. The cut is frame-exact (round(t * fps)),
    # so that frame can sit up to half a frame before edit_in; a set at edit_in then shows one frame of him first (10-19 QC).
    first = lambda t: min(t, round(t * fps) / fps - 0.002)          # never later than asked (a lead keeps its full length)

    def span(i, c):
        """(t0, t1) of a graphic on row i: from the row's first frame or a spoken word (minus lead), to a spoken word
        (end, end_row rows later, plus end_pad) or that row's end plus until. OB 10-19: covers only while he reads."""
        t0 = (first(rows[i]["edit_in"]) if c.get("start", "row") == "row" else at(i, c["start"]) - 0.04) - c.get("lead", 0.0)
        j = i + c.get("end_row", 0)
        t1 = (at(j, c["end"]) + c.get("end_pad", -0.03)) if c.get("end") else end(rows[j]) + c.get("until", 0.0)
        return max(0.0, t0), t1

    # OB 10-19 "add animations": springs only (cards.py rule). Covers still cut in fully opaque, so no look-down shows.
    def push(sel, t0, t1, amt):                                    # slow constant-velocity push-in while a graphic holds
        V.a(f'tl.fromTo({J(sel)},{{scale:1}},{{scale:{1 + amt},duration:{max(0.1, t1 - t0):.3f},ease:"none",immediateRender:false}},{t0:.3f});')
    def settle(sel, t, s0=1.12, sp="SOFT"):                        # a photo lands: zoom down onto it
        V.a(f'tl.fromTo({J(sel)},{{scale:{s0}}},{{scale:1,duration:{sp}.dur,ease:{sp}.ease,immediateRender:false}},{t:.3f});')
    def slide_pop(sel, t, dx=140):                                 # a pill slides in from the right as it pops
        V._in(sel, t, "SNAP")
        V.a(f'tl.fromTo({J(sel)},{{opacity:0,x:{dx},scale:0.9}},{{opacity:1,x:0,scale:1,duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});')
    covers = []

    n = 0
    for i, r in enumerate(rows):                                   # blue cards (one or a list per row)
        cs = (r.get("fx") or {}).get("card")
        if not cs: continue
        for c in (cs if isinstance(cs, list) else [cs]):
            t0, t1 = span(i, c)
            cid = f"ac{n}"; n += 1
            rw = row_words(i); ptr = next((j for j, (_, t) in enumerate(rw) if t >= t0 - 0.1), len(rw)); last = t0; lines = []
            for li, (text, size) in enumerate(c["lines"]):
                spans = []
                for wk, wd in enumerate(text.split()):
                    hit = next((j for j in range(ptr, len(rw)) if rw[j][0] == norm(wd)), None)
                    if hit is not None: last = max(rw[hit][1], t0 + 0.02); ptr = hit + 1
                    wid = f"{cid}w{li}_{wk}"
                    if t0 <= 0.01 and last < 0.15:              # frame 1 of the ad: drawn, not set (a set at 0 s misses frame 1)
                        spans.append(f'<span class="aw" id="{wid}" style="opacity:1">{esc(wd)}</span>')
                    else:
                        spans.append(f'<span class="aw" id="{wid}">{esc(wd)}</span>')
                        V.pop(f"#{wid}", max(t0, last - 0.03), s0=0.55, sp="SNAP")   # each word springs in as he says it
                lines.append(f'<div class="adl" style="font-size:{_fit(text, AD_SIZES[size], 900)}px">{"".join(spans)}</div>')
            tile0 = ' style="opacity:1"' if t0 <= 0.01 else ""  # the opening card's tile is already up on frame 1
            tile = f'<div class="adtile" id="{cid}t"{tile0}><img src="../assets/ad/{c["icon"]}.png"/></div>' if c.get("icon") else ""
            on0 = ' style="opacity:1"' if t0 <= 0.01 else ""        # a set at exactly 0 s misses frame 1: start visible instead
            V.html.append(f'<div class="adcard" id="{cid}"{on0}>{tile}<div class="adtxt{"" if tile else " notile"}"><div class="blk">{"".join(lines)}</div></div></div>')
            if not on0: V.set(f"#{cid}", "{opacity:1}", t0)
            V.set(f"#{cid}", "{opacity:0}", t1)
            if tile and not tile0: V.pop(f"#{cid}t", t0 + 0.02, s0=0.55, sp="SNAP")
            push(f"#{cid} .blk", t0, t1, 0.05)
            V.s("whoosh", t0); V.nocap.append((t0, t1)); covers.append((t0, t1))
    groups = {}                                                    # pill stacks, grouped across rows
    for i, r in enumerate(rows):
        pl = (r.get("fx") or {}).get("pills")
        if pl:
            g = groups.setdefault(pl["group"], {"on": pl["on"], "rows": [], "items": [], "spec": pl, "i0": i})
            g["rows"].append(i); g["items"] += [(i, it) for it in pl["items"]]
    for gk, g in groups.items():
        r0, r1 = rows[g["rows"][0]], rows[g["rows"][-1]]; i0, sp0 = g["i0"], g["spec"]
        if sp0.get("windows"):                                      # the card comes back each time he reads, the list growing
            wins = [span(i0 + w.get("row", 0), w) for w in sp0["windows"]]
        elif sp0.get("end"):
            wins = [span(i0, sp0)]
        else:
            wins = [(first(r0["edit_in"]), end(r1))]
        t0, t1 = wins[0][0], wins[-1][1]; k = len(g["items"]); gid = f"ag_{gk}"
        on_card = g["on"] == "card"
        ph, gap, pw, left = (106, 26, 760, 160) if on_card else (100, 16, 820, 70)
        top0 = (900 - (k * ph + (k - 1) * gap) // 2) if on_card else 1010
        pills = []
        for j, (ri, it) in enumerate(g["items"]):
            t = max(at(ri, it["at"]) - 0.05, t0 + 0.02); pid = f"{gid}p{j}"
            mk = f'<img class="mk" src="../assets/ad/{it["mark"]}.png"/>' if it.get("mark") else ""
            pad_l = 100 if mk else 44
            fs = _fit(it["text"], 50 if on_card else 46, pw - pad_l - 130)
            pills.append(f'<div class="adpill" id="{pid}" style="left:{left}px;top:{top0 + j * (ph + gap)}px;width:{pw}px;height:{ph}px;'
                         f'padding:0 130px 0 {pad_l}px;font-size:{fs}px">{mk}<span>{esc(it["text"])}</span>'
                         f'<img class="ic" src="../assets/ad/{it["icon"]}.png"/></div>')
            slide_pop(f"#{pid}", t); V.s("pop", t)
        if on_card:
            V.html.append(f'<div class="adcard" id="{gid}">{"".join(pills)}</div>')
            for a, b in wins:
                V.set(f"#{gid}", "{opacity:1}", a); V.set(f"#{gid}", "{opacity:0}", b); V.s("whoosh", a)
                V.nocap.append((a, b)); covers.append((a, b))
        else:
            V.html.append(f'<div class="adgrp" id="{gid}">{"".join(pills)}</div>')
            V.xout(f"#{gid}", t1 - 0.14, dur=0.12)
            V.nocap.append((t0, t1))
    for i, r in enumerate(rows):                                   # full-screen client proof (OB 10-18: "show proof, best visual ones")
        pf = (r.get("fx") or {}).get("proof")
        if not pf: continue
        t0 = first(r["edit_in"]) - pf.get("lead", 0.0); t1 = end(r) + pf.get("until", 0.0); pid = f"apf{i}"
        on0 = ' style="opacity:1"' if t0 <= 0.01 else ""
        V.html.append(f'<div class="adproof" id="{pid}"{on0}><img src="../assets/ad/{pf["img"]}"/></div>')
        if not on0: V.set(f"#{pid}", "{opacity:1}", t0)
        V.set(f"#{pid}", "{opacity:0}", t1); V.s("whoosh", t0)
        settle(f"#{pid} > img", t0); covers.append((t0, t1))
    # timed cutaways inside a line: photo frames and client text cards
    for i, r in enumerate(rows):
        for ci, cu in enumerate((r.get("fx") or {}).get("cuts", [])):
            last_row = rows[i + cu.get("through", 0)]
            t0 = r["edit_in"] + cu["from"] if cu.get("from", 0.0) else first(r["edit_in"])
            if cu.get("end"): t1 = at(i + cu.get("end_row", 0), cu["end"]) + cu.get("end_pad", -0.03)
            elif cu.get("to", "end") == "end": t1 = end(last_row) + cu.get("until", 0.0)
            else: t1 = r["edit_in"] + cu["to"]
            cid = f"acut{i}_{ci}"
            if "img" in cu:
                V.html.append(f'<div class="adproof" id="{cid}"><img src="../assets/ad/{cu["img"]}"/></div>')
                settle(f"#{cid} > img", t0); push(f"#{cid}", t0, t1, 0.03)
            else:                                                  # his own message, highlight sweeping the line that matters
                w, h = cu.get("w", 960), cu.get("h", 380)
                top = 960 - (h + 40) // 2
                hl = "".join(f'<div class="adhl" id="{cid}h{k}" style="left:{20 + x0}px;top:{20 + y0}px;width:{x1 - x0}px;height:{y1 - y0}px"></div>'
                             for k, (x0, y0, x1, y1) in enumerate(cu.get("hl", [])))
                V.html.append(f'<div class="adproof" id="{cid}"><div class="adtlab" id="{cid}l" style="top:{top - 110}px">{esc(cu.get("label", ""))}</div>'
                              f'<div class="adpaper" id="{cid}p" style="top:{top}px;width:{w + 40}px;height:{h + 40}px;left:{(1080 - w - 40) // 2}px">'
                              f'<img src="../assets/ad/{cu["text"]}" style="width:{w}px;height:{h}px"/>{hl}</div></div>')
                V._in(f"#{cid}p", t0, "SNAP")                      # the message slides up into place, its label pops
                V.a(f'tl.fromTo("#{cid}p",{{y:150,opacity:0}},{{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease,immediateRender:false}},{t0:.3f});')
                V.pop(f"#{cid}l", t0 + 0.05, s0=0.6, sp="SNAP")
                for k in range(len(cu.get("hl", []))):
                    V.set(f"#{cid}h{k}", "{scaleX:0,transformOrigin:\"0% 50%\"}", 0)
                    V.a(f'tl.fromTo("#{cid}h{k}",{{scaleX:0,transformOrigin:"0% 50%"}},{{scaleX:1,duration:.26,ease:"none",immediateRender:false}},{t0 + cu.get("hl_at", 0.25) + k * 0.28:.3f});')
                    V.s("tick_2" if k else "tick", t0 + cu.get("hl_at", 0.25) + k * 0.28)
                V.nocap.append((t0, t1))
            V.set(f"#{cid}", "{opacity:1}", t0); V.set(f"#{cid}", "{opacity:0}", t1); V.s("whoosh", t0); covers.append((t0, t1))
    for i, r in enumerate(rows):                                   # the DM pill stays to the end
        dm = (r.get("fx") or {}).get("dm")
        if not dm: continue
        t = at(i, dm["at"]) - 0.05
        V.html.append('<div class="adpill dm" id="addm" style="left:200px;top:1190px;width:680px;height:112px;padding:0 120px 0 44px;font-size:52px">'
                      f'<span>Send me a DM</span><img class="ic" src="../assets/ad/{dm.get("icon", "chat")}.png"/></div>')
        V.pop("#addm", t, s0=0.82, sp="SNAP"); V.s("pop", t)
    V.covers = sorted(covers)                                      # for stills and checks: when a full-screen graphic is up
    # each time a cover lifts and he is back, the shot lands with a soft zoom (the A-roll is #aroll in a render, #bg in a mock)
    for a, b in sorted(covers):
        if b >= D - 0.05 or any(a2 <= b + 0.02 < b2 for a2, b2 in covers): continue
        V.a(f'tl.fromTo("#aroll, #bg",{{scale:1.07,transformOrigin:"50% 38%"}},{{scale:1,duration:SOFT.dur,ease:SOFT.ease,immediateRender:false}},{b:.3f});')
    return 0.0, D + 60.0          # no frame-1 hook block, no scrim


AD_CSS = """
.adcard { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; background: #7EC4FA; opacity: 0; }
.adgrp { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }
.adproof { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; opacity: 0; background: #7EC4FA; }
.adproof > img { width: 1080px; height: 1920px; display: block; }
.adtlab { position: absolute; left: 0; width: 1080px; text-align: center; font-family: 'AvH'; font-size: 66px; letter-spacing: -1px; color: #fff; }
.adpaper { position: absolute; background: #fff; border: 3px solid #111; border-radius: 26px; box-sizing: content-box; overflow: hidden; }
.adpaper img { position: absolute; left: 20px; top: 20px; display: block; }
.adhl { position: absolute; background: #F7DC3A; opacity: .85; mix-blend-mode: multiply; border-radius: 6px; }
.adtile { position: absolute; left: 385px; top: 470px; width: 310px; height: 310px; background: #fff; border: 3px solid #111;
          border-radius: 66px; opacity: 0; display: flex; align-items: center; justify-content: center; }
.adtile img { width: 200px; height: 200px; object-fit: contain; }
.adtxt { position: absolute; left: 0; width: 1080px; top: 850px; display: flex; justify-content: center; }
.adtxt.notile { top: 0; height: 1920px; align-items: center; }
.adtxt .blk { display: inline-block; text-align: left; }
.adl { font-family: 'AvH'; color: #fff; letter-spacing: -0.045em; line-height: 0.98; white-space: nowrap; }
.aw { display: inline-block; opacity: 0; margin-right: 0.2em; }
.adpill { position: absolute; box-sizing: border-box; background: #fff; border: 2.5px solid #111; border-radius: 24px; display: flex;
          align-items: center; justify-content: center; font-family: 'AvH'; color: #111; letter-spacing: -0.03em; opacity: 0;
          white-space: nowrap; box-shadow: 0 10px 24px rgba(0,0,0,.18); }
.adpill .mk { position: absolute; left: 24px; top: 50%; width: 56px; height: 56px; margin-top: -28px; object-fit: contain; }
.adpill .ic { position: absolute; right: -28px; top: -24px; width: 148px; height: 148px; object-fit: contain; }
.adpill.dm .ic { right: -34px; top: -30px; }
"""


SEQ = {"RESET": reset_seq, "LOSERS": losers_seq, "REACT": react_seq, "ADFX": adfx_seq}

VIZ_CSS = f"""
.vz {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; overflow: visible; }}
.scrim {{ position: absolute; left: -80px; width: 1240px; top: 900px; height: 700px; opacity: 0;
          background: radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,0,0,.62) 0%, rgba(0,0,0,.42) 55%, rgba(0,0,0,0) 100%); }}
.vlab {{ position: absolute; font-family: 'DINC'; letter-spacing: 2px; line-height: 1; opacity: 0; text-shadow: 0 3px 14px rgba(0,0,0,.7); }}
.svl {{ font-family: 'DINC'; font-size: 34px; letter-spacing: 1.5px; }}
.svd {{ font-family: 'DINC'; font-size: 36px; letter-spacing: 1px; fill: {GR}; }}
.svb {{ font-family: 'DINC'; font-size: 72px; letter-spacing: 2px; }}
.svp {{ font-family: 'DINC'; font-size: 60px; letter-spacing: 1px; }}
.chip {{ position: absolute; font-family: 'DINC'; letter-spacing: 1.5px; padding: 10px 18px 3px; border-radius: 12px; opacity: 0;
         white-space: nowrap; box-shadow: 0 10px 26px rgba(0,0,0,.45); }}
.big {{ position: absolute; left: 0; width: {W}px; text-align: center; font-family: 'DINC'; font-size: 160px; line-height: 1; color: #fff;
        opacity: 0; text-shadow: 0 6px 24px rgba(0,0,0,.6); }}
.cal {{ position: absolute; width: 300px; height: 330px; opacity: 0; }}
.cal .face {{ position: absolute; inset: 0; background: #fff; border-radius: 28px; overflow: hidden; backface-visibility: hidden;
              box-shadow: 0 24px 60px rgba(0,0,0,.55); }}
.cal .calh {{ height: 84px; color: #fff; font-family: 'DINC'; font-size: 48px; letter-spacing: 3px; display: flex; align-items: center;
              justify-content: center; padding-top: 6px; }}
.cal .tro {{ position: absolute; left: 55px; top: 104px; }}
.cal .calt {{ position: absolute; left: 0; right: 0; bottom: 26px; text-align: center; font-family: 'DINC'; font-size: 40px; letter-spacing: 2px; color: #111; }}
.badge {{ position: absolute; right: -34px; top: -30px; background: {Y}; color: {INK}; font-family: 'DINC'; font-size: 40px; letter-spacing: 1px;
          padding: 12px 18px 5px; border-radius: 16px; opacity: 0; box-shadow: 0 10px 24px rgba(0,0,0,.45); }}
.stamp2 {{ position: absolute; left: 540px; top: 990px; border: 8px solid {R}; color: {R}; background: rgba(10,10,10,.75); border-radius: 14px;
           font-family: 'DINC'; font-size: 84px; letter-spacing: 4px; padding: 10px 26px 0; opacity: 0; white-space: nowrap; }}
.pot {{ position: absolute; left: 110px; width: 860px; top: 1040px; height: 260px; opacity: 0; }}
.potl {{ position: absolute; left: 0; top: 0; font-family: 'DINC'; font-size: 52px; letter-spacing: 2px; color: #fff; text-shadow: 0 3px 14px rgba(0,0,0,.7); }}
.pot100 {{ position: absolute; right: 0; top: 12px; font-family: 'DINC'; font-size: 40px; letter-spacing: 1px; color: {GR}; }}
.pott {{ position: absolute; left: 0; top: 84px; width: 860px; height: 84px; border-radius: 42px; background: #2a2a2d;
         box-shadow: inset 0 0 0 2px rgba(255,255,255,.12), 0 14px 36px rgba(0,0,0,.45); overflow: hidden; }}
.potf {{ position: absolute; left: 0; top: 0; height: 84px; border-radius: 42px; }}
.potk {{ position: absolute; right: 26px; top: 21px; width: 34px; height: 41px; }}
.panel {{ position: absolute; background: #0e0e10; border-radius: 40px; box-shadow: 0 0 0 2px rgba(255,255,255,.07), 0 26px 70px rgba(0,0,0,.6);
          overflow: hidden; opacity: 0; }}
.panel .hdr {{ position: absolute; left: 0; right: 0; top: 0; height: 100px; border-bottom: 2px solid rgba(255,255,255,.08); }}
.av {{ position: absolute; top: 24px; width: 54px; height: 54px; border-radius: 50%; box-shadow: 0 0 0 4px #0e0e10; }}
.hn {{ position: absolute; top: 16px; font-family: 'AvDB'; font-size: 36px; color: #fff; }}
.hs {{ position: absolute; top: 58px; font-family: 'AvDB'; font-size: 26px; color: {GR}; }}
.mute {{ position: absolute; right: 30px; top: 18px; border: 6px solid {R}; color: {R}; border-radius: 12px; font-family: 'DINC'; font-size: 52px;
         letter-spacing: 3px; padding: 6px 16px 0; opacity: 0; background: #0e0e10; }}
.area {{ position: absolute; left: 0; right: 0; overflow: hidden; }}
.bub {{ position: absolute; color: #fff; font-family: 'AvDB'; font-size: 42px; line-height: 52px; padding: 19px 28px; border-radius: 34px;
        white-space: nowrap; opacity: 0; }}
.bub.solo {{ box-shadow: 0 18px 44px rgba(0,0,0,.5); }}
.tap {{ position: absolute; width: 58px; height: 58px; border-radius: 50%; background: #2C2C2E; border: 4px solid #0e0e10; display: flex;
        align-items: center; justify-content: center; opacity: 0; }}
.rpanel {{ position: absolute; border-radius: 0; overflow: hidden; opacity: 0; background: #000; box-shadow: none; }}   /* plain box, like his 1230/0719 reels */
.rtag {{ position: absolute; display: flex; gap: 10px; align-items: center; background: rgba(12,12,12,.86); color: #fff; font-family: 'DINC';
         font-size: 40px; letter-spacing: 1.5px; padding: 10px 18px 4px; border-radius: 12px; opacity: 0; white-space: nowrap; }}
.rtag b {{ color: {G}; font-family: 'AvH'; font-size: 36px; margin-top: -6px; }}
.rcard {{ position: absolute; opacity: 0; }}
.rcard.paper {{ background: #fff; border-radius: 30px; box-shadow: 0 30px 80px rgba(0,0,0,.6); overflow: hidden; }}
.rcard .tile {{ position: absolute; border-radius: 22px; overflow: hidden; box-shadow: 0 0 0 3px rgba(255,255,255,.9), 0 20px 50px rgba(0,0,0,.55); }}
.rcard .tile img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.ba {{ position: absolute; left: 14px; top: 14px; font-style: normal; background: rgba(12,12,12,.85); color: #fff; font-family: 'DINC';
       font-size: 34px; letter-spacing: 1.5px; padding: 8px 14px 2px; border-radius: 10px; }}
.ba.g {{ background: {G}; color: #08240f; }}
.hl {{ position: absolute; background: {Y}; opacity: .9; border-radius: 6px; mix-blend-mode: multiply; }}
.rchip {{ position: absolute; width: 238px; text-align: center; background: {Y}; color: {INK}; font-family: 'DINC'; font-size: 46px;
          letter-spacing: 1.5px; padding: 14px 0 6px; border-radius: 14px; opacity: 0; box-shadow: 0 16px 36px rgba(0,0,0,.5); }}
"""

JS_HELPERS = r"""
const UP = p => 2 * p - p * p, DOWN = p => p * p;             // ballistic: rising decelerates, falling accelerates
function CL(sel) { const el = document.querySelector(sel); return el.getTotalLength(); }
function DRAW(sel, t, dur, ease) {
  document.querySelectorAll(sel).forEach(function (el) {
    const L = el.getTotalLength(); el.style.strokeDasharray = L + ' ' + L;
    if (t < 0) { el.style.strokeDashoffset = L; return; }       // register hidden; a later fromTo draws it
    tl.fromTo(el, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: dur, ease: ease }, t);
  });
}
"""


def caption_pages_dtw(rows, words, f1_out, per=3):
    """`per`-word pages per row (3 as lecture_cards; 2 for the ad look), each word lit at its own Whisper time."""
    cap, times = caption_times(rows, words)
    pages = []
    for i, r in enumerate(rows):
        idx = [k for k, (ri, _) in enumerate(cap) if ri == i]
        for s in range(0, len(idx), per):
            ks = idx[s:s + per]
            end = times[idx[s + per]] if s + per < len(idx) else r["edit_out"]
            pages.append({"words": [cap[k][1] for k in ks], "times": [times[k] for k in ks], "t0": times[ks[0]], "t1": end})
    return pages


def caption_times(rows, words):
    """Each row's caption words lined up with Whisper's words: cap = [(row, word)], times[k]; misses interpolated in the row."""
    cap = [(i, w) for i, r in enumerate(rows) for w in r["caption"].split()]
    a, b = [norm(w) for _, w in cap], [x["n"] for x in words.w]
    times = [None] * len(cap)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size): times[blk.a + k] = words.w[blk.b + k]["t"]
    for i, r in enumerate(rows):                         # fill misses inside each row, clamp to the row
        idx = [k for k, (ri, _) in enumerate(cap) if ri == i]
        lo, hi = r["edit_in"] + 0.02, r["edit_out"] - 0.05
        known = [(k, times[k]) for k in idx if times[k] is not None and lo - 0.3 <= times[k] <= hi + 0.3]
        for k in idx:
            if times[k] is not None and any(k == kk for kk, _ in known): continue
            prv = [(kk, t) for kk, t in known if kk < k]; nxt = [(kk, t) for kk, t in known if kk > k]
            p = prv[-1] if prv else (idx[0] - 1, lo); n = nxt[0] if nxt else (idx[-1] + 1, hi)
            times[k] = p[1] + (n[1] - p[1]) * (k - p[0]) / max(1, n[0] - p[0])
        prev = lo
        for k in idx:
            times[k] = min(max(times[k], prev, lo), hi); prev = times[k]
    return cap, times


def assemble(spec, name, mode, proj):
    words = Words(spec["viz"]["words"]); T = words.t
    rows, D = spec["rows"], spec["duration"]
    V = prep(Viz(proj), spec, name, mode, proj)
    f1_out, scrim_in = SEQ[spec["viz"].get("seq", name)](V, T, D)
    for m in V.bad: print("STUCK-EXIT " + m, file=sys.stderr)
    if V.bad and mode == "render": sys.exit("lecture_viz: an exit would be undone by a running spring (see STUCK-EXIT); not rendering")
    js = [f'tl.to("#scrim",{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{scrim_in:.3f});'] + V.js
    caps = []
    card_spans = [(r["edit_in"], r["edit_out"] + r.get("gap", 0)) for r in rows if r.get("card")] + V.nocap
    for p_i, p in enumerate(caption_pages_dtw(rows, words, f1_out, spec["viz"].get("cap_words", 3))):
        if any(a - 0.05 <= p["t0"] < b for a, b in card_spans): continue      # a card owns the zone: no captions over it
        cut = [a for a, b in card_spans if p["t0"] < a < p["t1"]]               # a card that lands mid-page ends the page
        if cut: p = dict(p, t1=min(cut))
        if p["t0"] < f1_out:
            if p["t1"] - f1_out < 0.3: continue
            p = dict(p, t0=f1_out + 0.02)
        ws = "".join(f'<span class="w" id="w{p_i}_{k}">{esc(w)}</span>' for k, w in enumerate(p["words"]))
        caps.append(f'<div class="cap" id="p{p_i}">{ws}</div>')
        js.append(f'tl.set("#p{p_i}",{{opacity:1}},{p["t0"]:.3f}); tl.set("#p{p_i}",{{opacity:0}},{p["t1"]:.3f});')
        for k, t in enumerate(p["times"]):
            t_off = p["times"][k + 1] if k + 1 < len(p["times"]) else p["t1"]
            js.append(f'tl.set("#w{p_i}_{k}",{{className:"w on"}},{max(t, p["t0"]):.3f}); tl.set("#w{p_i}_{k}",{{className:"w"}},{t_off:.3f});')
    f1 = ""
    if spec.get("frame1"):                               # the ads have no frame-1 hook block: captions from frame 1
        lines = "<br>".join(f"<span>{esc(l)}</span>" for l in spec["frame1"].split("\n"))
        f1_style = f' style="top:{spec["frame1_top"]}px"' if spec.get("frame1_top") else ""
        f1 = f'<div class="f1" id="f1"{f1_style}><div class="hook">{lines}</div></div>'
        js.append(f'tl.set("#f1",{{opacity:1}},0); tl.to("#f1",{{opacity:0,y:-30,duration:SOFT.dur,ease:SOFT.ease}},{f1_out:.3f});')
    if mode == "mock": bg = '<img id="bg" class="media" src=""/>'
    elif mode == "overlay": bg = ""
    else: bg = (f'<video id="aroll" class="media clip" src="../assets/{name}_cut.mp4" muted playsinline data-start="0" '
                f'data-duration="{D:.3f}" data-track-index="0"></video>')
    body_bg = "transparent" if mode == "overlay" else "#000"
    extra_css = (f" .cap {{ top: {spec['viz']['cap_top']}px; }}" if spec["viz"].get("cap_top") else "") + \
                (" .rpanel { background: transparent !important; }" if mode == "overlay" else "") + \
                (" .cap { text-transform: none; font-size: 78px; letter-spacing: -2px; left: 50px; right: 50px;"
                 " text-shadow: 0 4px 18px rgba(0,0,0,.55), 0 2px 4px rgba(0,0,0,.65); } .cap .on { color: #fff; } .cap .w { margin: 0 9px; }"
                 if spec["viz"].get("cap_live") is False else "") + V.css
    defs = ('<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' + "".join(V.defs))
    return f"""<!doctype html>
<html lang="en" data-resolution="portrait"><head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script><style>{BASE_CSS}{VIZ_CSS}
html, body {{ background: {body_bg}; }} #root {{ background: {body_bg}; }}{extra_css}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="{W}" data-height="{H}">
<div>{bg}</div>
<div class="scrim" id="scrim"></div>
<svg class="vz" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{defs}</defs>{''.join(V.svg)}</svg>
{''.join(V.html)}
{''.join(caps)}
{f1}
</div>
<script>
window.__timelines = window.__timelines || {{}};
{SPRINGS}
const tl = gsap.timeline({{ paused: true }});
{JS_HELPERS}
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""


def prep(V, spec, name, mode, proj):
    V.spec, V.name, V.mode = spec, name, mode
    V.nocap, V.css = [], ""                              # caption-free spans and extra CSS a sequence may add
    cj = f"{proj}/assets/react/cards.json"
    V.cards = json.load(open(cj)) if os.path.exists(cj) else {}
    return V


def sfx_events(spec, proj):
    V = prep(Viz(proj), spec, spec.get("title", ""), "render", proj); T = Words(spec["viz"]["words"]).t
    f1_out, _ = SEQ[spec["viz"]["seq"]](V, T, spec["duration"])
    hook = [("whoosh", round(f1_out - 0.06, 3))] if spec.get("frame1") else []
    return hook + sorted(V.sfx, key=lambda e: e[1])


def main():
    edl, proj, name = sys.argv[1], sys.argv[2], sys.argv[3]
    mode = "mock" if "--mock" in sys.argv else "overlay" if "--overlay" in sys.argv else "render"
    spec = json.load(open(edl))
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    out = f"{proj}/compositions/{name}{'' if mode == 'render' else '.' + mode}.html"
    open(out, "w").write(assemble(spec, name, mode, proj))
    print(out)


if __name__ == "__main__":
    main()
