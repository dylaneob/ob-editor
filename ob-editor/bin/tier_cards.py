#!/usr/bin/env python3
"""HyperFrames composition for OB's tier-list reels (Dan Martell "RANKED" reference, IG DdO1aQtCPGG).

  python3 tier_cards.py EDL.json PROJECT_DIR NAME [--mock] [--captions]

Layers over the graded cut (1080x1920; the cut already has the tier framing and the blur below the board):
  - white rounded title box at the top, black sans, 2 lines (frame 1 shows it with the empty board)
  - the board at y 860-1510: 6 TierMaker rows (label cell 128 px, dark row, white lowercase items), or for
    the cardio take a "walking vs" scoreboard (walking cell turns green with a check on his answer,
    a small "longevity" tag where he credits the other cardio)
  - each item pops as a dark chip over his chest when he names it, then springs into its row slot on the
    tier word (cardio: the opponent slides into its row as he starts his answer). Slots are laid out with
    PIL metrics of the same font, so every item lands where the finished board has it.
  - a CTA chip on the comment line
  - --captions: 3-word captions above the board, hidden while a chip is up (OB's call; default off)
Motion uses closed-form springs only (POP/SNAP/SOFT/STAMP, same constants as lecture_cards.py).
--mock swaps the video for per-shot stills (tier_stills.py) and writes NAME_layout.json with the mock times.
"""
import html, json, os, re, sys
from PIL import ImageFont

W, H = 1080, 1920
FONTS = os.path.expanduser("~/ob-editor/fonts")
BOARD_TOP, BOARD_BOT, NROWS, SEP = 860, 1510, 6, 2
ROW_H = (BOARD_BOT - BOARD_TOP - SEP * (NROWS - 1)) / NROWS
LABEL_W = 128
ITEM_PX, ITEM_GAP, BODY_PAD, WRAP_PX = 38, 34, 30, 35
CHIP_SCALE, CHEST = 1.3, (540, 812)          # chip size over his chest, and its centre (between chin and board)
ROW_BG, INK = "#1b1b1b", "#111111"
TIER_COLORS = {"S": "#FF7F7F", "A": "#FFBF7F", "B": "#FFDF7F", "C": "#FFFF7F", "D": "#BFFF7F", "F": "#7FFF7F"}
HERO_W, WIN_GREEN, TAG_BG = 250, "#4ADE80", "#FFDF7F"
OPT_TOP, OPT_H, OPT_W, OPT_X = 856, 128, 468, 44      # this-or-that cards on his chest, left = champion, right = challenger
CAP_TOP_BESIDE = 836                                   # captions on his chest when the labels sit beside his head
esc = lambda s: html.escape(s or "", quote=True)

SPRINGS = r"""
function spring(k, c, m = 1, v0 = 0) {
  const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m)); let f, T;
  if (z < 1) { const wd = w0 * Math.sqrt(1 - z * z);
    f = t => 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0 - v0) / wd) * Math.sin(wd * t)); T = Math.log(1000) / (z * w0); }
  else { f = t => 1 - Math.exp(-w0 * t) * (1 + (w0 - v0) * t); T = 1.6 * Math.log(1000) / w0; }
  return { dur: +T.toFixed(3), ease: p => (p >= 1 ? 1 : f(p * T)) };
}
const POP = spring(320, 17), SNAP = spring(260, 22), SOFT = spring(170, 26), STAMP = spring(420, 16);
"""

