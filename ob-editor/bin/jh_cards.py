#!/usr/bin/env python3
"""Paper cards for the Johnny Harris-style edit (C4372 "We Lost the Plot", 2026-10-23), loaded by cards.py.

  anchor   the adult obesity line (CDC/NCHS NHANES, ages 20-74, age-adjusted), drawn in red ink on paper up to an era's end;
           survey points pop as the pen reaches them; optional era tags pinned on the line, a shaded band, a second series
           (the sweetener supply, fat's share of calories) and the dotted "what should happen" line
  ledger   the scorecard: four rows (the villain, what they sold you, who got paid, what the line did), one column per era,
           the current column typing in on his words, the past columns in older ink; optional red stamp for the motif
  stamp    a red rubber stamp slammed over his own frame (dates, verdicts); his face stays (not a cover)
Every card is drawn in code on the paper sheet (hf/assets/paper.jpg, made in code), its first frame finished; the sheet
pushes in at a constant speed for the whole card. Times come from ev["at_t"] (seconds from the card's start).
"""
import html

W, H = 3840, 2160
INK, RED, YEL = "#1f1b16", "#B3261E", "#F7DC3A"
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
FONTS = ("<style>@font-face{font-family:'ATW';src:url('../assets/fonts/AmericanTypewriter.ttf')}"
         "@font-face{font-family:'ATWB';src:url('../assets/fonts/AmericanTypewriterBold.ttf')}"
         "@font-face{font-family:'ATWS';src:url('../assets/fonts/AmericanTypewriterSemibold.ttf')}"
         ".atw{font-family:'ATW'}.atwb{font-family:'ATWB'}.atws{font-family:'ATWS'}</style>")
PAPER = ('<img src="../assets/paper.jpg" style="position:absolute;left:-40px;top:-24px;width:3920px;height:2208px;object-fit:cover">'
         '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 55%,rgba(40,25,10,.28) 100%)"></div>')
# CDC/NCHS Health E-Stat 111 (Feb 2026), adults 20-74, age-adjusted; x = the middle of each survey period
NHANES = [(1961, 13.4), (1972.5, 14.5), (1978, 15.0), (1991, 23.2), (1999.5, 30.9), (2001.5, 31.2), (2003.5, 32.9), (2005.5, 35.1),
          (2007.5, 34.3), (2009.5, 36.1), (2011.5, 35.3), (2013.5, 38.2), (2015.5, 40.0), (2017.5, 42.8), (2022, 40.8)]


def T(ev, key, default):
    if isinstance(key, (int, float)): return float(key)
    return float((ev.get("at_t") or {}).get(key, default))


# ------------------------------------------------------------------------------------------------ anchor
Y0, Y1, VMAX = 1957, 2025, 45.0
# Two layouts: the full sheet, or "beside": the board in cards.py's left panel (SIDE_W 2300 px) with OB slid right, his face on
# screen (Johnny Harris's 1955 vs 2025: he stands beside the chart for half the runtime, and his most-replayed moment is him beside
# the board, then 2.6 s of the chart full frame). f scales the type and the marks; the full sheet's numbers are the 10-23 originals.
GEO = {False: dict(X0=560, X1=3420, YB=1800, YT=470, f=1.0, ty=150, ts=150, sy=315, ss=58, ylx=190, yls=56, xw=240, xt=34, xls=60,
                   ny=1955, nw=2900, ns=44, src="right:120px;top:2040px;font-size:40px"),
       True: dict(X0=330, X1=2060, YB=1690, YT=640, f=0.92, ty=190, ts=132, sy=345, ss=52, ylx=180, yls=54, xw=200, xt=30, xls=56,
                  ny=1845, nw=1730, ns=40, src="left:330px;top:1960px;width:1760px;font-size:34px;line-height:1.3")}
X0, X1, YB, YT = (GEO[False][k] for k in ("X0", "X1", "YB", "YT"))
xa = lambda yr, g=GEO[False]: g["X0"] + (yr - Y0) / (Y1 - Y0) * (g["X1"] - g["X0"])
ya = lambda v, g=GEO[False]: g["YB"] - v / VMAX * (g["YB"] - g["YT"])


def _cum(pts):
    out, L = [0.0], 0.0
    for (a, b), (c, d) in zip(pts, pts[1:]):
        L += ((c - a) ** 2 + (d - b) ** 2) ** 0.5; out.append(L)
    return out


