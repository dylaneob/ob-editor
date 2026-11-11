#!/usr/bin/env python3
"""HyperFrames compositions for reaction edits: Doctor Mike grammar on OB's card system.

  python3 react_cards.py EVENTS.json PROJECT_DIR [--mock]

Every composition draws over its BASE (the already-composed edit frame for that moment: OB full
frame, or the split screen with OB on the left and the clip on the right). --mock uses a still of the base so Puppeteer
can screenshot the exact layout; the render uses the base clip as a muted <video>.
e["on"] is "split" or "ob": labels, pops, terms and verdict stamps all sit on OB's side, never on the clip.
Canvas 3840x2160; split geometry lives in react_geom.py (OB panel x 0-2505, clip panel x 2565-3780).
"""
import html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from react_cards_base import CSS, esc   # fonts, topo, PiP styles (snapshot of cards.py)
from react_geom import OB_X, CLIP_X, CLIP_W

W, H, Y, R, G = 3840, 2160, "#F7DC3A", "#E53935", "#2E7D32"
# Brand look (OB 10-28, ~/ob-editor/brand/brand.json "boxes": false): Big Shoulders Display, no boxes, cards or bubbles
# behind words, a soft shadow, OB yellow on the one word that matters. Every reaction from C4407 (11-03) on.
BR = json.load(open(os.path.expanduser("~/ob-editor/brand/brand.json")))
BRAND = not BR.get("boxes", True)
if BRAND: Y = BR["accent"]
SH = f"0 {round(3840 * BR['shadow']['y_of_width'])}px {round(3840 * BR['shadow']['blur_of_width'])}px rgba(0,0,0,{BR['shadow']['alpha']})"
SPRINGS = r'''
function spring(k, c, m = 1, v0 = 0) {
  const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m)); let f, T;
  if (z < 1) { const wd = w0 * Math.sqrt(1 - z * z);
    f = t => 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0 - v0) / wd) * Math.sin(wd * t)); T = Math.log(1000) / (z * w0); }
  else { f = t => 1 - Math.exp(-w0 * t) * (1 + (w0 - v0) * t); T = 1.6 * Math.log(1000) / w0; }
  return { dur: +T.toFixed(3), ease: p => (p >= 1 ? 1 : f(p * T)) };
}
const POP = spring(320, 17), SNAP = spring(260, 22), SOFT = spring(170, 26), SLAM = spring(520, 20), SLIDE = spring(210, 27);
'''
EXTRA_CSS = f"""
.stamp {{ position:absolute; padding:30px 70px; border:16px solid currentColor; border-radius:28px; font-family:'DINC';
          font-size:300px; line-height:1; letter-spacing:6px; text-transform:uppercase; background:rgba(10,10,10,.35); }}
.stampsub {{ position:absolute; font-family:'AvDB'; font-size:64px; color:#fff; text-shadow:0 4px 16px rgba(0,0,0,.85); }}
.pop {{ position:absolute; font-family:'DINC'; color:#fff; line-height:1; text-transform:uppercase;
        -webkit-text-stroke:14px #000; paint-order:stroke fill; text-shadow:0 14px 30px rgba(0,0,0,.6); white-space:nowrap; }}
.term {{ position:absolute; background:#fff; color:#111; border-radius:22px; padding:26px 46px 30px; box-shadow:0 18px 50px rgba(0,0,0,.45); }}
.term .t {{ font-family:'DINC'; font-size:120px; line-height:1; }}
.term .s {{ font-family:'AvDB'; font-size:56px; color:#444; margin-top:12px; }}
.panelClip {{ position:absolute; left:{CLIP_X}px; top:0; width:{CLIP_W}px; height:{H}px; overflow:hidden; background:#000; }}
.ovw {{ position:absolute; opacity:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.ovw img {{ width:100%; object-fit:contain; display:block; }}
.ovl {{ font-size:92px; line-height:1; color:#fff; text-shadow:0 4px 22px rgba(0,0,0,.85); margin-top:26px; white-space:nowrap; }}
.card {{ margin-top:26px; background:#fff; border-radius:28px; padding:54px 62px 46px; box-shadow:0 30px 80px rgba(0,0,0,.5); }}
.hl {{ background-color:rgba(247,220,58,0); border-radius:8px; padding:0 6px; -webkit-box-decoration-break:clone; box-decoration-break:clone; }}
"""
if BRAND:
    EXTRA_CSS += f"""
@font-face {{ font-family:'BSD'; src:url('../assets/fonts/BigShouldersDisplay.ttf'); font-weight:100 900; }}
.din {{ font-family:'BSD'; font-weight:900; text-transform:uppercase; letter-spacing:.005em; }}
.avb {{ font-family:'BSD'; font-weight:800; }}
.av {{ font-family:'BSD'; font-weight:600; }}
#root {{ text-shadow:{SH}; }}
.stamp {{ border:none; background:none; padding:0; font-family:'BSD'; font-weight:900; letter-spacing:.005em; text-shadow:{SH}; }}
.stampsub {{ font-family:'BSD'; font-weight:800; text-transform:uppercase; letter-spacing:.02em; text-shadow:{SH}; }}
.pop {{ font-family:'BSD'; font-weight:900; -webkit-text-stroke:0; letter-spacing:.005em; text-shadow:{SH}; }}
.term {{ background:none; box-shadow:none; border-radius:0; padding:0; color:#fff; }}
.term .t {{ font-family:'BSD'; font-weight:900; text-transform:uppercase; text-shadow:{SH}; }}
.term .s {{ font-family:'BSD'; font-weight:800; color:#fff; text-shadow:{SH}; }}
.hl {{ background:none !important; color:{Y}; padding:0; }}
svg text {{ font-family:'BSD' !important; font-weight:700; }}
"""


def wrap(text, n):
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])


def base(ev, mock, cls="layer"):
    if mock:
        return f'<div class="{cls}"><img class="media" src="../assets/stills/{ev["id"]}.jpg"/></div>'
    return (f'<div class="{cls}"><video id="base" class="media clip" src="../assets/base/{ev["id"]}.mp4" muted playsinline '
            f'data-start="0" data-duration="{ev["dur"]:.3f}" data-track-index="0"></video></div>')


def pip(ev, mock):   # OB from the base (base is OB full frame for card events)
    return f'<div class="pip">{base(ev, mock)}</div>'


# Side layout (study cards, charts, end card), OB's rule from C4352: never a boxed PiP. The panel covers
# x 1640-3840 and OB's own frame slides left, uncropped and unscaled, so he stays on the side he looks from.
SIDE_X = 1640


def side_shift(ev):   # put his face near the middle of the 0-1640 strip (the middle of everywhere it goes in the event, when measured)
    c = (ev["face_x0"] + ev["face_x1"]) / 2 if "face_x0" in ev else ev.get("face_cx", 1840)
    return int(max(-1250, min(-450, 820 - c)))