CSS = f"""
@font-face {{ font-family: 'AvDB'; src: url('../assets/fonts/AvenirNext-DemiBold.ttf'); }}
@font-face {{ font-family: 'AvM'; src: url('../assets/fonts/AvenirNext-Medium.ttf'); }}
@font-face {{ font-family: 'AvH'; src: url('../assets/fonts/AvenirNext-Heavy.ttf'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
.media {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.title {{ position: absolute; left: 50%; top: 112px; transform: translateX(-50%); background: #fff; color: {INK}; border-radius: 26px;
          padding: 14px 36px 16px; font-family: 'AvDB'; font-size: 56px; line-height: 1.12; text-align: center; white-space: nowrap;
          letter-spacing: -0.3px; box-shadow: 0 10px 30px rgba(0,0,0,.18); }}
.board {{ position: absolute; left: 0; top: {BOARD_TOP}px; width: {W}px; height: {BOARD_BOT - BOARD_TOP}px; background: #000; }}
.trow {{ position: absolute; left: 0; width: {W}px; height: {ROW_H:.3f}px; background: {ROW_BG}; }}
.lab {{ position: absolute; left: 0; top: 0; width: {LABEL_W}px; height: 100%; display: flex; align-items: center; justify-content: center;
        font-family: 'AvDB'; font-size: 50px; color: {ROW_BG}; }}
.hero {{ position: absolute; left: 0; top: 0; width: {HERO_W}px; height: 100%; background: #e6e6e6; }}
.hero .win {{ position: absolute; inset: 0; background: {WIN_GREEN}; opacity: 0; }}
.hero .ht {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 10px;
             font-family: 'AvDB'; font-size: 40px; color: {ROW_BG}; }}
.hero .chk {{ width: 34px; height: 34px; display: inline-block; }}
.hero .chk svg {{ width: 34px; height: 34px; display: block; }}
.vs {{ position: absolute; font-family: 'AvM'; font-size: 32px; color: #9a9a9a; }}
.it {{ position: absolute; font-family: 'AvDB'; font-size: {ITEM_PX}px; line-height: 1; color: #fff; white-space: nowrap;
       transform-origin: 50% 50%; opacity: 0; }}
.it .bg {{ position: absolute; inset: -14px -24px; background: {ROW_BG}; border-radius: 16px; opacity: .95;
           box-shadow: 0 12px 34px rgba(0,0,0,.38); }}
.it .tx {{ position: relative; }}
.tag {{ position: absolute; font-family: 'AvDB'; font-size: 30px; line-height: 1; color: {ROW_BG}; background: {TAG_BG};
        padding: 7px 15px 6px; border-radius: 999px; opacity: 0; transform-origin: 0% 50%; white-space: nowrap; }}
.cta {{ position: absolute; left: 50%; translate: -50% 0; top: {CHEST[1] - 38}px; background: #fff; color: {INK};
        border-radius: 18px; padding: 14px 30px 12px; font-family: 'AvDB'; font-size: 50px; line-height: 1; white-space: nowrap;
        box-shadow: 0 14px 40px rgba(0,0,0,.35); opacity: 0; }}
.cta b {{ font-family: 'AvH'; letter-spacing: .5px; }}
.tot {{ position: absolute; left: 50%; top: 112px; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; gap: 10px; }}
.tot span {{ background: #fff; color: {INK}; border-radius: 20px; padding: 9px 28px 12px; font-family: 'AvDB'; font-size: 54px; line-height: 1.1;
             white-space: nowrap; letter-spacing: -0.3px; box-shadow: 0 10px 30px rgba(0,0,0,.18); }}
.opt {{ position: absolute; top: {OPT_TOP}px; width: {OPT_W}px; height: {OPT_H}px; border-radius: 28px; background: {ROW_BG}; border: 5px solid #444;
        display: flex; align-items: center; justify-content: center; font-family: 'AvH'; font-size: 54px; color: #fff; white-space: nowrap;
        box-shadow: 0 18px 46px rgba(0,0,0,.42); transform-origin: 50% 50%; }}
.opt .ring {{ position: absolute; inset: -5px; border: 5px solid {WIN_GREEN}; border-radius: 28px; opacity: 0; }}
.opt .ok {{ position: absolute; left: -24px; top: -30px; width: 72px; height: 72px; border-radius: 50%; background: {WIN_GREEN};
            display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 22px rgba(0,0,0,.35); opacity: 0; }}
.opt .ok svg {{ width: 40px; height: 40px; }}
.orb {{ position: absolute; left: {W / 2 - 38}px; top: {OPT_TOP + OPT_H / 2 - 38}px; width: 76px; height: 76px; border-radius: 50%; background: #fff;
        color: {INK}; display: flex; align-items: center; justify-content: center; font-family: 'AvH'; font-size: 30px; z-index: 3;
        box-shadow: 0 8px 22px rgba(0,0,0,.3); }}
.ttag {{ position: absolute; translate: -50% 0; top: {OPT_TOP + OPT_H + 18}px; font-family: 'AvDB'; font-size: 32px; line-height: 1; color: {ROW_BG}; background: {TAG_BG};
         padding: 8px 18px 7px; border-radius: 999px; opacity: 0; white-space: nowrap; transform-origin: 50% 0%; }}
.lbl {{ position: absolute; translate: -50% -50%; color: #fff; font-family: 'AvH'; line-height: 1; white-space: nowrap; transform-origin: 50% 50%;
        text-shadow: 0 0 10px rgba(0,0,0,.55), 0 3px 0 rgba(0,0,0,.88), 3px 0 0 rgba(0,0,0,.88), -3px 0 0 rgba(0,0,0,.88), 0 -3px 0 rgba(0,0,0,.88),
                     2px 2px 0 rgba(0,0,0,.88), -2px -2px 0 rgba(0,0,0,.88), 2px -2px 0 rgba(0,0,0,.88), -2px 2px 0 rgba(0,0,0,.88); }}
.gchk {{ position: absolute; translate: -50% -50%; width: 84px; height: 84px; opacity: 0; transform-origin: 50% 50%; }}
.gchk svg {{ width: 84px; height: 84px; display: block; overflow: visible; }}
.cap {{ position: absolute; left: 60px; right: 60px; top: {CHEST[1] - 40}px; text-align: center; font-family: 'AvH'; font-size: 58px;
        line-height: 1.05; color: #fff; opacity: 0;
        text-shadow: 0 0 6px rgba(0,0,0,.95), 0 3px 0 rgba(0,0,0,.9), 3px 0 0 rgba(0,0,0,.9), -3px 0 0 rgba(0,0,0,.9), 0 -3px 0 rgba(0,0,0,.9); }}
"""