def anchor(ev, mock):
    D = ev["dur"]; frm, to = ev.get("from", 1957), ev.get("to", 2023)
    g = GEO[bool(ev.get("beside"))]; f = g["f"]; X0, X1, YB, YT = g["X0"], g["X1"], g["YB"], g["YT"]
    xa_ = lambda yr: xa(yr, g)
    ya_ = lambda v: ya(v, g)
    pts = [(xa_(y), ya_(v), y, v) for y, v in NHANES if y <= to + 0.6]
    P = [(p[0], p[1]) for p in pts]; cum = _cum(P); Ltot = cum[-1] if cum else 1
    def len_at(year):
        if year <= pts[0][2]: return 0.0
        for k in range(len(pts) - 1):
            if pts[k][2] <= year <= pts[k + 1][2]:
                fr_ = (year - pts[k][2]) / (pts[k + 1][2] - pts[k][2]); return cum[k] + fr_ * (cum[k + 1] - cum[k])
        return Ltot
    t_draw = T(ev, "draw", 0.35); d_draw = float(ev.get("draw_dur", max(1.2, min(3.2, (to - max(frm, 1961)) / 14))))
    l0 = len_at(frm)
    title = ev.get("title", "Adults with obesity"); sub = ev.get("sub", "United States, ages 20 to 74")
    b = [FONTS, '<div id="aw" style="position:absolute;inset:0;transform-origin:52% 50%">', PAPER,
         f'<div class="din" style="position:absolute;left:{X0}px;top:{g["ty"]}px;font-size:{g["ts"]}px;line-height:1;color:{INK};letter-spacing:2px">{esc(title.upper())}</div>',
         f'<div class="atw" style="position:absolute;left:{X0 + 6}px;top:{g["sy"]}px;font-size:{g["ss"]}px;color:#4a4136">{esc(sub)}</div>']
    for v in (10, 20, 30, 40):
        b.append(f'<div style="position:absolute;left:{X0}px;top:{ya_(v):.0f}px;width:{X1 - X0}px;border-top:3px dashed rgba(31,27,22,.18)"></div>'
                 f'<div class="atw" style="position:absolute;left:{X0 - g["ylx"]}px;top:{ya_(v) - 34 * f:.0f}px;width:{g["ylx"] - 30}px;text-align:right;font-size:{g["yls"]}px;color:#5a5044">{v}%</div>')
    b.append(f'<div style="position:absolute;left:{X0}px;top:{YB}px;width:{X1 - X0}px;height:6px;background:{INK};opacity:.85"></div>')
    for yr in range(1960, 2030, 10):
        b.append(f'<div class="atw" style="position:absolute;left:{xa_(yr) - g["xw"] / 2:.0f}px;top:{YB + g["xt"]}px;width:{g["xw"]}px;text-align:center;font-size:{g["xls"]}px;color:#3b342c">{yr}</div>'
                 f'<div style="position:absolute;left:{xa_(yr) - 2:.0f}px;top:{YB - 10}px;width:5px;height:26px;background:{INK};opacity:.7"></div>')
    js = []
    # bands (behind the line)
    for k, bd in enumerate(ev.get("bands", [])):
        a_, b_, lab, key = bd
        b.append(f'<div id="bd{k}" style="position:absolute;left:{xa_(a_):.0f}px;top:{YT - 40}px;width:{xa_(b_) - xa_(a_):.0f}px;height:{YB - YT + 40}px;'
                 f'background:rgba(179,38,30,.10);border-left:4px solid rgba(179,38,30,.45);border-right:4px solid rgba(179,38,30,.45)">'
                 f'<div class="din" style="position:absolute;left:0;right:0;top:{-96 * f:.0f}px;text-align:center;font-size:{84 * f:.0f}px;color:{RED}">{esc(lab)}</div></div>')
        if T(ev, key, 1.0) >= 0: js.append(f'tl.fromTo("#bd{k}",{{opacity:0,scaleX:.001}},{{opacity:1,scaleX:1,duration:SLIDE.dur,ease:SLIDE.ease,transformOrigin:"0% 50%"}},{T(ev, key, 1.0):.3f});')
    # second series (its own right-hand scale), drawn in blue ink
    s2 = ev.get("series2")
    if s2:
        mx = s2.get("max", max(v for _, v in s2["points"]) * 1.15)
        y2 = lambda v: YB - v / mx * (YB - YT)
        P2 = [(xa_(yr), y2(v)) for yr, v in s2["points"]]; L2 = _cum(P2)[-1]
        d2 = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(P2))
        c2 = s2.get("color", "#1F5FA8")
        t2 = T(ev, s2.get("at", "s2"), 1.2)
        b.append(f'<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}"><path id="s2" d="{d2}" fill="none" stroke="{c2}" stroke-width="{12 * f:.0f}" '
                 f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{L2:.1f}" stroke-dashoffset="{L2 if t2 >= 0 else 0:.1f}"/></svg>')
        lx, ly_ = P2[-1]
        b.append(f'<div id="s2l" class="atwb" style="position:absolute;left:{lx - 900 * f:.0f}px;top:{ly_ + 30 * f:.0f}px;width:{880 * f:.0f}px;text-align:right;font-size:{58 * f:.0f}px;color:{c2}">{esc(s2["label"])}</div>')
        if t2 >= 0: js += [f'tl.to("#s2",{{strokeDashoffset:0,duration:{s2.get("dur", 2.2)},ease:"none"}},{t2:.3f});',
               f'tl.fromTo("#s2l",{{opacity:0}},{{opacity:1,duration:.4}},{t2 + s2.get("dur", 2.2) - 0.3:.3f});']
    # the obesity line
    dpath = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(P))
    # a part cut from a longer card (beside_split.py) keeps the card's times: a negative time happened before the part began, so
    # that element starts finished (no tween) and the line starts as far drawn as it had got
    lt = l0 + (Ltot - l0) * min(1.0, -t_draw / max(d_draw, 1e-6)) if t_draw < 0 else l0
    b.append(f'<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}"><path id="ln" d="{dpath}" fill="none" stroke="{RED}" stroke-width="{16 * f:.0f}" '
             f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{Ltot:.1f}" stroke-dashoffset="{Ltot - lt:.1f}"/></svg>')
    if t_draw >= 0:
        js.append(f'tl.fromTo("#ln",{{strokeDashoffset:{Ltot - l0:.1f}}},{{strokeDashoffset:0,duration:{d_draw:.3f},ease:"none"}},{t_draw:.3f});')
    elif t_draw + d_draw > 0.05:
        js.append(f'tl.fromTo("#ln",{{strokeDashoffset:{Ltot - lt:.1f}}},{{strokeDashoffset:0,duration:{t_draw + d_draw:.3f},ease:"none"}},0);')
    labels = {round(y, 1): t for y, t in ev.get("labels", [])}
    r_ = 21 * f
    for k, (x, y, yr, v) in enumerate(pts):
        ti = 0.0 if yr <= frm else t_draw + d_draw * (len_at(yr) - l0) / max(Ltot - l0, 1)
        b.append(f'<div id="dt{k}" style="position:absolute;left:{x - r_:.0f}px;top:{y - r_:.0f}px;width:{2 * r_:.0f}px;height:{2 * r_:.0f}px;border-radius:{r_:.0f}px;background:{RED};'
                 f'border:{6 * f:.0f}px solid #f3ead6"></div>')
        if yr > frm and ti >= 0: js.append(f'tl.fromTo("#dt{k}",{{scale:.001}},{{scale:1,duration:POP.dur,ease:POP.ease}},{ti:.3f});')
        lab = labels.get(round(yr, 1))
        if lab:
            b.append(f'<div id="lb{k}" class="din" style="position:absolute;left:{x - 260 * f:.0f}px;top:{y - 150 * f:.0f}px;width:{520 * f:.0f}px;text-align:center;'
                     f'font-size:{104 * f:.0f}px;color:{RED};line-height:1">{esc(lab)}</div>')
            if yr > frm and ti >= 0: js.append(f'tl.fromTo("#lb{k}",{{opacity:0,y:24}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{ti + 0.05:.3f});')
    # era tags pinned above the line
    for k, tg in enumerate(ev.get("tags", [])):
        yr, text, key = tg[0], tg[1], tg[2]
        v = next((vv for (yy, vv) in reversed(NHANES) if yy <= yr), NHANES[0][1])
        # tg[3]: extra lift in px (C4372 H01: the beside panel wraps a tag to two lines, which sat on the end point's label)
        x, y = xa_(yr), ya_(v) - (330 + (k % 2) * 120 + (tg[3] if len(tg) > 3 else 0)) * f
        ti = T(ev, key, 0.0) if key else 0.0
        b.append(f'<div id="tg{k}" style="position:absolute;left:{x - 230 * f:.0f}px;top:{y:.0f}px;width:{460 * f:.0f}px;text-align:center;transform:rotate({-3 + (k % 3) * 3}deg)">'
                 f'<span class="atwb" style="display:inline-block;padding:{14 * f:.0f}px {28 * f:.0f}px;background:#fffaf0;border:{6 * f:.0f}px solid {INK};font-size:{66 * f:.0f}px;color:{INK};'
                 f'box-shadow:0 10px 24px rgba(0,0,0,.18)">{esc(text)}</span></div>')
        if key and ti >= 0: js.append(f'tl.fromTo("#tg{k}",{{opacity:0,y:-60,scale:1.2}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{ti:.3f});')
    gh = ev.get("ghost")
    if gh:
        g0 = gh.get("from", 1978); v0 = next(v for (yy, v) in NHANES if yy >= g0)
        gx0, gy0 = xa_(g0), ya_(v0); gx1, gy1 = xa_(gh.get("to", 2023)), ya_(gh.get("to_v", 9.0))
        cx = (gx0 + gx1) / 2
        b.append(f'<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}"><path id="gh" d="M{gx0:.0f},{gy0:.0f} Q{cx:.0f},{gy0 - 40:.0f} {gx1:.0f},{gy1:.0f}" '
                 f'fill="none" stroke="#5a5044" stroke-width="{10 * f:.0f}" stroke-dasharray="26 22" stroke-linecap="round" opacity="{0 if T(ev, gh.get("at", "ghost"), 0.6) >= 0 else 1}"/></svg>'
                 f'<div id="ghl" class="hand" style="position:absolute;left:{gx1 - 900 * f:.0f}px;top:{gy1 + 30 * f:.0f}px;width:{900 * f:.0f}px;text-align:right;font-size:{78 * f:.0f}px;color:#4a4136">{esc(gh.get("label", "what should happen"))}</div>')
        tg_ = T(ev, gh.get("at", "ghost"), 0.6)
        if tg_ >= 0: js += [f'tl.fromTo("#gh",{{opacity:0}},{{opacity:1,duration:.6}},{tg_:.3f});', f'tl.fromTo("#ghl",{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tg_ + .3:.3f});']
    if ev.get("note"):
        b.append(f'<div id="nt" class="atw" style="position:absolute;left:{X0}px;top:{g["ny"]}px;width:{g["nw"]}px;font-size:{g["ns"]}px;color:#5a5044">{esc(ev["note"])}</div>')
    b.append(f'<div class="atw" style="position:absolute;{g["src"]};color:#6b6155;text-align:{"left" if ev.get("beside") else "right"}">'
             f'{esc(ev.get("source", "CDC/NCHS, NHANES · Health E-Stat 111 (Feb 2026) · ages 20-74, age-adjusted"))}</div>')
    b.append('</div>')
    js.append(f'tl.fromTo("#aw",{{scale:1}},{{scale:1.035,duration:{D:.3f},ease:"none"}},0);')
    return "".join(b), js


# ------------------------------------------------------------------------------------------------ ledger
ROWS = ["The villain", "What they sold you", "Who got paid", "What the line did"]


def _fs(text, w, h):
    n = len(text)
    for fs in (70, 64, 58, 52, 47, 42, 38):
        cpl = max(1, int(w / (fs * 0.62))); lines = -(-n // cpl)
        if lines * fs * 1.18 <= h: return fs
    return 32


def ledger(ev, mock):
    """ev: cols [header, ...], cells [[villain, product, paid, line], ...] (one list per column), col (the column that types in now),
    at {"r0".."r3"} for its rows, red (a column index drawn in red ink), stamp [text, key]."""
    D = ev["dur"]; cols, cells, cur = ev["cols"], ev["cells"], ev.get("col", len(ev["cols"]) - 1)
    n = len(cols); LX, LW = 200, 640; CX0 = LX + LW; CW = (3660 - CX0) / n; HY, HH, RH = 330, 170, 390
    b = [FONTS, '<div id="lw" style="position:absolute;inset:0;transform-origin:50% 48%">', PAPER,
         f'<div class="din" style="position:absolute;left:{LX}px;top:110px;font-size:150px;color:{INK};line-height:1">{esc(ev.get("title", "THE SCORECARD"))}</div>']
    gy1 = HY + HH + RH * 4
    b.append(f'<div style="position:absolute;left:{LX}px;top:{HY + HH}px;width:{3660 - LX}px;height:5px;background:{INK};opacity:.8"></div>')
    for r in range(1, 4):
        b.append(f'<div style="position:absolute;left:{LX}px;top:{HY + HH + RH * r}px;width:{3660 - LX}px;height:3px;background:{INK};opacity:.28"></div>')
    for c in range(n + 1):
        x = CX0 + CW * c - (LW if c == 0 else 0) * 0
        b.append(f'<div style="position:absolute;left:{CX0 + CW * c:.0f}px;top:{HY}px;width:3px;height:{gy1 - HY}px;background:{INK};opacity:{.5 if c == 0 else .22}"></div>')
    js = []
    ra = (ev.get("at_t") or {}) if cur < 0 else {}   # the empty scorecard (col -1): r0..r3 write the row labels in
    for r, lab in enumerate(ROWS):
        b.append(f'<div id="rl{r}" class="din" style="position:absolute;left:{LX}px;top:{HY + HH + RH * r + 40}px;width:{LW - 40}px;font-size:84px;line-height:1.02;color:{INK}">{esc(lab.upper())}</div>')
        if f"r{r}" in ra: js.append(f'tl.fromTo("#rl{r}",{{clipPath:"inset(0% 100% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:.5,ease:"none"}},{ra[f"r{r}"]:.3f});')
    for c, hd in enumerate(cols):
        x = CX0 + CW * c; past, now = c < cur, c == cur
        ink = RED if ev.get("red") == c else INK
        op = .82 if past else 1
        hdcls = "din"
        b.append(f'<div id="hd{c}" style="position:absolute;left:{x:.0f}px;top:{HY}px;width:{CW:.0f}px;height:{HH}px;display:flex;align-items:center;justify-content:center">'
                 + (f'<div id="hm{c}" style="position:absolute;left:18px;right:18px;top:38px;bottom:38px;background:{YEL};opacity:.85;transform-origin:0 50%"></div>' if now else "")
                 + f'<div class="{hdcls}" style="position:relative;font-size:{96 if len(hd) <= 6 else 72}px;color:{ink};opacity:{op if c <= cur else .25}">{esc(hd)}</div></div>')
        if now: js.append(f'tl.fromTo("#hm{c}",{{scaleX:.001}},{{scaleX:1,duration:SLIDE.dur,ease:SLIDE.ease}},.15);')
        if c > cur: continue
        for r in range(4):
            text = cells[c][r] if r < len(cells[c]) else ""
            if not text: continue
            fs = _fs(text, CW - 60, RH - 70)
            b.append(f'<div id="c{c}_{r}" class="atws" style="position:absolute;left:{x + 30:.0f}px;top:{HY + HH + RH * r + 34}px;width:{CW - 60:.0f}px;height:{RH - 60}px;'
                     f'font-size:{fs}px;line-height:1.16;color:{ink};opacity:{op};text-transform:uppercase">{esc(text)}</div>')
            if now:
                t = T(ev, f"r{r}", 0.5 + 0.6 * r)
                js.append(f'tl.fromTo("#c{c}_{r}",{{clipPath:"inset(0% 100% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:.55,ease:"none"}},{t:.3f});')
    st = ev.get("stamp")
    if st:
        text, key = st[0], st[1]; t = T(ev, key, D - 1.2)
        b.append(f'<div id="stp" style="position:absolute;left:{W // 2 - 1500}px;top:{HY + HH + RH * 1.3:.0f}px;width:3000px;text-align:center;transform:rotate(-6deg);opacity:0">'
                 f'<span class="din" style="display:inline-block;padding:30px 70px;border:14px double {RED};color:{RED};font-size:150px;letter-spacing:6px;'
                 f'background:rgba(243,234,214,.55);mix-blend-mode:multiply">{esc(text)}</span></div>')
        js.append(f'tl.fromTo("#stp",{{opacity:0,scale:1.6}},{{opacity:.92,scale:1,duration:.22,ease:"power4.in"}},{t:.3f});')
    if ev.get("source"):
        b.append(f'<div class="atw" style="position:absolute;right:140px;top:2050px;font-size:40px;color:#6b6155">{esc(ev["source"])}</div>')
    b.append('</div>')
    z = float(ev.get("zoom", 1.42 if cur > 0 else 1.0)) if cur >= 0 else 1.0
    if z > 1.0:   # start on this era's column at a size a phone can read, then pull back to the whole scorecard
        cx, cy = CX0 + CW * (cur + 0.5), (HY + gy1) / 2
        back = T(ev, "back", max([T(ev, f"r{r}", 0) for r in range(4)] + [0]) + 0.9)
        js += [f'tl.set("#lw",{{transformOrigin:"{cx:.0f}px {cy:.0f}px",scale:{z}}},0);',
               f'tl.to("#lw",{{scale:1.0,duration:1.1,ease:SOFT.ease}},{back:.3f});']
    else:
        js.append(f'tl.fromTo("#lw",{{scale:1.0}},{{scale:1.03,duration:{D:.3f},ease:"none"}},0);')
    return "".join(b), js


# ------------------------------------------------------------------------------------------------ stamp (on his frame)
def stamp(ev, mock):
    """A red rubber stamp beside his face: ev text (\\n for two lines), sub (small typed line under it), side L|R, at {"s": key}."""
    D = ev["dur"]; side = ev.get("side", "L"); x = 260 if side == "L" else 2380
    lines = esc(ev["text"]).replace("\n", "<br>")
    b = (FONTS + f'<div id="sw" style="position:absolute;left:{x}px;top:{ev.get("y", 640)}px;width:1200px;text-align:center;transform:rotate({-7 if side == "L" else 6}deg);opacity:0">'
         f'<div class="din" style="display:inline-block;padding:26px 54px 18px;border:12px solid {RED};border-radius:10px;color:{RED};font-size:{ev.get("size", 150)}px;'
         f'line-height:1;letter-spacing:4px;background:rgba(255,248,235,.82);box-shadow:0 18px 50px rgba(0,0,0,.35)">{lines}</div>'
         + (f'<div class="atwb" style="margin-top:24px;font-size:54px;color:#fff;text-shadow:0 4px 18px rgba(0,0,0,.9)">{esc(ev["sub"])}</div>' if ev.get("sub") else "")
         + '</div>')
    t = T(ev, "s", 0.1)
    js = [f'tl.fromTo("#sw",{{opacity:0,scale:1.5}},{{opacity:1,scale:1,duration:.2,ease:"power4.in"}},{t:.3f});',
          f'tl.to("#sw",{{opacity:0,duration:.25}},{max(t + 0.5, D - 0.3):.3f});']
    return b, js


# ------------------------------------------------------------------------------------------------ ribbon
def ribbon(ev, mock):
    """A paper timeline ribbon across the frame. ev stops [[label, tag], ...]; at {"go": key} the stops land one by one;
    mode "villains" (default): the tags flick along it, "strike" index gets a red pen line at at["strike"];
    mode "map": the chapter map, stop ev["lit"] lights at at["lit"] (the others stay pale)."""
    D = ev["dur"]; st = ev["stops"]; n = len(st); x0, x1, ly = 380, 3460, 1120
    X = lambda k: x0 + (x1 - x0) * (k / max(n - 1, 1))
    at = ev.get("at_t") or {}; tgo = at.get("go", 0.15); lit = ev.get("lit")
    b = [FONTS, '<div id="rw" style="position:absolute;inset:0;transform-origin:50% 52%">', PAPER,
         f'<div id="rb" style="position:absolute;left:{x0 - 120}px;top:{ly - 70}px;width:{x1 - x0 + 240}px;height:140px;background:#f6efdf;'
         f'border-top:5px solid {INK};border-bottom:5px solid {INK};box-shadow:0 18px 40px rgba(0,0,0,.18);transform-origin:0 50%"></div>']
    if ev.get("title"):
        b.append(f'<div class="din" style="position:absolute;left:0;width:{W}px;text-align:center;top:300px;font-size:150px;color:{INK}">{esc(ev["title"])}</div>')
    js = [f'tl.fromTo("#rb",{{scaleX:.001}},{{scaleX:1,duration:.7,ease:SLIDE.ease}},{max(0.0, tgo - 0.4):.3f});']
    step = float(ev.get("step", min(0.32, max(0.12, (D - tgo - 1.0) / max(n, 1)))))
    for k, (lab, tag) in enumerate(st):
        on = (lit is None) or (k == lit) or ev.get("mode") != "map"
        col = RED if (lit is not None and k == lit) else INK
        b.append(f'<div id="rs{k}" style="position:absolute;left:{X(k) - 260:.0f}px;top:{ly - 52}px;width:520px;text-align:center">'
                 f'<span class="din" style="font-size:{92 if len(lab) <= 6 else 64}px;color:{col};opacity:{1 if on else .35}">{esc(lab)}</span></div>'
                 f'<div id="rd{k}" style="position:absolute;left:{X(k) - 16:.0f}px;top:{ly + 82}px;width:32px;height:32px;border-radius:16px;background:{col}"></div>')
        js.append(f'tl.fromTo(["#rs{k}","#rd{k}"],{{opacity:0,y:20}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tgo + step * k:.3f});')
        if tag:
            b.append(f'<div id="rt{k}" style="position:absolute;left:{X(k) - 280:.0f}px;top:{ly + 160 + (k % 2) * 150}px;width:560px;text-align:center;transform:rotate({-4 + (k % 3) * 4}deg)">'
                     f'<span class="atwb" style="display:inline-block;padding:16px 30px;background:#fffaf0;border:6px solid {INK};font-size:{70 if len(tag) <= 10 else 56}px;color:{INK};'
                     f'box-shadow:0 12px 26px rgba(0,0,0,.2)">{esc(tag)}</span></div>')
            js.append(f'tl.fromTo("#rt{k}",{{opacity:0,y:-50,scale:1.25}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{tgo + step * k + 0.1:.3f});')
    if "strike" in ev:
        k = ev["strike"]; ts = at.get("strike", D - 0.9)
        b.append(f'<div id="rx" style="position:absolute;left:{X(k) - 300:.0f}px;top:{ly + 230 + (k % 2) * 150}px;width:600px;height:18px;background:{RED};'
                 f'transform:rotate(-8deg);transform-origin:0 50%;border-radius:9px;mix-blend-mode:multiply"></div>')
        js.append(f'tl.fromTo("#rx",{{scaleX:.001}},{{scaleX:1,duration:.35,ease:"power2.out"}},{ts:.3f});')
    if lit is not None and "lit" in at:
        b.append(f'<div id="rl" style="position:absolute;left:{X(lit) - 120:.0f}px;top:{ly - 120}px;width:240px;height:240px;border-radius:120px;border:10px solid {RED};opacity:0"></div>')
        js.append(f'tl.fromTo("#rl",{{opacity:0,scale:1.6}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{at["lit"]:.3f});')
    b.append('</div>')
    js.append(f'tl.fromTo("#rw",{{scale:1}},{{scale:1.03,duration:{D:.3f},ease:"none"}},0);')
    return "".join(b), js


# ------------------------------------------------------------------------------------------------ jtitle
def jtitle(ev, mock):
    """The title card: big type on a dark sheet with film grain, a red pen line drawn under the last words, era years drifting below."""
    D = ev["dur"]
    yrs = "".join(f'<span class="atw" style="margin:0 46px">{esc(y)}</span>' for y in ev.get("years", ["1961", "1992", "2004", "2018", "2020s", "2025"]))
    b = (FONTS + '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 42%,#2a241c 0%,#14110d 60%,#080706 100%)"></div>'
         '<div id="tw" style="position:absolute;inset:0;transform-origin:50% 46%">'
         f'<div id="t1" class="din" style="position:absolute;left:0;width:{W}px;text-align:center;top:560px;font-size:420px;line-height:1;color:#f3ead6;letter-spacing:8px">{esc(ev["line1"])}</div>'
         f'<div id="t2" class="din" style="position:absolute;left:0;width:{W}px;text-align:center;top:1000px;font-size:420px;line-height:1;color:#f3ead6;letter-spacing:8px">{esc(ev["line2"])}</div>'
         f'<div id="tu" style="position:absolute;left:{W // 2 - 1080}px;top:1450px;width:2160px;height:26px;background:{RED};border-radius:13px;transform-origin:0 50%"></div>'
         f'<div id="ty" style="position:absolute;left:0;width:{W}px;text-align:center;top:1620px;font-size:70px;color:#b8ab93;white-space:nowrap">{yrs}</div></div>')
    js = ['tl.fromTo("#t1",{opacity:0,y:40},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0.05);',
          'tl.fromTo("#t2",{opacity:0,y:40},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0.3);',
          'tl.fromTo("#tu",{scaleX:.001},{scaleX:1,duration:.55,ease:"power2.out"},0.75);',
          f'tl.fromTo("#ty",{{opacity:0,x:120}},{{opacity:.9,x:-120,duration:{max(D, 1):.3f},ease:"none"}},0.4);',
          f'tl.fromTo("#tw",{{scale:1}},{{scale:1.05,duration:{D:.3f},ease:"none"}},0);']
    return b, js


# ------------------------------------------------------------------------------------------------ jchapter
ERA_STOPS = ["1961", "1992", "2004", "2018", "2020s", "2025"]


def jchapter(ev, mock):
    """The era date card (Johnny Harris M13, a replay-peak type): the year huge on film black with a soft glow, one typed line under it,
    a red pen line, and the six eras along the foot with this one lit. Chapters without a year ("The real reason") set the title big.
    ev title "1961 · Fat is the villain" (or "The real reason"), n (the chapter number)."""
    D = ev["dur"]; title = ev.get("title", ""); n = ev.get("n", 0)
    big, small = (title.split(" · ", 1) + [""])[:2] if " · " in title else (title, ev.get("sub", ""))
    era = big if big in ERA_STOPS else None
    fs = 520 if len(big) <= 5 else (380 if len(big) <= 9 else (300 if len(big) <= 15 else 240))
    b = [FONTS, '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 44%,#2a241c 0%,#14110d 58%,#070605 100%)"></div>',
         '<div id="cw" style="position:absolute;inset:0;transform-origin:50% 45%">',
         f'<div id="cy" class="din" style="position:absolute;left:0;width:{W}px;text-align:center;top:{(860 if small else 960) - fs // 2}px;font-size:{fs}px;line-height:1;'
         f'color:#f3ead6;letter-spacing:{10 if era else 6}px;text-shadow:0 0 70px rgba(255,214,150,.22)">{esc(big.upper())}</div>']
    js = ['tl.fromTo("#cy",{opacity:0,scale:1.06},{opacity:1,scale:1,duration:.35,ease:"power2.out"},0.0);']
    if small:
        b.append(f'<div id="cs" class="atw" style="position:absolute;left:0;width:{W}px;text-align:center;top:{860 + fs // 2 + 70}px;font-size:110px;color:#e6dcc6">'
                 f'<span id="csi" style="display:inline-block">{esc(small)}</span></div>'
                 f'<div id="cu" style="position:absolute;left:{W // 2 - 700}px;width:1400px;top:{860 + fs // 2 + 230}px;height:16px;background:{RED};border-radius:8px;transform-origin:0 50%"></div>')
        js += ['tl.fromTo("#csi",{clipPath:"inset(0% 100% 0% 0%)"},{clipPath:"inset(0% 0% 0% 0%)",duration:.6,ease:"none"},0.35);',
               'tl.fromTo("#cu",{scaleX:.001},{scaleX:1,duration:.45,ease:"power2.out"},0.95);']
    else:   # a chapter after the eras: PART N typed above, the red pen line under the title
        b.append(f'<div id="ck" class="atw" style="position:absolute;left:0;width:{W}px;text-align:center;top:{960 - fs // 2 - 190}px;font-size:84px;letter-spacing:14px;color:#b8ab93">'
                 f'<span id="cki" style="display:inline-block">PART {n}</span></div>'
                 f'<div id="cu" style="position:absolute;left:{W // 2 - 900}px;width:1800px;top:{960 + fs // 2 + 60}px;height:18px;background:{RED};border-radius:9px;transform-origin:0 50%"></div>')
        js += ['tl.fromTo("#cki",{clipPath:"inset(0% 100% 0% 0%)"},{clipPath:"inset(0% 0% 0% 0%)",duration:.45,ease:"none"},0.2);',
               'tl.fromTo("#cu",{scaleX:.001},{scaleX:1,duration:.5,ease:"power2.out"},0.6);']
    if True:   # the eras along the foot (the chapter map, so the viewer knows where they are): this era lit, or all six passed and this chapter lit at the end
        stops = ERA_STOPS + ([] if era else [big.upper()])
        x0, x1, y = (760, 3080, 1900) if era else (420, 3420, 1900)
        b.append(f'<div style="position:absolute;left:{x0}px;top:{y}px;width:{x1 - x0}px;height:4px;background:rgba(243,234,214,.25)"></div>')
        for k, st in enumerate(stops):
            x = x0 + (x1 - x0) * k / (len(stops) - 1); on = (st == era) if era else (k == len(stops) - 1)
            b.append(f'<div style="position:absolute;left:{x - 13:.0f}px;top:{y - 11}px;width:26px;height:26px;border-radius:13px;background:{RED if on else "rgba(243,234,214,.45)"}"></div>'
                     f'<div class="atw" style="position:absolute;left:{x - 330:.0f}px;width:660px;text-align:center;top:{y + 36}px;font-size:56px;white-space:nowrap;color:{"#f3ead6" if on else "rgba(243,234,214,.45)"}">{esc(st)}</div>')
            if on:
                b.append(f'<div id="cr" style="position:absolute;left:{x - 44:.0f}px;top:{y - 42}px;width:88px;height:88px;border-radius:44px;border:7px solid {RED}"></div>')
                js.append('tl.fromTo("#cr",{opacity:0,scale:1.8},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},0.5);')
    b.append('</div>')
    js.append(f'tl.fromTo("#cw",{{scale:1}},{{scale:1.03,duration:{D:.3f},ease:"none"}},0);')
    return "".join(b), js


FN = {"anchor": anchor, "ledger": ledger, "stamp": stamp, "ribbon": ribbon, "jtitle": jtitle, "jchapter": jchapter}
TYPES = set(FN)
COVER = {"anchor", "ledger", "ribbon", "jtitle", "jchapter"}   # full-frame (stamp sits on his face)


def body(ev, mock):
    return FN[ev["type"]](ev, mock)


def settle(ev):
    ts = list((ev.get("at_t") or {}).values()) or [0.6]
    return min(ev["dur"] - 0.1, max(ts) + 1.4)