def slots(ev):
    """Image slots on OB's own frame, left and right of his face (react_prep measures face_cx per event)."""
    fx = int(ev.get("face_cx", 1840)); M, G = 60, 480   # G clears his cap brim, not just his face
    L0, L1, R0, R1 = M, fx - G, fx + G, W - M
    if "face_x0" in ev: L1, R0 = int(ev["face_x0"]) - 190, int(ev["face_x1"]) + 190   # his face over the whole event (react_prep)
    lw, rw, lay = L1 - L0, R1 - R0, ev["layout"]
    if lay in ("flash", "pair"):      # one tall slot each side
        a, b = min(1300, lw), min(1300, rw)
        return [(L0 + (lw - a) // 2, 200, a, 1700), (R0 + (rw - b) // 2, 200, b, 1700)]
    if lay == "pairw":                # one wide slot each side: screenshots, app charts
        a, b = min(1400, lw), min(1400, rw)
        return [(L0 + (lw - a) // 2, 530, a, 1100), (R0 + (rw - b) // 2, 530, b, 1100)]
    if lay == "quad":                 # two portrait slots each side
        g = 40; a, b = min(640, (lw - g) // 2), min(640, (rw - g) // 2)
        lx, rx = L0 + (lw - 2 * a - g) // 2, R0 + (rw - 2 * b - g) // 2
        return [(lx, 480, a, 1180), (lx + a + g, 480, a, 1180), (rx, 480, b, 1180), (rx + b + g, 480, b, 1180)]
    if lay == "one":                  # one big slot on the roomier side
        if rw >= lw: b = min(1500, rw); return [(R0 + (rw - b) // 2, 170, b, 1760)]
        a = min(1500, lw); return [(L0 + (lw - a) // 2, 170, a, 1760)]
    raise ValueError(lay)


def study_html(s):
    if BRAND:   # no card: the paper's lines as text on the panel, OB yellow on the finding's key phrase
        f = esc(s["finding"])
        if s.get("hl"): f = f.replace(esc(s["hl"]), f'<span class="hl">{esc(s["hl"])}</span>', 1)
        fs = 92 if len(s["finding"]) <= 110 else 78
        return (f'<div id="sc"><div class="avb" style="font-size:48px;color:{Y};letter-spacing:.12em;text-transform:uppercase">'
                f'{esc(s.get("tag", "Study"))} · {esc(s["journal"])} · {esc(s["year"])}</div>'
                f'<div class="avb" style="font-size:62px;line-height:1.14;margin-top:30px">{esc(s["title"])}</div>'
                f'<div class="av" style="font-size:44px;color:#d6d6d6;margin-top:18px">{esc(s["authors"])}</div>'
                f'<div style="height:6px;width:170px;background:{Y};margin:48px 0 42px"></div>'
                f'<div class="din" style="font-size:{fs}px;line-height:1.1">{f}</div>'
                f'<div class="av" style="font-size:40px;color:#cfcfcf;margin-top:40px">{esc(s.get("src") or ("PubMed " + s["pmid"] + " · doi.org/" + s["doi"]))}</div></div>')
    f = esc(s["finding"])
    if s.get("hl"): f = f.replace(esc(s["hl"]), f'<span class="hl">{esc(s["hl"])}</span>', 1)
    fs = 74 if len(s["finding"]) <= 110 else 62
    return (f'<div id="sc"><div style="display:flex;align-items:center;gap:26px">'
            f'<span class="avb" style="background:{Y};color:#111;font-size:44px;padding:8px 20px;border-radius:10px;letter-spacing:2px">{esc(s.get("tag", "STUDY"))}</span>'
            f'<span class="avb" style="font-size:52px;color:#fff">{esc(s["journal"])} · {esc(s["year"])}</span></div>'
            f'<div class="card"><div class="avb" style="font-size:56px;line-height:1.22;color:#111">{esc(s["title"])}</div>'
            f'<div class="av" style="font-size:40px;color:#6a6a6a;margin-top:20px">{esc(s["authors"])}</div>'
            f'<div style="height:3px;background:#e7e7e7;margin:36px 0 32px"></div>'
            f'<div class="avb" style="font-size:{fs}px;line-height:1.28;color:#111">{f}</div>'
            f'<div class="av" style="font-size:36px;color:#8c8c8c;margin-top:32px">{esc(s.get("src") or ("PubMed " + s["pmid"] + " · doi.org/" + s["doi"]))}</div></div></div>')


def chart_html(c, full):
    """Animated chart from primary data. full=True: standalone card (title + source); else it sits under a study card."""
    k, CW = c["kind"], 1980
    CH = c.get("h", 1150 if full else 660)
    head = ""
    if full:
        head = (f'<div class="din" style="font-size:112px;line-height:1.04">{esc(c["title"])}</div>'
                f'<div class="av" style="font-size:44px;color:#a8a8a8;margin:18px 0 44px">{esc(c.get("source", ""))}</div>')
    elif c.get("title"):
        head = f'<div class="avb" style="font-size:46px;color:#d8d8d8;margin-bottom:20px">{esc(c["title"])}</div>'
    if k == "hbars":
        mx = max(v for _, v, _ in c["rows"]) or 1; rh = CH // len(c["rows"]); body = ""
        for i, (lbl, v, txt) in enumerate(c["rows"]):
            col = Y if i == c.get("hi", 0) else "#efefef"
            body += (f'<div style="display:flex;align-items:center;height:{rh}px">'
                     f'<div class="avb" style="width:560px;font-size:46px;color:#e8e8e8;line-height:1.15">{esc(lbl)}</div>'
                     f'<div class="hb" style="width:{max(10, int(1060 * v / mx))}px;height:76px;border-radius:38px;background:{col};transform-origin:left center"></div>'
                     f'<div class="din hv" style="font-size:86px;margin-left:30px;white-space:nowrap;color:{col}">{esc(txt)}</div></div>')
    elif k == "line":
        xs = c["x"]; x0, x1, y0, y1 = 150, CW - 280, 50, CH - 100
        X = lambda i: x0 + i * (x1 - x0) / (len(xs) - 1)
        Yv = lambda v: y0 + (c["ymax"] - v) / (c["ymax"] - c["ymin"]) * (y1 - y0)
        svg = "".join(f'<line x1="{x0}" y1="{Yv(g):.0f}" x2="{x1}" y2="{Yv(g):.0f}" stroke="#2e2e2e" stroke-width="3"/>'
                      f'<text x="{x0 - 22}" y="{Yv(g) + 14:.0f}" text-anchor="end" font-family="AvM" font-size="38" fill="#9a9a9a">{g}{esc(c.get("unit", ""))}</text>'
                      for g in c["yticks"])
        svg += "".join(f'<text x="{X(i):.0f}" y="{y1 + 66}" text-anchor="middle" font-family="AvM" font-size="40" fill="#a8a8a8">{esc(l)}</text>' for i, l in enumerate(xs))
        for j, sr in enumerate(c["series"]):
            pts = " ".join(f"{X(i):.1f},{Yv(v):.1f}" for i, v in enumerate(sr["y"]))
            svg += (f'<polyline id="ln{j}" points="{pts}" fill="none" stroke="{sr["color"]}" stroke-width="{14 if j == 0 else 10}" stroke-linejoin="round" '
                    f'stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>')
            svg += "".join(f'<circle class="ld" cx="{X(i):.1f}" cy="{Yv(v):.1f}" r="{16 if j == 0 else 12}" fill="{sr["color"]}"/>' for i, v in enumerate(sr["y"]))
            for i, lab in sr.get("labels", {}).items():
                i = int(i); dy = sr.get("dy", 80)
                anchor, dx = ("start", 34) if i == len(xs) - 1 else ("middle", 0)
                svg += (f'<text class="lt" x="{X(i) + dx:.0f}" y="{Yv(sr["y"][i]) + (30 if dx else dy):.0f}" text-anchor="{anchor}" font-family="DINC" '
                        f'font-size="{92 if j == 0 else 66}" fill="{sr["color"]}">{esc(lab)}</text>')
        legend = "".join(f'<span style="display:inline-flex;align-items:center;gap:14px;margin-right:50px"><span style="width:50px;height:12px;border-radius:6px;background:{sr["color"]}"></span>{esc(sr["name"])}</span>'
                         for sr in c["series"])
        body = f'<div class="avb" style="font-size:44px;color:#ddd;margin-bottom:6px">{legend}</div><svg width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">{svg}</svg>'
    elif k == "vbars":   # positive bars grow up from the zero line, negative ones hang down (C4354: one shared scale, zero placed by the data)
        bars = c["bars"]; n = len(bars); bw = 360; top = 130
        pmx = max([v for _, v, _ in bars if v > 0] or [0]); nmx = max([-v for _, v, _ in bars if v < 0] or [0]); span = (pmx + nmx) or 1
        bh = CH - (470 if nmx else 360)   # room under a hanging bar for its value label
        zero = int(top + bh * pmx / span); gap = (CW - 120 - n * bw) // max(1, n - 1); body = f'<div style="position:relative;width:{CW}px;height:{CH}px">'
        body += f'<div style="position:absolute;left:60px;top:{zero}px;width:{CW - 120}px;height:4px;background:#5a5a5a"></div>'
        if c.get("zero"): body += f'<div class="av" style="position:absolute;left:60px;top:{zero + (14 if pmx else -66)}px;font-size:40px;color:#a8a8a8">{esc(c["zero"])}</div>'
        for i, (lbl, v, txt) in enumerate(bars):
            x = 60 + i * (bw + gap); hpx = max(10, int(bh * abs(v) / span)); col = Y if i == c.get("hi", 0) else "#efefef"
            if v >= 0:
                body += (f'<div class="vb" style="position:absolute;left:{x}px;top:{zero - hpx}px;width:{bw}px;height:{hpx}px;background:{col};border-radius:26px 26px 0 0;transform-origin:50% 100%"></div>'
                         f'<div class="din vv" style="position:absolute;left:{x - 40}px;width:{bw + 80}px;text-align:center;top:{zero - hpx - 104}px;font-size:84px;color:{col}">{esc(txt)}</div>')
            else:
                body += (f'<div class="vb" style="position:absolute;left:{x}px;top:{zero + 4}px;width:{bw}px;height:{hpx}px;background:{col};border-radius:0 0 26px 26px;transform-origin:50% 0%"></div>'
                         f'<div class="din vv" style="position:absolute;left:{x - 40}px;width:{bw + 80}px;text-align:center;top:{zero + 18 + hpx}px;font-size:84px;color:{col}">{esc(txt)}</div>')
            body += f'<div class="avb" style="position:absolute;left:{x - 30}px;width:{bw + 60}px;text-align:center;top:{CH - 120}px;font-size:42px;line-height:1.15;color:#e2e2e2">{esc(lbl)}</div>'
        body += "</div>"
    elif k == "stack":   # one 100% bar; narrow segments get their label on a second row
        segs = c["segs"]; tot = sum(p for _, p, _ in segs); bw = CW - 40; x = 0; parts = labs = ""
        for i, (lbl, p, col) in enumerate(segs):
            w = int(bw * p / tot); row2 = w < 520
            parts += f'<div class="sg" style="position:absolute;left:{x}px;top:0;width:{w - 10}px;height:250px;background:{col};border-radius:26px;transform-origin:left center"></div>'
            lx = min(x, bw - 520) if row2 else x
            labs += (f'<div class="sl" style="position:absolute;left:{lx}px;top:{560 if row2 else 290}px;width:520px">'
                     f'<div class="din" style="font-size:150px;line-height:1;color:{col}">{p}%</div>'
                     f'<div class="avb" style="font-size:52px;color:#e8e8e8;margin-top:10px">{esc(lbl)}</div></div>')
            x += w
        foot = f'<div class="av sl" style="position:absolute;left:0;top:{CH - 110}px;width:{bw}px;font-size:40px;line-height:1.3;color:#a8a8a8">{esc(c.get("note", ""))}</div>'
        body = f'<div style="position:relative;width:{bw}px;height:{CH}px">{parts}{labs}{foot}</div>'
    elif k == "scatter":
        P = c["points"]; x0, x1, y0, y1 = 170, CW - 50, 30, CH - 330
        X = lambda v: x0 + (v - c["xmin"]) / (c["xmax"] - c["xmin"]) * (x1 - x0)
        Yv = lambda v: y1 - (v - c["ymin"]) / (c["ymax"] - c["ymin"]) * (y1 - y0)
        svg = "".join(f'<line x1="{x0}" y1="{Yv(g):.0f}" x2="{x1}" y2="{Yv(g):.0f}" stroke="#2e2e2e" stroke-width="3"/>'
                      f'<text x="{x0 - 22}" y="{Yv(g) + 14:.0f}" text-anchor="end" font-family="AvM" font-size="38" fill="#9a9a9a">{g}%</text>' for g in c["yticks"])
        svg += "".join(f'<text x="{X(g):.0f}" y="{y1 + 60}" text-anchor="middle" font-family="AvM" font-size="38" fill="#9a9a9a">{g}%</text>' for g in c["xticks"])
        svg += f'<text x="{(x0 + x1) / 2:.0f}" y="{y1 + 124}" text-anchor="middle" font-family="AvDB" font-size="42" fill="#d8d8d8">{esc(c["xlabel"])}</text>'
        svg += f'<text x="{x0 - 120}" y="{(y0 + y1) / 2:.0f}" text-anchor="middle" font-family="AvDB" font-size="42" fill="#d8d8d8" transform="rotate(-90 {x0 - 120} {(y0 + y1) / 2:.0f})">{esc(c["ylabel"])}</text>'
        a, b = c["trend"]
        svg += (f'<line id="tr" x1="{X(c["xmin"]):.0f}" y1="{Yv(a + b * c["xmin"]):.0f}" x2="{X(c["xmax"]):.0f}" y2="{Yv(a + b * c["xmax"]):.0f}" stroke="{Y}" '
                f'stroke-width="9" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>')
        hi = {s: col for col, ss in c["highlight"] for s in ss}
        for s, (xv, yv) in sorted(P.items(), key=lambda kv: kv[1][0]):
            col = hi.get(s, "#d9d9d9")
            svg += f'<circle class="sd" cx="{X(xv):.1f}" cy="{Yv(yv):.1f}" r="{20 if s in hi else 15}" fill="{col}" fill-opacity="{1 if s in hi else .78}"/>'
            if s in hi:
                svg += f'<text class="hl2" x="{X(xv):.0f}" y="{Yv(yv) - 34:.0f}" text-anchor="middle" font-family="DINC" font-size="58" fill="{col}">{esc(s)}</text>'
        stats = "".join(f'<div class="ss" style="flex:1"><div class="din" style="font-size:118px;line-height:1;color:{col}">{esc(v)}</div>'
                        f'<div class="avb" style="font-size:46px;color:#e2e2e2;margin-top:10px">{esc(l)}</div></div>' for v, l, col in c["stats"])
        body = (f'<svg width="{CW}" height="{CH - 190}" viewBox="0 0 {CW} {CH - 190}">{svg}</svg>'
                f'<div style="display:flex;gap:60px;margin-top:10px;padding-left:{x0}px">{stats}</div>')
    else:
        raise ValueError(k)
    return f'<div id="ch">{head}{body}</div>'


def chart_js(c, t0):
    k = c["kind"]
    if k == "hbars":
        return [f'tl.fromTo(".hb",{{scaleX:0}},{{scaleX:1,duration:SNAP.dur,ease:SNAP.ease,stagger:.22}},{t0:.2f});',
                f'tl.fromTo(".hv",{{opacity:0}},{{opacity:1,duration:.3,ease:"none",stagger:.22}},{t0 + .35:.2f});']
    if k == "line":
        return ([f'tl.fromTo("#ln{j}",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:1.5,ease:SOFT.ease}},{t0 + .3 * j:.2f});' for j in range(len(c["series"]))]
                + [f'tl.fromTo(".ld",{{opacity:0}},{{opacity:1,duration:.25,ease:"none",stagger:.12}},{t0:.2f});',
                   f'tl.fromTo(".lt",{{opacity:0}},{{opacity:1,duration:.35,ease:"none",stagger:.15}},{t0 + 1.1:.2f});'])
    if k == "vbars":
        return [f'tl.fromTo(".vb",{{scaleY:0}},{{scaleY:1,duration:SNAP.dur,ease:SNAP.ease,stagger:.35}},{t0:.2f});',
                f'tl.fromTo(".vv",{{opacity:0}},{{opacity:1,duration:.3,ease:"none",stagger:.35}},{t0 + .45:.2f});']
    if k == "stack":
        return [f'tl.fromTo(".sg",{{scaleX:0}},{{scaleX:1,duration:SNAP.dur,ease:SNAP.ease,stagger:.45}},{t0:.2f});',
                f'tl.fromTo(".sl",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease,stagger:.4}},{t0 + .25:.2f});']
    if k == "scatter":
        return [f'tl.fromTo(".sd",{{opacity:0,scale:.3}},{{opacity:1,scale:1,duration:.4,ease:POP.ease,stagger:.025,transformOrigin:"50% 50%"}},{t0:.2f});',
                f'tl.fromTo("#tr",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:1.0,ease:SOFT.ease}},{t0 + 1.5:.2f});',
                f'tl.fromTo(".hl2",{{opacity:0}},{{opacity:1,duration:.35,ease:"none",stagger:.12}},{t0 + 1.7:.2f});',
                f'tl.fromTo(".ss",{{opacity:0,y:24}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease,stagger:.3}},{t0 + 2.3:.2f});']
    raise ValueError(k)


def side(ev, mock, inner, js, D, back=True):
    """OB slides left (uncropped), the panel slides in from the right; both return at the end."""
    sh = side_shift(ev)
    b = (f'<div class="bg"></div><div id="vid" class="layer">{base(ev, mock)}</div>'
         f'<div id="panel" style="position:absolute;left:{SIDE_X}px;top:0;width:{W - SIDE_X}px;height:{H}px;overflow:hidden">'
         f'<div class="bg"></div>{inner}</div>')
    js += [f'tl.fromTo("#vid",{{x:0}},{{x:{sh},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
           f'tl.fromTo("#panel",{{x:{W - SIDE_X}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);']
    if back and D > 1.6:
        js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.55:.3f});',
               f'tl.to("#panel",{{x:{W - SIDE_X},duration:SLIDE.dur,ease:SLIDE.ease}},{D - 0.55:.3f});']
    return b


def _zone(ev, want=None):
    """the free side beside his face on a full-frame shot: (side, x0, x1); want 'L'/'R' forces a side. With react_prep's face
    span the zone clears everywhere his face goes during the event, 230 px past his face box (his ears and cap brim stick out
    about 80): one still at 1 s let him lean into the tags (C4407 3:59 and 8:51, 11-03)."""
    if "face_x0" in ev: L, R = (120, int(ev["face_x0"]) - 230), (int(ev["face_x1"]) + 230, W - 120)
    else:
        fx = int(ev.get("face_cx", 1840)); G = 520
        L, R = (120, fx - G), (fx + G, W - 120)
    side = want or ("R" if R[1] - R[0] >= L[1] - L[0] else "L")
    return (side,) + (L if side == "L" else R)


ICO = None
def _icon(name):
    global ICO
    if ICO is None:
        import re as _re
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards.py")).read()
        m = _re.search(r"ICONS = \{(.*?)\n\}", src, _re.S)
        ICO = dict(_re.findall(r'"([a-z_]+)": \'(.*?)\',', m.group(1))) if m else {}
    return REV2_ICONS.get(name or "") or ICO.get(name or "", ICO.get("check", ""))


# ---- C4415 rev 2 (OB 11-04 notes on v3: "flash the videos at the start", "when I say scrolling ... show it on the screen",
#      "make up the comments when I say the comments", "bring up studies", "overlay way more graphics while I'm talking, no need to
#      take the whole screen"). All of these sit on his own frame beside his face (_zone), never full screen.
REV2_ICONS = {
    "egg": '<path d="M12 3c-3.6 0-6.5 5.2-6.5 9.6a6.5 6.5 0 0 0 13 0C18.5 8.2 15.6 3 12 3z"/><circle cx="12" cy="13.6" r="2.6"/>',
    "pizza": '<path d="M12 21L3.8 6.6a15 15 0 0 1 16.4 0z"/><path d="M5.3 9.1a12 12 0 0 1 13.4 0"/><circle cx="12" cy="11.6" r="1.1"/><circle cx="9.7" cy="15" r=".9"/><circle cx="14.1" cy="15.6" r=".9"/>',
    "berries": '<circle cx="8" cy="15.2" r="3.6"/><circle cx="15.8" cy="15.6" r="3.6"/><circle cx="12" cy="9.3" r="3.6"/><path d="M12 5.7c0-1.5.9-2.6 2.5-2.9"/>',
    "apple": '<path d="M12 7.6c-1.8-1.3-6.6-1.5-6.6 4.2 0 4.3 2.8 8.4 4.7 8.4 1 0 1.2-.6 1.9-.6s.9.6 1.9.6c1.9 0 4.7-4.1 4.7-8.4 0-5.7-4.8-5.5-6.6-4.2z"/><path d="M12 7.6c0-2 .6-3.4 2-4.6"/>',
    "kiwi": '<circle cx="12" cy="12" r="8.6"/><circle cx="12" cy="12" r="3"/><path d="M12 5.4v1.2M12 17.4v1.2M5.4 12h1.2M17.4 12h1.2M7.3 7.3l.8.8M15.9 15.9l.8.8M7.3 16.7l.8-.8M15.9 8.1l.8-.8"/>',
    "mushroom": '<path d="M3.4 12.2a8.6 7 0 0 1 17.2 0z"/><path d="M9.4 12.2v5.6a2.6 2.6 0 0 0 5.2 0v-5.6"/><circle cx="9" cy="8.6" r=".9"/><circle cx="14.4" cy="7.6" r=".9"/>',
    "bean": '<path d="M7.6 4.4c3-1.5 6 .4 6.5 3s2.2 2.6 3.8 3.4c2.3 1.3 2 5.6-1.3 7.6-3.8 2.3-9.5 1-11.5-3.2C3 11.4 4.6 5.9 7.6 4.4z"/>',
    "pill": '<path d="M10.6 4.6a4.2 4.2 0 0 1 6 6l-6 6a4.2 4.2 0 0 1-6-6z"/><path d="M7.6 7.6l6 6"/>',
    "wheat": '<path d="M12 21V7.5"/><path d="M12 7.6c-1.8-1-2.4-2.9-1.8-4.8 1.9.7 2.5 2.8 1.8 4.8zM12 7.6c1.8-1 2.4-2.9 1.8-4.8-1.9.7-2.5 2.8-1.8 4.8zM12 12.4c-2.2-.6-3.4-2.4-3.2-4.5 2.1.2 3.3 2.1 3.2 4.5zM12 12.4c2.2-.6 3.4-2.4 3.2-4.5-2.1.2-3.3 2.1-3.2 4.5zM12 17c-2.2-.6-3.4-2.4-3.2-4.5 2.1.2 3.3 2.1 3.2 4.5zM12 17c2.2-.6 3.4-2.4 3.2-4.5-2.1.2-3.3 2.1-3.2 4.5z"/>',
    "brain": '<path d="M9.2 4.4a3 3 0 0 0-3 3 3 3 0 0 0-2.1 5.1 3 3 0 0 0 2.5 5.4A3 3 0 0 0 12 19V5.6a3 3 0 0 0-2.8-1.2zM14.8 4.4a3 3 0 0 1 3 3 3 3 0 0 1 2.1 5.1 3 3 0 0 1-2.5 5.4A3 3 0 0 1 12 19"/>',
    "bone": '<path d="M8.3 10.2l5.5 5.5a2.4 2.4 0 1 0 3.3 3.3 2.4 2.4 0 1 0 3.3-3.3 2.4 2.4 0 1 0-3.3-3.3L11.6 6.9A2.4 2.4 0 1 0 8.3 3.6 2.4 2.4 0 1 0 5 6.9a2.4 2.4 0 1 0 3.3 3.3z"/>',
    "muscle": '<path d="M5 19.5c1.2-5.8 3.6-9.4 6.6-11.4l1.2-3c.8-1 2.8-.7 3 .9l-.9 3.1c2.3.1 3.9 1.5 4.6 3.6 1.2 3.6-1.5 6.8-5.6 6.8z"/><path d="M11 13.5c1.5-1.2 3.4-1.5 5-.8"/>',
    "pen": '<path d="M14.6 3.4l6 6-9.8 9.8-6-6z"/><path d="M4.8 13.2l-2 7.9 7.9-2M16.6 1.4l6 6M9.2 11l3.8 3.8"/>',
    "can": '<path d="M7.5 5.5h9l-.6 1.6v11.8l.6 1.6h-9l.6-1.6V7.1z"/><path d="M8.1 9.5h7.8M10.5 3.5h3"/>',
    "vest": '<path d="M8.5 3L5 6.5V20h6v-6h2v6h6V6.5L15.5 3l-2 4h-3z"/>',
    "chocolate": '<rect x="5.5" y="3" width="13" height="18" rx="1.6"/><path d="M5.5 9h13M5.5 15h13M12 3v18"/>',
    "broccoli": '<path d="M9.8 21h4.4l-.9-6.6h-2.6z"/><circle cx="8" cy="11.2" r="3.3"/><circle cx="16" cy="11.2" r="3.3"/><circle cx="12" cy="7.8" r="3.7"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    "camera": '<rect x="2.8" y="7" width="13" height="10" rx="2"/><path d="M15.8 10.5l5.4-3.2v9.4l-5.4-3.2"/>',
    "bookmark": '<path d="M6.5 3.5h11V21L12 17.2 6.5 21z"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>',
    "share": '<path d="M21 3L10 14M21 3l-6.5 18-4.5-7-7-4.5z"/>',
    "comment": '<path d="M20.5 11.6a8.4 8.4 0 0 1-12.4 7.4L3.5 20.5l1.6-4.4A8.4 8.4 0 1 1 20.5 11.6z"/>',
    "heart2": '<path d="M12 20.3S3.5 15.3 3.5 9.2A4.6 4.6 0 0 1 12 6.8a4.6 4.6 0 0 1 8.5 2.4c0 6.1-8.5 11.1-8.5 11.1z"/>',
}
REV2_CSS = """
.paper, .paper * { text-shadow:none !important; }
.hlm { background-image:linear-gradient(transparent 50%, rgba(255,212,0,.92) 50%, rgba(255,212,0,.92) 94%, transparent 94%);
       background-repeat:no-repeat; background-size:0% 100%; -webkit-box-decoration-break:clone; box-decoration-break:clone; }
.cmt, .cmt * { font-family:'Avenir Next','Helvetica Neue',sans-serif; }
"""
AVN = "font-family:'Avenir Next','Helvetica Neue',sans-serif"


def _svg(name, size, stroke="#fff", sw=2.0, idd="", fill="none", extra=""):
    i = f' id="{idd}"' if idd else ""
    return (f'<svg{i} viewBox="0 0 24 24" width="{size}" height="{size}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round" style="flex:none;{extra}">{_icon(name)}</svg>')


def rev2(ev, mock, D):
    t = ev["type"]; js = []
    if t == "feed":   # a phone beside him scrolling through what-I-eat-in-a-day videos (his opening lines), then landing on one
        items, tt = ev["items"], ev["items_t"]; side, x0, x1 = _zone(ev, ev.get("side"))
        PW, PH, BZ = 860, 1529, 30; bw, bh = PW + 2 * BZ, PH + 2 * BZ
        sc = round(min(1.0, (x1 - x0 - 40) / bw, (H - 240) / bh), 3); cx = (x0 + x1) // 2
        cells = []
        for i, it in enumerate(items):
            t_in = tt[i]; t_out = tt[i + 1] if i + 1 < len(items) else D
            if mock: med = f'<img src="../assets/feed/{it["file"]}.jpg" style="width:100%;height:100%;object-fit:cover"/>'
            else:
                st = max(0.0, t_in - 0.5); du = min(D, t_out + 0.5) - st
                med = (f'<video id="fv{i}" class="clip" src="../assets/feed/{it["file"]}.mp4" muted playsinline data-start="{st:.3f}" '
                       f'data-duration="{du:.3f}" data-track-index="{2 + i}" style="width:100%;height:100%;object-fit:cover"></video>')
            cells.append(f'<div style="position:relative;width:{PW}px;height:{PH}px;overflow:hidden;background:#111">{med}'
                         f'<div style="position:absolute;left:44px;bottom:120px;{AVN};font-weight:700;font-size:44px;color:#fff;'
                         f'text-shadow:0 2px 12px rgba(0,0,0,.75)">{esc(it["handle"])}</div></div>')
        rail = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:8px">{_svg(n, 92, idd=("fbk" if n == "bookmark" else ""), extra="filter:drop-shadow(0 2px 8px rgba(0,0,0,.6))")}</div>'
                       for n in ("heart2", "comment", "bookmark", "share"))
        b = (f'<div id="ph" style="position:absolute;left:{cx - bw // 2}px;top:{(H - bh) // 2}px;width:{bw}px;height:{bh}px;border-radius:118px;'
             f'background:#0c0c0c;box-shadow:0 50px 120px rgba(0,0,0,.6),inset 0 0 0 3px #2a2a2a;transform:scale({sc})">'
             f'<div style="position:absolute;left:{BZ}px;top:{BZ}px;width:{PW}px;height:{PH}px;border-radius:90px;overflow:hidden;background:#000">'
             f'<div id="fc" style="position:absolute;left:0;top:0;width:{PW}px">{"".join(cells)}</div>'
             f'<div style="position:absolute;right:30px;bottom:330px;display:flex;flex-direction:column;gap:54px">{rail}</div>'
             f'<div style="position:absolute;left:50%;top:22px;width:250px;height:58px;margin-left:-125px;border-radius:30px;background:#0c0c0c"></div></div></div>')
        if ev.get("foot"):
            b += (f'<div id="fd" style="position:absolute;left:140px;top:1963px;{AVN};font-weight:600;font-size:40px;letter-spacing:.05em;'
                  f'color:rgba(255,255,255,.92);white-space:nowrap">{esc(ev["foot"])}</div>')
            js += ['tl.fromTo("#fd",{opacity:0,y:24},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0.05);',
                   f'tl.to("#fd",{{opacity:0,duration:.3,ease:"none"}},{min(D - .4, ev.get("foot_dur", 5.0)):.3f});']
        js += [f'tl.fromTo("#ph",{{y:1300,rotation:9,scale:{sc}}},{{y:0,rotation:0,scale:{sc},duration:SLIDE.dur,ease:SLIDE.ease}},0);']
        for i in range(1, len(items)):
            js.append(f'tl.to("#fc",{{y:{-i * PH},duration:.42,ease:"power3.inOut"}},{max(0.05, tt[i] - 0.42):.3f});')
        if ev.get("save_t") is not None:
            st_ = ev["save_t"]
            js += [f'tl.set("#fbk path",{{attr:{{fill:"{Y}"}},stroke:"{Y}"}},{st_:.3f});',
                   f'tl.fromTo("#fbk",{{scale:1}},{{scale:1.5,duration:.16,ease:"power2.out",yoyo:true,repeat:1,transformOrigin:"50% 50%"}},{st_:.3f});']
        if ev.get("zoom_t") is not None:   # "you want to look just like them": a slow push on her
            js.append(f'tl.to("#ph",{{scale:{sc * 1.06:.3f},duration:{max(.5, D - .6 - ev["zoom_t"]):.3f},ease:"none"}},{ev["zoom_t"]:.3f});')
        if D > 1.2: js.append(f'tl.to("#ph",{{y:1400,rotation:-10,duration:.5,ease:"power2.in"}},{D - .52:.3f});')
    elif t == "lineup":   # the six diets flash in on his words (her own opening video + who she is), then all six in a grid
        items, tt = ev["items"], ev["items_t"]; side, x0, x1 = _zone(ev, ev.get("side")); zw = x1 - x0
        TH = 1360; TW = int(TH * 9 / 16)
        if TW > zw - 80: TW = zw - 80; TH = int(TW * 16 / 9)
        bx, by = x0 + (zw - TW) // 2, 330
        g = 34; gw = min(400, (zw - 2 * g) // 3); gh = int(gw * 16 / 9)
        gx0, gy0 = x0 + (zw - (3 * gw + 2 * g)) // 2, 360
        gt = ev.get("grid_t", D - 3.0); n = len(items); parts = []
        for i, it in enumerate(items):
            st = max(0.0, tt[i] - 0.1)
            med = (f'<img src="../assets/feed/{it["file"]}.jpg" style="width:100%;height:100%;object-fit:cover"/>' if mock else
                   f'<video id="lv{i}" class="clip" src="../assets/feed/{it["file"]}.mp4" muted playsinline data-start="{st:.3f}" '
                   f'data-duration="{D - st:.3f}" data-track-index="{2 + i}" style="width:100%;height:100%;object-fit:cover"></video>')
            parts.append(f'<div id="lt{i}" style="position:absolute;left:{bx}px;top:{by}px;width:{TW}px;height:{TH}px;opacity:0;transform-origin:0 0">'
                         f'<div id="li{i}" style="position:absolute;inset:0;transform-origin:50% 60%">'
                         f'<div style="position:absolute;inset:0;border:12px solid #fff;border-radius:12px;overflow:hidden;background:#111;box-shadow:0 30px 80px rgba(0,0,0,.55)">{med}</div>'
                         f'<div id="ll{i}" style="position:absolute;left:-400px;right:-400px;top:{TH + 26}px;text-align:center">'
                         f'<div class="din" style="font-size:96px;line-height:1">{esc(it["label"])}</div>'
                         f'<div class="avb" style="font-size:50px;color:{Y};margin-top:10px;letter-spacing:.03em">{esc(it["handle"])}</div></div></div></div>')
        b = (f'<div id="lk" class="din" style="position:absolute;left:{x0}px;width:{zw}px;top:150px;text-align:center;font-size:112px;line-height:1;opacity:0">'
             f'{esc(ev.get("kicker", ""))}</div>' + "".join(parts))
        if ev.get("kicker"): js.append(f'tl.fromTo("#lk",{{opacity:0,y:-30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{ev.get("kick_t", 0.05):.3f});')
        for i in range(n):
            rot = 3 if i % 2 else -3
            js += [f'tl.set("#lt{i}",{{opacity:1}},{tt[i]:.3f});',
                   f'tl.fromTo("#li{i}",{{scale:.55,rotation:{rot * 3},y:160}},{{scale:1,rotation:{rot},y:0,duration:POP.dur,ease:POP.ease}},{tt[i]:.3f});',
                   f'tl.fromTo("#ll{i}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tt[i] + .12:.3f});']
            if i + 1 < n: js.append(f'tl.to("#lt{i}",{{opacity:0,duration:.16,ease:"none"}},{tt[i + 1]:.3f});')
        for k in range(n):
            gx, gy = gx0 + (k % 3) * (gw + g), gy0 + (k // 3) * (gh + g)
            js += [f'tl.set("#ll{k}",{{opacity:0}},{gt:.3f});', f'tl.to("#li{k}",{{rotation:0,duration:.3}},{gt:.3f});',
                   # a plain .to: a fromTo renders its start state at once, which switched the last tile on (black, before its video) from frame 1
                   f'tl.to("#lt{k}",{{opacity:1,x:{gx - bx},y:{gy - by},scale:{gw / TW:.4f},duration:.55,ease:"power3.out"}},{gt + .05 * k:.3f});']
        if D > 1.2: js.append(f'tl.to(["[id^=lt]","#lk"],{{opacity:0,duration:.28,ease:"none"}},{D - .3:.3f});')
    elif t == "cmts":   # made-up comments of the kind he means (OB 11-04: "make up the comments"): labelled as such, no likes, no real handles
        items, tt = ev["items"], ev["items_t"]; side, x0, x1 = _zone(ev, ev.get("side")); zw = min(1700, x1 - x0)
        left = x0 if side == "R" else x1 - zw
        fs = 112 if zw >= 1350 else 96
        rows = ""
        for i, txt in enumerate(items):
            hd = "@" + "•" * (5 + (i * 3) % 4)
            rows += (f'<div id="cm{i}" class="cmt" style="display:flex;gap:30px;align-items:flex-start;opacity:0;margin-top:58px">'
                     f'<div style="width:150px;height:150px;border-radius:50%;flex:none;background:linear-gradient(140deg,#6b6b6b,#2b2b2b);display:flex;align-items:center;justify-content:center">'
                     f'<svg viewBox="0 0 24 24" width="92" height="92" fill="none" stroke="#c9c9c9" stroke-width="1.6"><circle cx="12" cy="9" r="3.6"/><path d="M5 20c1.2-3.6 3.9-5.4 7-5.4s5.8 1.8 7 5.4"/></svg></div>'
                     f'<div style="min-width:0;flex:1"><div style="font-weight:600;font-size:{int(fs * .6)}px;color:#d9d9d9">{hd}</div>'
                     f'<div style="font-weight:600;font-size:{fs}px;line-height:1.18;color:#fff;margin-top:4px">{esc(txt)}</div></div>'
                     f'{_svg("heart2", 84, stroke="#fff", sw=2, extra="margin-top:40px")}</div>')
        shade = "270deg" if side == "R" else "90deg"
        b = (f'<div id="cs" style="position:absolute;{"right" if side == "R" else "left"}:0;top:0;width:{min(W, zw + 700)}px;height:{H}px;opacity:0;'
             f'background:linear-gradient({shade},rgba(0,0,0,.55),rgba(0,0,0,.25) 60%,rgba(0,0,0,0))"></div>'
             f'<div id="cb" style="position:absolute;left:{left}px;top:{ev.get("y", 520)}px;width:{zw}px">'
             f'<div id="ck" class="din" style="font-size:96px;color:{Y};letter-spacing:.05em;opacity:0">{esc(ev.get("kicker", "COMMENTS LIKE THESE"))}</div>{rows}</div>')
        js.append('tl.fromTo("#cs",{opacity:0},{opacity:1,duration:.25,ease:"none"},0);')
        js += ['tl.fromTo("#ck",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0.05);',
               f'tl.fromTo("#cb",{{y:0}},{{y:-24,duration:{max(D, .5):.3f},ease:"none"}},0);']
        js += [f'tl.fromTo("#cm{i}",{{opacity:0,y:46,scale:.9}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease,transformOrigin:"0% 50%"}},{tt[i]:.3f});' for i in range(len(items))]
        if D > 1.0: js.append(f'tl.to(["#cb","#cs"],{{opacity:0,duration:.25,ease:"none"}},{D - .27:.3f});')
    elif t == "paper":   # the study itself beside him (journal, year, title, authors, the finding highlighted, PMID/DOI)
        s = ev["study"]; side, x0, x1 = _zone(ev, ev.get("side")); zw = x1 - x0
        PWD = int(min(1650, zw - 30)); k = max(.78, PWD / 1650); left = x0 + (zw - PWD) // 2
        fnd = esc(s["finding"]); hl = esc(s["hl"])
        if hl and hl in fnd: fnd = fnd.replace(hl, f'<span class="hlm">{hl}</span>', 1)
        tl_ = s["title"]; fst = int((66 if len(tl_) <= 80 else 58) * k)
        b = (f'<div id="ppw" style="position:absolute;left:{left}px;top:{ev.get("y", 200)}px;width:{PWD}px">'
             f'<div id="pp" class="paper" style="background:#F7F6F1;border-radius:6px;padding:{int(60 * k)}px {int(70 * k)}px {int(52 * k)}px;'
             f'box-shadow:0 40px 100px rgba(0,0,0,.55);transform-origin:50% 100%">'
             f'<div style="display:flex;justify-content:space-between;align-items:baseline;{AVN};font-weight:700;font-size:{int(44 * k)}px;'
             f'letter-spacing:.04em;color:#9B1C1C;text-transform:uppercase"><span>{esc(s["journal"])}</span><span style="color:#777">{esc(str(s["year"]))}</span></div>'
             f'<div style="height:3px;background:#9B1C1C;margin:{int(20 * k)}px 0 {int(28 * k)}px"></div>'
             f'<div style="font-family:Georgia,\'Times New Roman\',serif;font-weight:700;font-size:{fst}px;line-height:1.2;color:#141414">{esc(tl_)}</div>'
             f'<div style="{AVN};font-size:{int(38 * k)}px;color:#6b6b6b;margin-top:{int(18 * k)}px">{esc(s["authors"])}</div>'
             f'<div style="{AVN};font-weight:600;font-size:{int(80 * k)}px;line-height:1.24;color:#1b1b1b;margin-top:{int(34 * k)}px">{fnd}</div>'
             f'<div style="{AVN};font-size:{int(34 * k)}px;color:#8a8a8a;margin-top:{int(30 * k)}px">{esc(s["ref"])}</div></div></div>')
        js += [f'tl.fromTo("#pp",{{opacity:0,y:460,rotation:-10}},{{opacity:1,y:0,rotation:-2,duration:SLIDE.dur,ease:SLIDE.ease}},0.02);',
               f'tl.fromTo("#ppw",{{y:0}},{{y:-28,duration:{max(D, .5):.3f},ease:"none"}},0);',
               f'tl.to(".hlm",{{backgroundSize:"100% 100%",duration:.8,ease:"power2.out"}},{min(1.0, max(.4, D - 1.2)):.3f});']
        if D > 1.0: js.append(f'tl.to("#ppw",{{opacity:0,duration:.28,ease:"none"}},{D - .3:.3f});')
    else:
        raise ValueError(t)
    return b, js


def markus(ev, mock, D):
    """Brand-look explainer overlays on his full-frame shots (Big Shoulders, no boxes, soft shadow, OB yellow on the key word):
    fq   his own line(s) as a big title beside his face, each line landing as he says it (at_t["l0"...]), a key phrase underlined
    tags Markus-style tags: a yellow line icon + his words, springing out beside his head on his words (items_t), drifting up
    num  a big yellow number with a small letter-spaced label above it (brand rule), counting up on his word
    chap the claim label lower left ("CLAIM 03 · FOLIC ACID"), so viewers always know which claim they're in"""
    t = ev["type"]; js = []
    if t == "fq":
        given = ev["text"].split("\n"); side, x0, x1 = _zone(ev, ev.get("side"))
        bw = min(ev.get("w", 1700), x1 - x0); at = ev.get("at_t") or {}
        tg, last = [], -1.0
        for k in range(len(given)):
            r = at.get(f"l{k}", 0.0 if k == 0 else None)
            if r is None or (k and r < last + 0.25): r = last + max(0.4, min(0.8, (D - 0.8) / len(given)))
            tg.append(round(min(max(r, 0.0), max(D - 0.5, 0.0)), 3)); last = tg[-1]
        lines, ts = [], []   # a line over 18 characters wraps at the space nearest its middle, both halves landing together
        for x, tk in zip(given, tg):
            if len(x) > 18 and " " in x:
                sp = [i for i, ch in enumerate(x) if ch == " "]; cut = min(sp, key=lambda i: abs(i - len(x) / 2))
                lines += [x[:cut], x[cut + 1:]]; ts += [tk, tk]
            else: lines.append(x); ts.append(tk)
        n = len(lines)
        L_ = max(len(x) for x in lines); fs = ev.get("size") or int(max(150, min(240, 0.94 * bw / (0.44 * max(L_, 1)))))
        ul = ev.get("underline") or ""
        def uline(x):
            e_ = esc(x)
            return e_.replace(esc(ul), f'<span style="position:relative;display:inline-block;color:{Y}">{esc(ul)}<span class="ubar" style="position:absolute;left:0;right:0;bottom:2px;height:12px;background:{Y};transform-origin:left center"></span></span>', 1) if ul and esc(ul) in e_ else e_
        bh = n * fs * 1.0 + (96 if ev.get("kicker") else 0); top = int(max(180, min(ev.get("y", 1000) - bh / 2, H - 260 - bh)))
        shade = "90deg" if side == "L" else "270deg"
        pos = f"left:{x0}px" if side == "L" else f"right:{W - x1}px"
        rows = "".join(f'<div id="fq{k}" class="din" style="font-size:{fs}px;line-height:1;opacity:0">{uline(x)}</div>' for k, x in enumerate(lines))
        kick = f'<div id="fqk" class="avb" style="font-size:66px;color:{Y};letter-spacing:.14em;text-transform:uppercase;margin-bottom:26px;opacity:0">{esc(ev["kicker"])}</div>' if ev.get("kicker") else ""
        b = (f'<div id="fqs" style="position:absolute;{"left" if side == "L" else "right"}:0;top:0;width:{min(W, bw + 700)}px;height:{H}px;opacity:0;'
             f'background:linear-gradient({shade},rgba(0,0,0,.5),rgba(0,0,0,.22) 60%,rgba(0,0,0,0))"></div>'
             f'<div id="fqb" style="position:absolute;{pos};top:{top}px;width:{bw}px;text-align:{"left" if side == "L" else "right"}">{kick}{rows}</div>')
        js += ['tl.fromTo("#fqs",{opacity:0},{opacity:1,duration:.22,ease:"none"},0);', f'tl.fromTo("#fqb",{{y:0}},{{y:-24,duration:{max(D, .5):.3f},ease:"none"}},0);']
        if kick: js.append('tl.fromTo("#fqk",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0.02);')
        js += [f'tl.fromTo("#fq{k}",{{opacity:0,y:44,scale:.95}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{tk:.3f});' for k, tk in enumerate(ts)]
        kU = next((k for k, x in enumerate(lines) if ul and esc(ul) in esc(x)), None)
        if kU is not None: js.append(f'tl.fromTo("#fq{kU} .ubar",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{min(ts[kU] + .35, max(D - .4, 0)):.3f});')
        if D > 1.0: js.append(f'tl.to(["#fqb","#fqs"],{{opacity:0,duration:.22,ease:"none"}},{D - .24:.3f});')
    elif t == "tags":
        items = ev["items"]; side, x0, x1 = _zone(ev, ev.get("side")); ys = ev.get("ys") or [420, 690, 960]
        side = "L" if side == "R" else "R"   # anchor the row on his side of the zone: the icon sits next to his face, the words run outward
        tt = ev.get("items_t") or [round(.08 + i * .7, 3) for i in range(len(items))]
        b, fit = "", []
        for it in items:   # never past the frame edge (C4407 mocks: 30-letter tags ran off)
            txt = it[0]; fs = int(min(150, (x1 - x0 - 170) / (0.47 * max(len(txt), 1))))
            if fs < 100 and " " in txt:   # a long tag in a narrow zone goes on two lines at a readable size (C4407 11-03: zones that
                sp = [k for k, ch in enumerate(txt) if ch == " "]; cut = min(sp, key=lambda k: abs(k - len(txt) / 2))   # clear his whole
                parts = [txt[:cut], txt[cut + 1:]]                                                                       # movement are narrower)
                fit.append((parts, int(min(128, (x1 - x0 - 170) / (0.47 * max(len(x) for x in parts))))))
            else: fit.append(([txt], fs))
        tops = [ys[i % len(ys)] for i in range(len(items))]
        for i in range(1, len(tops)):   # a two-line tag pushes the rows under it down, never into them
            tops[i] = max(tops[i], tops[i - 1] + int(len(fit[i - 1][0]) * fit[i - 1][1] * 1.02) + 70)
        for i, it in enumerate(items):
            icon = it[1] if len(it) > 1 else "check"; parts, fs = fit[i]
            pos = f"left:{x0}px" if side == "L" else f"right:{W - x1}px"
            b += (f'<div id="tg{i}" style="position:absolute;{pos};top:{tops[i]}px;display:flex;align-items:center;gap:28px;opacity:0;'
                  f'flex-direction:{"row" if side == "L" else "row-reverse"};transform-origin:{"0%" if side == "L" else "100%"} 50%">'
                  f'<svg viewBox="0 0 24 24" width="140" height="140" fill="none" stroke="{Y}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex:none;filter:drop-shadow({SH})">{_icon(icon)}</svg>'
                  f'<span class="din" style="font-size:{fs}px;line-height:1;white-space:nowrap;text-align:{"left" if side == "L" else "right"}">{"<br/>".join(esc(x) for x in parts)}</span></div>')
            ti = tt[i] if i < len(tt) else .08 + i * .7
            js += [f'tl.fromTo("#tg{i}",{{opacity:0,scale:.6,x:{-50 if side == "L" else 50}}},{{opacity:1,scale:1,x:0,duration:POP.dur,ease:POP.ease}},{ti:.3f});',
                   f'tl.fromTo("#tg{i}",{{y:0}},{{y:-20,duration:{max(D - ti, .5):.3f},ease:"none"}},{ti:.3f});']
        if D > 1.0: js.append(f'tl.to("[id^=tg]",{{opacity:0,duration:.25,ease:"none"}},{D - .27:.3f});')
    elif t == "num":
        side, x0, x1 = _zone(ev, ev.get("side")); cx = (x0 + x1) // 2
        import re as _re
        m = _re.match(r"^([^0-9]*)([0-9][0-9,]*)(.*)$", ev["value"]); pre, num, suf = (m.group(1), m.group(2), m.group(3)) if m else ("", "", ev["value"])
        b = (f'<div id="nm" style="position:absolute;left:{cx - 900}px;width:1800px;top:{ev.get("y", 560)}px;text-align:center;opacity:0">'
             f'<div class="avb" style="font-size:64px;letter-spacing:.14em;text-transform:uppercase;color:#f2f2f2">{esc(ev.get("label", ""))}</div>'
             f'<div class="din" style="font-size:{ev.get("size", 330)}px;line-height:.95;color:{Y};margin-top:18px">{esc(pre)}<span id="nv">{esc(num) if (mock or ev.get("static")) else "0"}</span>{esc(suf)}</div>'
             + (f'<div class="avb" style="font-size:62px;margin-top:24px;text-transform:uppercase;letter-spacing:.04em">{esc(ev["sub"])}</div>' if ev.get("sub") else "") + '</div>')
        js += ['tl.fromTo("#nm",{opacity:0,scale:.82,y:30},{opacity:1,scale:1,y:0,duration:POP.dur,ease:POP.ease},0.05);']
        if num and not mock and not ev.get("static"):
            v = int(num.replace(",", ""))
            js += [f'const nvo={{v:0}}; tl.to(nvo,{{v:{v},duration:.9,ease:"power2.out",onUpdate:()=>{{document.getElementById("nv").textContent=Math.round(nvo.v).toLocaleString("en-US")}}}},0.15);']
        if D > 1.0: js.append(f'tl.to("#nm",{{opacity:0,duration:.25,ease:"none"}},{D - .27:.3f});')
    elif t == "chap":
        b = (f'<div id="cp" style="position:absolute;left:150px;top:1860px;opacity:0">'
             f'<div style="width:120px;height:10px;background:{Y};margin-bottom:22px"></div>'
             f'<div style="display:flex;align-items:baseline;gap:30px"><span class="din" style="font-size:112px;color:{Y}">CLAIM {int(ev["n"]):02d}</span>'
             f'<span class="din" style="font-size:112px">{esc(ev["title"])}</span></div></div>')
        js += ['tl.fromTo("#cp",{opacity:0,x:-60},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0.05);']
        if D > 1.0: js.append(f'tl.to("#cp",{{opacity:0,x:-30,duration:.3,ease:"none"}},{D - .32:.3f});')
    return b, js


def body(ev, mock):
    t, D, on = ev["type"], ev["dur"], ev.get("on", "ob")
    js = []
    ox = OB_X + 170 if on == "split" else 170    # OB-side left edge for labels/terms
    if t == "label":
        b = f"""{base(ev, mock)}
<div style="position:absolute;left:{ox - 170}px;top:0;width:2000px;height:700px;background:radial-gradient(ellipse at 0% 0%,rgba(0,0,0,.55),rgba(0,0,0,0) 70%)"></div>
<div id="lb" style="position:absolute;left:{ox}px;top:120px"><div style="width:130px;height:10px;background:{Y};margin-bottom:34px"></div>
<div class="din" style="font-size:118px;line-height:1">{esc(ev["title"])}</div><div class="avb" style="font-size:64px;color:#e8e8e8;margin-top:18px">{esc(ev.get("sub",""))}</div></div>"""
        js += ['tl.fromTo("#lb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0);', f'tl.to("#lb",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.5,0.5):.2f});']
    elif t == "title":
        b = f"""{base(ev, mock)}<div id="tt" class="pop" style="left:150px;top:620px;font-size:330px;line-height:.95;transform:rotate(-5deg)">FACT <span style="color:{Y}">OR</span><br/>CAP?</div>"""
        js += ['tl.fromTo("#tt",{opacity:0,scale:1.6},{opacity:1,scale:1,duration:SLAM.dur,ease:SLAM.ease,transformOrigin:"30% 50%"},0);', f'tl.to("#tt",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.45,0.5):.2f});']
    elif t == "stamp":
        col = {"red": R, "yellow": Y, "green": "#43A047"}[ev.get("color", "red")]
        cx, cy = (OB_X + 1995, 640) if on == "split" else (min(3330, max(2900, int(ev.get("face_cx", 1840)) + 1100)), 900)   # split: over the lamp area between OB and the clip, never on the clip; OB: clear of his face (C4354 R30 sat on his cap)
        if on != "split" and "face_x1" in ev: cx = min(3330, max(2900, int(ev["face_x1"]) + 900))
        size = (300 if len(ev["text"]) <= 4 else 190) if on != "split" else (240 if len(ev["text"]) <= 4 else 150)
        b = f"""{base(ev, mock)}
<div id="st" class="stamp" style="color:{col};left:{cx}px;top:{cy}px;font-size:{size}px;transform:translate(-50%,-50%) rotate(-9deg)">{esc(ev["text"])}</div>
<div id="ss" class="stampsub" style="left:{cx}px;top:{cy + (250 if on != "split" else 200)}px;transform:translateX(-50%);width:{1100 if on != "split" else 880}px;text-align:center">{esc(ev.get("topic",""))}</div>"""
        js += ['tl.fromTo("#st",{opacity:0,scale:2.2},{opacity:1,scale:1,duration:SLAM.dur,ease:SLAM.ease},0);',
               'tl.fromTo("#ss",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.25);',
               f'tl.to(["#st","#ss"],{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.4,0.6):.2f});']
    elif t == "pop":
        lines = wrap(ev["text"], 12)
        room = 1060 if on == "split" or "face_x0" not in ev else max(600, min(1060, int(ev["face_x0"]) - 230 - 130))   # left of his face over the whole event
        fs = min(230, int(room / (0.47 * max(len(l) for l in lines))))
        x, y = (OB_X + 365, 1980 - len(lines) * fs) if on == "split" else (130, 1080 - len(lines) * fs // 2)
        b = f"""{base(ev, mock)}<div id="pp" class="pop" style="left:{x}px;top:{y}px;font-size:{fs}px;line-height:1;transform:rotate(-5deg)">{"<br/>".join(esc(l) for l in lines)}</div>"""
        js += ['tl.fromTo("#pp",{opacity:0,scale:.4,rotation:-14},{opacity:1,scale:1,rotation:-5,duration:POP.dur,ease:POP.ease,transformOrigin:"0% 50%"},0);',
               f'tl.to("#pp",{{opacity:0,scale:.9,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.35,0.5):.2f});']
    elif t == "term":
        x, y = (ox, 1700) if on == "split" else (220, 1660)
        b = f"""{base(ev, mock)}<div id="tm" class="term" style="left:{x}px;top:{y}px"><div class="t">{esc(ev["text"])}</div><div class="s">{esc(ev.get("sub",""))}</div></div>"""
        js += ['tl.fromTo("#tm",{opacity:0,y:40,scale:.92},{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease,transformOrigin:"0% 100%"},0);',
               f'tl.to("#tm",{{opacity:0,y:20,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.4,0.5):.2f});']
    elif t == "skip":
        b = f"""<div class="bg"></div><div id="sk" class="center din" style="top:930px;font-size:200px">{esc(ev["text"])}</div>
<div id="skb" style="position:absolute;left:1220px;top:1180px;width:1400px;height:14px;background:{Y};transform-origin:left center"></div>"""
        js += ['tl.fromTo("#sk",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);', 'tl.fromTo("#skb",{scaleX:0},{scaleX:1,duration:SOFT.dur,ease:SOFT.ease},.2);']
    elif t == "cite":
        b = f"""<div class="bg"></div>
<div id="ct" style="position:absolute;left:420px;top:470px;width:3000px">
 <div class="avb" style="font-size:60px;color:{Y};letter-spacing:6px">THE STUDY</div>
 <div class="din" style="font-size:118px;line-height:1.08;margin-top:26px">{esc(ev["title"])}</div>
 <div class="av" style="font-size:58px;color:#bdbdbd;margin-top:30px">{esc(ev["source"])}</div>
 <div id="cf" class="avb" style="font-size:86px;line-height:1.25;margin-top:90px;padding-left:44px;border-left:14px solid {Y}">{esc(ev["finding"])}</div>
 <div class="av" style="font-size:40px;color:#8a8a8a;margin-top:60px">{esc(ev["link"]) if ev.get("link") else "doi.org/" + esc(ev["doi"])}</div></div>"""
        js += ['tl.fromTo("#ct",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);', 'tl.fromTo("#cf",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.9);',
               ]
    elif t == "ba":
        j, (bf, bl), (af, al) = ev["japan"], ev["before"], ev["after"]
        b = f"""<div class="bg"></div>
<div id="jp" style="position:absolute;left:1320px;top:180px;width:1200px;height:1600px;border-radius:30px;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.6)"><img src="../assets/photos/{j}" style="width:100%;height:100%;object-fit:cover"/></div>
<div id="jpl" class="center din" style="top:1840px;font-size:96px">Japan, November</div>
<div id="bat" class="center din" style="top:150px;font-size:130px">{esc(ev["title"])}</div>
<div id="ba" style="position:absolute;left:0;width:100%;top:390px;display:flex;justify-content:center;gap:70px">
 <div style="text-align:center"><div style="width:1080px;height:1440px;border-radius:30px;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.6)"><img src="../assets/photos/{bf}" style="width:100%;height:100%;object-fit:cover"/></div><div class="din" style="font-size:96px;margin-top:30px">{esc(bl)}</div></div>
 <div style="text-align:center"><div style="width:1080px;height:1440px;border-radius:30px;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.6)"><img src="../assets/photos/{af}" style="width:100%;height:100%;object-fit:cover"/></div><div class="din" style="font-size:96px;margin-top:30px;color:{Y}">{esc(al)}</div></div></div>"""
        sw = min(2.6, D * 0.35)
        js += ['tl.fromTo(["#jp","#jpl"],{opacity:0,scale:.94},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},0);', 'tl.set(["#bat","#ba"],{opacity:0},0);',
               f'tl.to(["#jp","#jpl"],{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{sw:.2f});',
               f'tl.fromTo("#bat",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{sw + 0.1:.2f});',
               f'tl.fromTo("#ba",{{opacity:0,y:50}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{sw + 0.2:.2f});',
               ]
    elif t == "proof4":
        b = f"""<div class="bg"></div>
<div id="pf" style="position:absolute;left:900px;top:110px;width:1060px;height:1884px;border-radius:30px;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.6)"><img src="../assets/proof/{ev["image"]}" style="width:100%;height:100%;object-fit:cover"/></div>
<div id="pft" style="position:absolute;left:2160px;top:760px"><div style="width:150px;height:12px;background:{Y};margin-bottom:40px"></div>
 <div class="din" style="font-size:230px;line-height:1">{esc(ev["title"])}</div><div class="avb" style="font-size:96px;color:{Y};margin-top:30px">{esc(ev.get("sub",""))}</div>
 <div class="av" style="font-size:50px;color:#9a9a9a;margin-top:60px">{esc(ev.get("foot",""))}</div></div>"""
        js += ['tl.fromTo("#pf",{opacity:0,y:60},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);', 'tl.fromTo("#pft",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);',
               ]
    elif t == "montage":
        items = ev["items_r"]; slot = D / max(1, len(items)); parts = []
        for i, it in enumerate(items):
            st = i * slot
            if it["kind"] == "shot":
                fit = "object-fit:cover;object-position:50% 0%" if it["mode"] == "bio" else "object-fit:contain"
                inner = f'<img src="../assets/shots/{it["file"]}" style="width:100%;height:{ "2500px" if it["mode"] == "bio" else "100%"};{fit}"/>'
            else:
                inner = (f'<img src="../assets/stills/{ev["id"]}_m{i}.jpg" style="width:100%;height:100%;object-fit:contain"/>' if mock else
                         f'<video id="mv{i}" class="clip" src="../assets/montage/{ev["id"]}_m{i}.mp4" muted playsinline data-start="{st:.3f}" data-duration="{slot:.3f}" data-track-index="{2 + i}" style="width:100%;height:100%;object-fit:contain"></video>')
            parts.append(f'<div class="mi" id="mi{i}" style="position:absolute;inset:0;opacity:0">{inner}</div>')
            js += [f'tl.set("#mi{i}",{{opacity:1}},{st:.3f});', f'tl.fromTo("#mi{i}",{{scale:1.0}},{{scale:1.12,duration:{slot:.3f},ease:"none",transformOrigin:"50% 18%"}},{st:.3f});']
            if i + 1 < len(items): js.append(f'tl.set("#mi{i}",{{opacity:0}},{st + slot:.3f});')
        b = f"""{base(ev, mock)}<div class="panelClip">{"".join(parts)}</div>
<div id="mt" style="position:absolute;left:{OB_X + 170}px;top:120px"><div style="width:130px;height:10px;background:{Y};margin-bottom:34px"></div><div class="din" style="font-size:110px;line-height:1.05;width:2200px">{esc(ev["title"])}</div></div>"""
        js.insert(0, 'tl.fromTo("#mt",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.2);')
        if mock: js.append(f'tl.set(".mi",{{opacity:0}},{D-0.05:.3f}); tl.set("#mi0",{{opacity:1}},{D-0.04:.3f});')
    elif t == "glyco":   # C4407 (OB 11-03: "add any animations you can make"): Kreitzman 1992, 1 g glycogen is stored with 3-4 g water
        sd, x0, x1 = _zone(ev); cx = (x0 + x1) // 2; top = 430; drop = _icon("drop")   # never "side": that name is the side-layout helper
        drops = "".join(f'<svg class="gw" id="gw{i}" viewBox="0 0 24 24" width="190" height="190" fill="#4FA8FF" stroke="#BFE1FF" stroke-width="1.2" '
                        f'style="position:absolute;left:{cx - 470 + 250 * i}px;top:{top + 330}px;opacity:0;filter:drop-shadow({SH})">{drop}</svg>' for i in range(4))
        b = (base(ev, mock) +
             f'<div id="gk" class="avb" style="position:absolute;left:{cx - 900}px;width:1800px;top:{top - 150}px;text-align:center;font-size:64px;letter-spacing:.14em;text-transform:uppercase;opacity:0">What 1 gram of stored carbs holds</div>'
             f'<div id="gb" style="position:absolute;left:{cx - 140}px;top:{top}px;width:280px;height:280px;background:{Y};border-radius:26px;opacity:0;box-shadow:0 30px 80px rgba(0,0,0,.45)"></div>'
             f'<div id="gbl" class="din" style="position:absolute;left:{cx - 400}px;width:800px;top:{top + 90}px;text-align:center;font-size:96px;color:#111;opacity:0">1 G CARBS</div>'
             + drops +
             f'<div id="gwl" class="din" style="position:absolute;left:{cx - 900}px;width:1800px;top:{top + 560}px;text-align:center;font-size:120px;opacity:0">+ 3-4 G <span style="color:#4FA8FF">WATER</span></div>'
             f'<div id="gc" class="din" style="position:absolute;left:{cx - 1000}px;width:2000px;top:{top + 760}px;text-align:center;font-size:130px;opacity:0">CUT CARBS: <span style="color:{Y}">BOTH LEAVE</span></div>'
             f'<div class="av" style="position:absolute;left:{cx - 900}px;width:1800px;top:{top + 940}px;text-align:center;font-size:40px;color:#d6d6d6">Kreitzman et al. 1992, Am J Clin Nutr</div>')
        js += ['tl.fromTo("#gk",{opacity:0,y:-20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0.05);',
               'tl.fromTo(["#gb","#gbl"],{opacity:0,scale:.5},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},0.15);']
        js += [f'tl.fromTo("#gw{i}",{{opacity:0,y:-60,scale:.4}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{0.55 + 0.18 * i:.2f});' for i in range(4)]
        js += ['tl.fromTo("#gwl",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},1.35);']
        t_go = max(1.9, min(D * 0.55, D - 1.6))
        js += [f'tl.to(["#gb","#gbl",".gw"],{{x:{"900" if sd == "R" else "-900"},opacity:0,duration:.7,ease:"power2.in",stagger:.06}},{t_go:.2f});',
               f'tl.to("#gwl",{{opacity:.25,duration:.4,ease:"none"}},{t_go:.2f});',
               f'tl.fromTo("#gc",{{opacity:0,scale:.85}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t_go + .45:.2f});']
        if D > 1.0: js.append(f'tl.to(["#gk","#gc","#gwl"],{{opacity:0,duration:.25,ease:"none"}},{D - .27:.3f});')
    elif t in ("feed", "lineup", "cmts", "paper"):   # C4415 rev 2 (OB 11-04 notes on v3)
        b, js2 = rev2(ev, mock, D); b = base(ev, mock) + b; js += js2
    elif t in ("fq", "tags", "num", "chap"):   # C4407 (OB 11-03: "add the overlays and stuff like markusfit and dr mike ... when im explaining")
        b, js2 = markus(ev, mock, D); b = base(ev, mock) + b; js += js2
    elif t == "correction":   # OB's on-screen correction (C4407 folic acid, 11-03): yellow label, the right amount big, the source small
        line = esc(ev["line"])
        if ev.get("accent"): line = line.replace(esc(ev["accent"]), f'<span style="color:{Y}">{esc(ev["accent"])}</span>', 1)
        inner = (f'<div id="cr" style="position:absolute;left:150px;top:{ev.get("top", 470)}px;width:1920px">'
                 f'<div class="avb" style="font-size:70px;color:{Y};letter-spacing:.16em;text-transform:uppercase">{esc(ev["title"])}</div>'
                 f'<div class="din" style="font-size:150px;line-height:1.02;margin-top:34px">{line}</div>'
                 f'<div class="avb" style="font-size:70px;line-height:1.18;margin-top:48px">{esc(ev.get("sub", ""))}</div>'
                 f'<div class="av" style="font-size:46px;color:#d6d6d6;margin-top:56px;line-height:1.3">{esc(ev.get("small", ""))}</div></div>')
        b = side(ev, mock, inner, js, D)
        js.append('tl.fromTo("#cr",{opacity:0,x:40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.35);')
    elif t == "end":   # side layout, no boxed PiP (OB's C4352 rule): his frame slides left, the card fills the right
        inner = (f'<div id="eb" style="position:absolute;left:170px;top:600px;width:1900px"><div style="width:150px;height:12px;background:{Y};margin-bottom:46px"></div>'
                 f'<div class="din" style="font-size:220px;line-height:1">{esc(ev["title"])}</div>'
                 f'<div class="avb" style="font-size:82px;margin-top:50px;line-height:1.2">{esc(ev["line"])}</div>'
                 f'<div class="av" style="font-size:62px;margin-top:44px;color:#bdbdbd">{esc(ev.get("small", ""))}</div></div>')
        b = side(ev, mock, inner, js, D, back=False)
        js.append('tl.fromTo("#eb",{opacity:0,x:40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.35);')
    elif t == "overlay":
        # Images straight on OB's own frame, nothing drawn around them (OB's C4352 rule). Each item is
        # [file key, slot, optional label]; a new image in an occupied slot hard-cuts the old one away.
        S = slots(ev); times = ev["items_t"]; imgs, last = [], {}
        lab_h = 120 if any(len(it) > 2 and it[2] for it in ev["items"]) else 0
        for i, it in enumerate(ev["items"]):
            key, si = it[0], it[1]; lbl = it[2] if len(it) > 2 else None
            x, y, w, h = S[si]
            lab = f'<div class="ovl din">{esc(lbl)}</div>' if lbl else ""
            imgs.append(f'<div class="ovw" id="o{i}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                        f'<img src="../assets/{ev.get("folder", "proof")}/{key}.jpg" style="height:{h - lab_h}px"/>{lab}</div>')
            if si in last: js.append(f'tl.set("#o{last[si]}",{{opacity:0}},{times[i]:.3f});')
            js.append(f'tl.set("#o{i}",{{opacity:1}},{times[i]:.3f});')
            js.append(f'tl.fromTo("#o{i}",{{scale:1.07}},{{scale:1,duration:SNAP.dur,ease:SNAP.ease}},{times[i]:.3f});')
            nxt = [times[j] for j in range(i + 1, len(times)) if ev["items"][j][1] == si]
            hold = (nxt[0] if nxt else D - 0.27) - times[i]
            if hold >= 2.5:   # long hold: slow drift so the photo never sits frozen (no dead frames)
                js.append(f'tl.to("#o{i}",{{scale:1.04,duration:{hold:.3f}-SNAP.dur,ease:"none"}},{times[i]:.3f}+SNAP.dur);')
            last[si] = i
        b = base(ev, mock) + "".join(imgs)
        if ev.get("foot"):
            b += (f'<div class="av" style="position:absolute;left:60px;top:2080px;font-size:40px;color:rgba(255,255,255,.78);'
                  f'text-shadow:0 2px 10px rgba(0,0,0,.85);white-space:nowrap">{esc(ev["foot"])}</div>')
        if D > 1.0: js.append(f'tl.to(".ovw",{{opacity:0,duration:.25,ease:"none"}},{D - 0.27:.3f});')
    elif t == "study":   # the paper on screen (journal, year, title, authors, finding, PubMed ID, DOI) + its numbers as a chart
        c = ev.get("chart")
        inner = (f'<div style="position:absolute;left:110px;top:{130 if c else 680}px;width:1980px;display:flex;flex-direction:column;gap:64px">'
                 f'{study_html(ev["study"])}{chart_html(c, False) if c else ""}</div>')
        b = side(ev, mock, inner, js, D)
        js += ['tl.fromTo("#sc",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.3);',
               'tl.to(".hl",{backgroundColor:"rgba(247,220,58,1)",duration:.45,ease:"none"},1.2);']
        if c: js += ['tl.fromTo("#ch",{opacity:0},{opacity:1,duration:.3,ease:"none"},.7);'] + chart_js(c, 1.0)
    elif t == "list":   # code-drawn list on the side layout (C4354): items land one by one, on his words (items_t) or as a cascade
        txt = [it[0] if isinstance(it, list) else it for it in ev["items"]]; n = len(txt)
        times = ev.get("items_t") or [round(0.55 + i * (D * 0.62) / max(1, n), 3) for i in range(n)]
        cols = 2 if n > 8 else 1; per = (n + cols - 1) // cols; fs = 96 if cols == 1 else 66; rh = int(fs * 1.62)
        rows = [f'<div class="li" id="li{i}" style="display:flex;align-items:center;gap:30px;height:{rh}px;opacity:0">'
                f'<div style="width:{int(fs * .4)}px;height:{int(fs * .4)}px;background:{Y};flex:none"></div>'
                f'<div class="avb" style="font-size:{fs}px;line-height:1.05;white-space:nowrap">{esc(x)}</div></div>' for i, x in enumerate(txt)]
        colw = 2000 // cols
        grid = "".join(f'<div style="display:flex;flex-direction:column;width:{colw}px">{"".join(rows[c * per:(c + 1) * per])}</div>' for c in range(cols))
        foot = f'<div id="lf" class="av" style="font-size:46px;color:#a8a8a8;margin-top:40px;opacity:0">{esc(ev.get("foot", ""))}</div>' if ev.get("foot") else ""
        inner = (f'<div style="position:absolute;left:110px;top:{220 if cols == 2 else 300}px;width:2000px">'
                 f'<div id="lt"><div style="width:130px;height:10px;background:{Y};margin-bottom:34px"></div>'
                 f'<div class="din" style="font-size:{140 if len(ev["title"]) < 24 else 112}px;line-height:1">{esc(ev["title"])}</div></div>'
                 f'<div style="display:flex;margin-top:70px">{grid}</div>{foot}</div>')
        b = side(ev, mock, inner, js, D)
        js.append('tl.fromTo("#lt",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);')
        for i, tt in enumerate(times):
            js.append(f'tl.fromTo("#li{i}",{{opacity:0,x:-36}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(0.45, tt):.3f});')
        if foot: js.append(f'tl.to("#lf",{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{max(0.6, times[-1] + 0.3):.3f});')
    elif t == "chart":   # standalone animated chart from primary data, same side layout
        c = ev["chart"]
        inner = f'<div style="position:absolute;left:110px;top:{c.get("top", 190)}px;width:1980px">{chart_html(c, True)}</div>'
        b = side(ev, mock, inner, js, D)
        js += ['tl.fromTo("#ch",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.3);'] + chart_js(c, 0.8)
    elif t == "lab":   # C4415 (OB 11-04 "copy trainbloom on some overlays"): TrainBloom's off-white lab slide on the side layout.
        # ev["html"] is the slide in the approved mockups' units (1100 x 1080, the panel at half scale), drawn at 2x; ev["js"] animates
        # it (GSAP lines on tl, times from the event start). No brand shadow on the slide: his slides are flat.
        inner = ('<style>#panel svg text{font-family:\'Avenir Next\',sans-serif !important}</style>'   # the base CSS puts BSD on every svg text
                 '<div style="position:absolute;inset:0;background:#F3F2EE"></div>'
                 '<div style="position:absolute;left:0;top:0;width:1100px;height:1080px;transform:scale(2);transform-origin:0 0;'
                 f'font-family:\'Avenir Next\',sans-serif;color:#1d1d1d;text-shadow:none">{ev["html"]}</div>')
        b = side(ev, mock, inner, js, D, back=ev.get("back", True))
        js += list(ev.get("js", []))
    elif t == "plinth":   # C4415: TrainBloom's plinth with the product, virtual (Blender, 1920x1080 shown at 2x): her meal on a white
        # plinth that rises in on the right, floating white labels with pointers, his number counting up, the day meter bottom left
        x0, y0, x1, y1 = [v * 2 for v in ev["meal_box"]]; px = int(ev.get("px", 0)); cx = (x0 + x1) // 2 + px
        F = "font-family:'Avenir Next',sans-serif;color:#fff;white-space:nowrap;position:absolute;transform:translateX(-50%)"
        tri = f'<div style="position:absolute;left:{cx - 22}px;top:{y0 - 66}px;width:0;height:0;border-left:22px solid transparent;border-right:22px solid transparent;border-top:26px solid #fff;filter:drop-shadow(0 6px 10px rgba(0,0,0,.5))"></div>'
        lab = (f'<div id="pk" style="{F};left:{cx}px;top:{y0 - 500}px;font-size:230px;font-weight:800;line-height:1">{ev["kcal"]}</div>'
               f'<div id="pu" style="{F};left:{cx}px;top:{y0 - 252}px;font-size:58px;font-weight:600;letter-spacing:.06em">{esc(ev["sub"])}</div>'
               f'<div id="pn" style="{F};left:{cx}px;top:{y0 - 160}px;font-size:60px;font-weight:600;letter-spacing:.04em">{esc(ev["name"])}</div>'
               f'<div id="pt">{tri}</div>')
        segs, run = "", 0
        for i, k in enumerate(ev["meter"]["meals"]):
            w_ = 1120 * k / ev["meter"]["total"]
            cur = i == len(ev["meter"]["meals"]) - 1
            segs += (f'<div id="{"ms" if cur else f"m{i}"}" style="position:absolute;left:{140 + run + 4:.0f}px;top:1968px;width:{max(4, w_ - 8):.0f}px;height:28px;'
                     f'border-radius:14px;background:{Y if cur else "rgba(255,255,255,.92)"};transform-origin:0 50%"></div>'); run += w_
        meter = (f'<div style="position:absolute;left:140px;top:1968px;width:1120px;height:28px;border-radius:14px;background:rgba(255,255,255,.28)"></div>{segs}'
                 f'<div id="ml" style="position:absolute;left:140px;top:1872px;font-family:\'Avenir Next\',sans-serif;font-weight:600;font-size:56px;'
                 f'letter-spacing:.05em;color:#fff;white-space:nowrap">{esc(ev["meter"]["who"])}&nbsp; <span id="mv">{ev["meter"]["to"]:,}</span> KCAL</div>')
        b = (base(ev, mock) + f'<div id="plg"><img id="pl" src="../assets/plinth/{ev["key"]}.png" style="position:absolute;left:{px}px;top:0;width:3840px;height:2160px"/></div>'
             + f'<div id="plab">{lab}</div><div id="pm">{meter}</div>')
        js += ['tl.fromTo("#pl",{y:1150},{y:0,duration:SLIDE.dur,ease:SLIDE.ease},0);',
               'tl.fromTo("#plab",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.38);',
               'tl.fromTo("#pk",{scale:.82},{scale:1,duration:POP.dur,ease:POP.ease},.38);',   # numbers pop in at their value (seek-safe; no onUpdate counters)
               'tl.fromTo("#pm",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
               'tl.fromTo("#ms",{scaleX:0},{scaleX:1,duration:.7,ease:"power2.out"},.6);']
        if D > 1.6:
            js += [f'tl.to("#pl",{{y:1150,duration:SOFT.dur,ease:SOFT.ease}},{D - 0.5:.3f});',
                   f'tl.to(["#plab","#pm"],{{opacity:0,duration:.25,ease:"none"}},{D - 0.45:.3f});']
    elif t == "chip":   # C4415: a small flat label on his frame (diet name, COMING UP, the disclaimer); lines = [text, px, weight, colour]
        lines = "".join(f'<div style="font-size:{s}px;font-weight:{wt};letter-spacing:.05em;line-height:1.18;color:{c}">{esc(tx)}</div>' for tx, s, wt, c in ev["lines"])
        hgt = sum(int(s * 1.18) for _, s, _, _ in ev["lines"])
        top = 150 if ev.get("pos") == "tl" else 2160 - 150 - hgt
        b = base(ev, mock) + f'<div id="ch" style="position:absolute;left:140px;top:{top}px;font-family:\'Avenir Next\',sans-serif;white-space:nowrap">{lines}</div>'
        js += ['tl.fromTo("#ch",{opacity:0,y:24},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0.05);',
               f'tl.to("#ch",{{opacity:0,duration:.3,ease:"none"}},{max(0.5, D - 0.35):.3f});']
    else:
        raise ValueError(t)
    return b, js


def page(ev, mock):
    b, js = body(ev, mock)
    return f"""<!doctype html>
<html lang="en" data-resolution="landscape"><head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script><style>{CSS}{EXTRA_CSS}{REV2_CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{ev['dur']:.3f}" data-width="{W}" data-height="{H}">
{b}
</div>
<script>
window.__timelines = window.__timelines || {{}};
{SPRINGS}
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""


def main():
    events = json.load(open(sys.argv[1]))["events"]
    proj, mock = sys.argv[2], "--mock" in sys.argv
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    for ev in events:
        open(f'{proj}/compositions/{ev["id"]}{".mock" if mock else ""}.html', "w").write(page(ev, mock))
    print(len(events), "reaction compositions ->", proj, "(mock)" if mock else "")


if __name__ == "__main__":
    main()