CHECK_SVG = ('<svg viewBox="0 0 34 34"><polyline points="6,18 14,26 28,9" fill="none" stroke="#0b2e13" stroke-width="5.5" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def font(name, px): return ImageFont.truetype(os.path.join(FONTS, name), px)


def row_top(k): return BOARD_TOP + k * (ROW_H + SEP)


def text_w(txt, px=ITEM_PX, name="AvenirNext-DemiBold.ttf"): return font(name, px).getlength(txt)


def row_layout(items, k):
    """Slots (x, y, w, px) for one tier row: one line at 38 px while it fits, else two balanced lines at 35 px."""
    x0, x1 = LABEL_W + BODY_PAD, W - BODY_PAD
    def width(ws, gap): return sum(ws) + gap * max(0, len(ws) - 1)
    ws = [text_w(s_) for s_ in items]; top = row_top(k); out = {}
    if width(ws, ITEM_GAP) <= x1 - x0:
        lines, px, gap, ys = [list(range(len(items)))], ITEM_PX, ITEM_GAP, [top + (ROW_H - ITEM_PX) / 2]
    else:                                        # two lines: a touch smaller so the row breathes
        px, gap = WRAP_PX, ITEM_GAP - 4; ws = [text_w(s_, px) for s_ in items]; best = None
        for cut in range(1, len(items)):
            a, b = width(ws[:cut], gap), width(ws[cut:], gap)
            if max(a, b) <= x1 - x0 and (best is None or max(a, b) < best[0]): best = (max(a, b), cut)
        if best is None: raise SystemExit(f"row {k} does not fit in two lines: {items}")
        lines = [list(range(best[1])), list(range(best[1], len(items)))]
        y1 = top + (ROW_H - (2 * px + 10)) / 2; ys = [y1, y1 + px + 10]
    for ln, y in zip(lines, ys):
        x = x0
        for j in ln:
            out[items[j]] = {"x": round(x, 1), "y": round(y, 1), "w": round(ws[j], 1), "row": k, "px": px}
            x += ws[j] + gap
    return out


def tier_layout(final):
    """Final slot of every item, row by row (rows in board order, items in the order they are placed)."""
    slots = {}
    for k, t in enumerate(final): slots.update(row_layout(final[t], k))
    return slots


def to_state(st, f):
    """GSAP transform (x, y, scale) that shows an item sitting at its final slot f as if it were at slot st."""
    return (st["x"] + st["w"] / 2) - (f["x"] + f["w"] / 2), (st["y"] + st["px"] / 2) - (f["y"] + f["px"] / 2), st["px"] / f["px"]


def versus_layout(rows):
    slots, tags = {}, {}
    vs_w = text_w("vs", 32, "AvenirNext-Medium.ttf")
    for k, opp in enumerate(rows):
        top = row_top(k); x = HERO_W + 28
        ox = x + vs_w + 20; w = text_w(opp)
        slots[opp] = {"x": round(ox, 1), "y": round(top + (ROW_H - ITEM_PX) / 2, 1), "w": round(w, 1), "row": k, "vs_x": round(x, 1)}
        tags[k] = {"x": round(ox + w + 22, 1), "y": round(top + (ROW_H - 43) / 2, 1)}
    return slots, tags


SETTLE = {"pop": 0.45, "place": 0.8, "win": 0.6, "tag": 0.65, "cta": 0.75}


def mock_time(spec, i):
    """The moment each shot's mock shows: the last graphic event in the row once it has settled, else mid-row."""
    r = spec["rows"][i]; evs = [e for e in spec["events"] if e["shot"] == i]
    lo, hi = r["edit_in"] + 0.05, r["edit_out"] - 0.03
    t = max(e["edit"] + SETTLE[e["k"]] for e in evs) if evs else (r["edit_in"] + r["edit_out"]) / 2
    return round(min(max(t, lo), hi), 3)


def word_times(spec, islands):
    """Edit time of every caption word: matched to the per-island Whisper words of the row's source span,
    gaps filled by character share between known words. Without islands, character share over the row."""
    import difflib
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
    iw = [w for x in (islands or []) for w in x.get("words", []) if norm(w["w"])]
    out = []
    for r in spec["rows"]:
        cw = r["caption"].split(); n = len(cw); T = [None] * n
        src = [w for w in iw if r["src_in"] - 0.08 <= w["t0"] <= r["src_out"]]
        sm = difflib.SequenceMatcher(None, [norm(w) for w in cw], [norm(w["w"]) for w in src], autojunk=False)
        for a, b, size in sm.get_matching_blocks():
            for k in range(size): T[a + k] = max(r["src_in"], src[b + k]["t0"])
        anchors = [(-1, r["src_in"] + 0.02)] + [(i, t) for i, t in enumerate(T) if t is not None] + [(n, r["src_out"] - 0.08)]
        for (i0, t0), (i1, t1) in zip(anchors, anchors[1:]):
            gap = list(range(i0 + 1, i1))
            if not gap: continue
            seq = ([i0] if i0 >= 0 else []) + gap     # the known word before the gap takes its share first
            lens = [max(2, len(norm(cw[i]))) for i in seq]; span = max(0.0, t1 - t0); acc = 0.0
            for i, L in zip(seq, lens):
                if i != i0: T[i] = t0 + span * acc / sum(lens)
                acc += L
        for i in range(1, n): T[i] = max(T[i], T[i - 1] + 0.04)            # monotonic
        out.append([round(r["edit_in"] + min(t, r["src_out"]) - r["src_in"], 3) for t in T])
    return out


def cap_text(words):
    """Lowercase like the reference items, except tier letters and acronyms (S, A, HIIT, I); no commas or periods."""
    out = []
    for w in words:
        core = re.sub(r"[^A-Za-z]", "", w)
        w = w if (core and core.isupper()) else w.lower()
        out.append(re.sub(r"[.,;:!]+$", "", w))
    return " ".join(out)


def caption_pages(rows, times=None):
    """3-word pages; a page shorter than 0.3 s takes the next page's words with it, so nothing flickers."""
    pages = []
    for ri, r in enumerate(rows):
        words = r["caption"].split()
        if not words: continue
        if times: tw = times[ri]
        else:
            dur = r["edit_out"] - r["edit_in"] - 0.16
            lens = [max(2, len(re.sub(r"[^\w']", "", w))) for w in words]; tot = sum(lens)
            t = r["edit_in"] + 0.06; tw = []
            for L in lens: tw.append(t); t += dur * L / tot
        s, n = 0, len(words)
        punct = lambda k: bool(re.search(r"[.,?!;:]$", words[k - 1]))
        while s < n:
            if n - s <= 4: e = n                                  # 4 or fewer left: one page, no orphan word
            else:
                e = next((k for k in (s + 3, s + 2, s + 4) if punct(k)), s + 3)   # end on a comma or period when one is near
                if n - e == 1: e += 1
            while e < n and (tw[e] - tw[s]) < 0.3 and e - s < 5: e += 1
            end = tw[e] if e < n else r["edit_out"]
            pages.append({"text": cap_text(words[s:e]), "t0": tw[s], "t1": end}); s = e
    return pages


CHECK_WHITE = ('<svg viewBox="0 0 34 34"><polyline points="6,18 14,26 28,9" fill="none" stroke="#ffffff" stroke-width="5.5" '
               'stroke-linecap="round" stroke-linejoin="round"/></svg>')


CHECK_GREEN = ('<svg viewBox="0 0 34 34"><polyline points="5,18 13,26 29,8" fill="none" stroke="rgba(0,0,0,.6)" stroke-width="9.5" '
               'stroke-linecap="round" stroke-linejoin="round"/><polyline points="5,18 13,26 29,8" fill="none" stroke="#4ADE80" stroke-width="6" '
               'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def doc_html(D, name, mock, els, js):
    if mock:
        bg = f'<img id="bg" class="media" src="../assets/stills/{name}_000.jpg"/>'
    else:
        bg = (f'<video id="aroll" class="media clip" src="../assets/{name}_cut.mp4" muted playsinline data-start="0" '
              f'data-duration="{D:.3f}" data-track-index="0"></video>')
    return f"""<!doctype html>
<html lang="en" data-resolution="portrait"><head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script><style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="{W}" data-height="{H}">
<div>{bg}</div>
{chr(10).join(els)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
{SPRINGS}
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""


def card_label(item): return item if item.isupper() else item[:1].upper() + item[1:]


LBL_CY, LBL_XL, LBL_XR, LBL_MAXW, LBL_PX = 470, 150, 908, 280, 46   # "beside" layout: labels left and right of his head, sized to clear the widest punch-in


def build_tot(spec, name, mock, captions=False, times=None):
    """"This or that" (OB's references 10-16: @joeymiuccio leg edition, @notcoledasilva, @pivotalconversations).
    Stacked white title boxes; the champion (Walking) stays on the left for the whole reel and each challenger swaps
    in on the right on its word; a green check lands on his pick; a longevity tag goes under the challenger where he
    credits it; everything clears for the CTA chip. Round 1 is on screen from frame 1.
    board.layout "beside" (OB's pick 10-16, Joey's look): white outlined labels left and right of his head, a green
    check above the pick. "chest": dark cards on his chest with an "or" medallion (@notcoledasilva)."""
    rows, evs, D, board = spec["rows"], spec["events"], spec["duration"], spec["board"]
    beside = board.get("layout") == "beside"
    js, els, windows = [], [], []
    els.append('<div class="tot" id="title">' + "".join(f"<span>{esc(l)}</span>" for l in spec["board_title"].split("\n")) + "</div>")
    ev = sorted(evs, key=lambda e: e["edit"]); pops = [e for e in ev if e["k"] == "pop"]
    def lbl_px(text): return min(LBL_PX, int(LBL_PX * LBL_MAXW / max(1.0, text_w(text, LBL_PX, "AvenirNext-Heavy.ttf"))))
    if beside:
        hp = lbl_px(board["hero"])
        els.append(f'<div class="lbl" id="hero" style="left:{LBL_XL}px;top:{LBL_CY}px;font-size:{hp}px">{esc(board["hero"])}</div>')
        els.append(f'<div class="gchk" id="ok" style="left:{LBL_XL}px;top:{LBL_CY - hp / 2 - 50:.0f}px">{CHECK_GREEN}</div>')
    else:
        els.append(f'<div class="opt" id="hero" style="left:{OPT_X}px"><div class="ring" id="ring"></div><div class="ok" id="ok">{CHECK_WHITE}</div>{esc(board["hero"])}</div>')
    for n, e in enumerate(pops):
        vis = "" if n == 0 else ";opacity:0"          # round 1 is the hook: visible on frame 1 by its own style (a set at 0 never renders frame 0)
        if beside:
            els.append(f'<div class="lbl" id="ch{n}" style="left:{LBL_XR}px;top:{LBL_CY}px;font-size:{lbl_px(card_label(e["item"]))}px{vis}">{esc(card_label(e["item"]))}</div>')
        else:
            els.append(f'<div class="opt" id="ch{n}" style="left:{W - OPT_X - OPT_W}px{vis}">{esc(card_label(e["item"]))}</div>')
    if not beside: els.append('<div class="orb" id="orb">or</div>')
    rnd = lambda t: max([n for n, p in enumerate(pops) if p["edit"] <= t + 1e-6] + [0])
    tags = {}
    for e in ev:
        t = e["edit"]
        if e["k"] == "pop":
            n = pops.index(e)
            if n == 0:
                js.append(f'tl.fromTo("#ch0",{{scale:1.08}},{{scale:1,duration:POP.dur,ease:POP.ease}},{t:.3f});')
            else:
                start = rows[e["shot"]]["edit_in"]
                if not beside: js.append(f'tl.to("#ring",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{start:.3f});')
                js.append(f'tl.to("#ok",{{opacity:0,scale:.4,duration:SOFT.dur,ease:SOFT.ease}},{start:.3f});')
                js.append(f'tl.to("#ch{n - 1}",{{opacity:0,scale:.8,duration:SOFT.dur,ease:SOFT.ease}},{t - 0.06:.3f});')
                if n - 1 in tags: js.append(f'tl.to("#tt{n - 1}",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{t - 0.06:.3f});')
                js.append(f'tl.fromTo("#ch{n}",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{t:.3f});')
        elif e["k"] == "win":
            if not beside: js.append(f'tl.fromTo("#ring",{{opacity:0}},{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{t:.3f});')
            js.append(f'tl.fromTo("#ok",{{opacity:0,scale:.2}},{{opacity:1,scale:1,duration:STAMP.dur,ease:STAMP.ease}},{t + 0.04:.3f});')
        elif e["k"] == "tag":
            n = rnd(t); tags[n] = True
            x, y = (LBL_XR, LBL_CY + 40) if beside else (W - OPT_X - OPT_W / 2, OPT_TOP + OPT_H + 18)
            els.append(f'<div class="ttag" id="tt{n}" style="left:{x}px;top:{y}px">{esc(e["text"])}</div>')
            js.append(f'tl.fromTo("#tt{n}",{{opacity:0,scale:1.6}},{{opacity:1,scale:1,duration:STAMP.dur,ease:STAMP.ease}},{t:.3f});')
        elif e["k"] == "cta":
            last = len(pops) - 1
            gone = ["#hero", f"#ch{last}", "#ok"] + ([] if beside else ["#orb"]) + ([f"#tt{last}"] if last in tags else [])
            js.append(f'tl.to("{",".join(gone)}",{{opacity:0,scale:.85,duration:SOFT.dur,ease:SOFT.ease}},{t - 0.05:.3f});')
            els.append(f'<div class="cta" id="cta" style="top:{(CAP_TOP_BESIDE + 4) if beside else OPT_TOP + 26}px">comment <b>{esc(e["word"])}</b></div>')
            js.append(f'tl.fromTo("#cta",{{opacity:0,scale:.6,y:24}},{{opacity:1,scale:1,y:0,duration:POP.dur,ease:POP.ease}},{t:.3f});')
            windows.append((t - 0.05, D + 1))
    if captions:
        top = CAP_TOP_BESIDE if beside else OPT_TOP + OPT_H + 90
        for p_i, p in enumerate(caption_pages(rows, times)):
            if any(a < p["t1"] and p["t0"] < b for a, b in windows): continue
            els.append(f'<div class="cap" id="p{p_i}" style="top:{top}px">{esc(p["text"])}</div>')
            js.append(f'tl.set("#p{p_i}",{{opacity:1}},{p["t0"]:.3f}); tl.set("#p{p_i}",{{opacity:0}},{p["t1"]:.3f});')
    return doc_html(D, name, mock, els, js), {}


def build(spec, name, mock, captions=False, times=None):
    rows, evs, D, board = spec["rows"], spec["events"], spec["duration"], spec["board"]
    if board["kind"] == "thisorthat": return build_tot(spec, name, mock, captions, times)
    js, els = [], []
    title = "<br>".join(esc(l) for l in spec["board_title"].split("\n"))
    els.append(f'<div class="title" id="title">{title}</div>')
    B = ['<div class="board">']
    prefix, seq = {}, {}
    if board["kind"] == "tier":
        for e in sorted(evs, key=lambda e: e["edit"]):
            if e["k"] == "place": seq.setdefault(e["tier"], []).append(e["item"])
        final = {t: seq.get(t, []) for t in board["tiers"]}
        slots = tier_layout(final)
        # each row as it fills: a row that later needs two lines stays one centred line until then, then reflows
        prefix = {t: [row_layout(final[t][:m], k) for m in range(1, len(final[t]) + 1)] for k, t in enumerate(board["tiers"])}
        for k, t in enumerate(board["tiers"]):
            B.append(f'<div class="trow" style="top:{row_top(k) - BOARD_TOP:.2f}px"><div class="lab" style="background:{board.get("colors", TIER_COLORS)[t]}">{t}</div></div>')
    else:
        slots, tags = versus_layout(board["rows"])
        for k, opp in enumerate(board["rows"]):
            s = slots[opp]
            B.append(f'<div class="trow" style="top:{row_top(k) - BOARD_TOP:.2f}px"><div class="hero"><div class="win" id="win{k}"></div>'
                     f'<div class="ht"><span class="chk" id="chk{k}" style="opacity:0">{CHECK_SVG}</span>{esc(board["hero"])}</div></div>'
                     f'<div class="vs" style="left:{s["vs_x"]}px;top:{(ROW_H - 32) / 2 - 2:.1f}px">vs</div></div>')
    B.append("</div>")
    els.append("".join(B))
    # items: each one sits at its final slot; before it is placed it is moved and scaled to the chest
    chips = {}
    for e in evs:
        if e["k"] != "pop": continue
        it = e["item"]; s = slots[it]; n = len(chips); px = s.get("px", ITEM_PX); sc = CHIP_SCALE * ITEM_PX / px
        cx, cy = s["x"] + s["w"] / 2, s["y"] + px / 2
        dx, dy = CHEST[0] - cx, CHEST[1] - cy
        chips[it] = n
        els.append(f'<div class="it" id="it{n}" style="left:{s["x"]}px;top:{s["y"]}px;font-size:{px}px"><span class="bg" id="bg{n}"></span><span class="tx">{esc(it)}</span></div>')
        js.append(f'tl.set("#it{n}",{{x:{dx:.1f},y:{dy:.1f},scale:{sc:.4f},opacity:0}},0);')
        js.append(f'tl.fromTo("#it{n}",{{opacity:0,scale:{sc * 0.55:.4f}}},{{opacity:1,scale:{sc:.4f},duration:POP.dur,ease:POP.ease}},{e["edit"]:.3f});')
    windows = []                                     # chip-up windows, so captions stay out of the way
    for e in evs:
        k, t = e["k"], e["edit"]
        if k == "place":
            n = chips[e["item"]]
            if board["kind"] == "tier":
                row = seq[e["tier"]]; m = row.index(e["item"]) + 1; L = prefix[e["tier"]][m - 1]
                for it2 in row[:m]:              # the new item lands; earlier ones move only if the row reflows
                    if it2 != e["item"] and L[it2] == prefix[e["tier"]][m - 2][it2]: continue
                    x, y, sc = to_state(L[it2], slots[it2])
                    js.append(f'tl.to("#it{chips[it2]}",{{x:{x:.1f},y:{y:.1f},scale:{sc:.4f},duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});')
            else:
                js.append(f'tl.to("#it{n}",{{x:0,y:0,scale:1,duration:SNAP.dur,ease:SNAP.ease}},{t:.3f});')
            js.append(f'tl.to("#bg{n}",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{t + 0.06:.3f});')
            pop_t = next(p["edit"] for p in evs if p["k"] == "pop" and p["item"] == e["item"])
            windows.append((pop_t - 0.05, t + 0.4))
        elif k == "win":
            js.append(f'tl.fromTo("#win{e["row"]}",{{opacity:0}},{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{t:.3f});')
            js.append(f'tl.fromTo("#chk{e["row"]}",{{opacity:0,scale:0.2}},{{opacity:1,scale:1,duration:STAMP.dur,ease:STAMP.ease}},{t + 0.04:.3f});')
        elif k == "tag":
            g = tags[e["row"]]
            els.append(f'<div class="tag" id="tag{e["row"]}" style="left:{g["x"]}px;top:{g["y"]}px">{esc(e["text"])}</div>')
            js.append(f'tl.fromTo("#tag{e["row"]}",{{opacity:0,scale:1.7}},{{opacity:1,scale:1,duration:STAMP.dur,ease:STAMP.ease}},{t:.3f});')
        elif k == "cta":
            els.append(f'<div class="cta" id="cta">comment <b>{esc(e["word"])}</b></div>')
            js.append(f'tl.fromTo("#cta",{{opacity:0,scale:.6,y:24}},{{opacity:1,scale:1,y:0,duration:POP.dur,ease:POP.ease}},{t:.3f});')
            windows.append((t - 0.05, D + 1))
    for e in evs:                                    # a chip that was never placed would hang over his chest
        if e["k"] == "pop" and not any(p["k"] == "place" and p["item"] == e["item"] for p in evs):
            raise SystemExit(f"{e['item']} pops but is never placed")
    if captions:
        for p_i, p in enumerate(caption_pages(rows, times)):
            if any(a < p["t1"] and p["t0"] < b for a, b in windows): continue
            els.append(f'<div class="cap" id="p{p_i}">{esc(p["text"])}</div>')
            js.append(f'tl.set("#p{p_i}",{{opacity:1}},{p["t0"]:.3f}); tl.set("#p{p_i}",{{opacity:0}},{p["t1"]:.3f});')
    return doc_html(D, name, mock, els, js), slots


def main():
    edl, proj, name = sys.argv[1], sys.argv[2], sys.argv[3]
    mock, caps_flag = "--mock" in sys.argv, "--captions" in sys.argv
    spec = json.load(open(edl)); caps = caps_flag or bool(spec.get("captions"))     # OB picked captions on 10-16
    isl_p = os.path.join(os.path.dirname(os.path.abspath(edl)), f"{spec['take']}_islands.json")
    times = word_times(spec, json.load(open(isl_p)) if os.path.exists(isl_p) else None)
    for ch in ("board_title",):
        if "—" in spec[ch] or "–" in spec[ch]: raise SystemExit("no em/en dashes on screen")
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    doc, slots = build(spec, name, mock, caps, times)
    if "—" in doc: raise SystemExit("em dash in the composition")
    out = f"{proj}/compositions/{name}{'.caps' if caps_flag else ''}{'.mock' if mock else ''}.html"
    open(out, "w").write(doc)
    if mock:
        lay = {"name": name, "mock_times": [mock_time(spec, i) for i in range(len(spec["rows"]))], "slots": slots}
        json.dump(lay, open(f"{proj}/{name}_layout.json", "w"), indent=1)
    print(out)


if __name__ == "__main__":
    main()
