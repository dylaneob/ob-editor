#!/usr/bin/env python3
"""HyperFrames composition for a vertical lecture reel (That Zona Guy / Kara format, OB skin).

  python3 lecture_cards.py EDL.json PROJECT_DIR NAME [--mock]

Layers over the graded cut (1080x1920):
  - frame-1 hook (TODAY'S LECTURE kicker + yellow hook lines) in the card zone until the first card, so the
    TV title stays readable; no captions under it
  - slide cards over the lap area, keyed to the spoken line (never over the face)
  - CAP / BANNED stamps on the verdict lines (spring pop)
  - captions on his black shirt, 3-word pages, active word in yellow
Motion uses closed-form springs only. --mock swaps the video for per-shot stills.
"""
import html, json, os, re, sys

Y, R = "#F7DC3A", "#E53935"
W, H = 1080, 1920
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
@font-face {{ font-family: 'DINC'; src: url('../assets/fonts/DINCondensed-Bold.ttf'); }}
@font-face {{ font-family: 'AvDB'; src: url('../assets/fonts/AvenirNext-DemiBold.ttf'); }}
@font-face {{ font-family: 'AvH'; src: url('../assets/fonts/AvenirNext-Heavy.ttf'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
.media {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.f1 {{ position: absolute; left: 64px; width: 920px; top: 1010px; }}
.kick {{ display: inline-flex; gap: 12px; align-items: center; background: rgba(12,12,12,.9); color: #fff; border-radius: 14px;
         padding: 12px 20px 8px; font-family: 'DINC'; font-size: 40px; letter-spacing: 1.5px; margin-bottom: 16px; }}
.kick i {{ width: 14px; height: 14px; border-radius: 50%; background: {Y}; display: inline-block; margin-top: -4px; }}
.hook span {{ display: inline; background: {Y}; color: #111; font-family: 'DINC'; font-size: 104px; line-height: 1.14;
             padding: 8px 20px 0; box-decoration-break: clone; -webkit-box-decoration-break: clone; box-shadow: 0 18px 44px rgba(0,0,0,.45); }}
.card {{ position: absolute; left: 64px; width: 880px; top: 1040px; background: #fff; border-radius: 30px; color: #121212;
         padding: 34px 40px 38px; box-shadow: 0 26px 70px rgba(0,0,0,.55); opacity: 0; transform-origin: 50% 100%; }}
.lbl {{ font-family: 'DINC'; font-size: 38px; letter-spacing: 2px; color: #8a8a8a; margin-bottom: 10px; }}
.txt {{ font-family: 'AvH'; font-size: 60px; line-height: 1.12; }}
.big {{ font-family: 'DINC'; font-size: 150px; line-height: .95; color: {R}; }}
.sub {{ font-family: 'AvDB'; font-size: 40px; color: #333; margin-top: 10px; }}
.row {{ font-family: 'AvH'; font-size: 50px; line-height: 1.25; display: flex; gap: 22px; align-items: center; margin-top: 6px; }}
.row b {{ font-family: 'DINC'; font-size: 56px; width: 50px; text-align: center; }}
.stamp {{ position: absolute; right: 30px; top: -46px; border: 7px solid {R}; color: {R}; background: #fff; border-radius: 12px;
          font-family: 'DINC'; font-size: 80px; letter-spacing: 3px; padding: 8px 22px 0; transform: rotate(-7deg); opacity: 0; }}
.cap {{ position: absolute; left: 70px; right: 130px; top: 845px; text-align: center; font-family: 'AvH'; font-size: 64px; line-height: 1.08;
        color: #fff; text-transform: uppercase; opacity: 0;
        text-shadow: 0 0 6px rgba(0,0,0,.95), 0 3px 0 rgba(0,0,0,.9), 3px 0 0 rgba(0,0,0,.9), -3px 0 0 rgba(0,0,0,.9), 0 -3px 0 rgba(0,0,0,.9); }}
.cap .w {{ display: inline-block; margin: 0 9px; }}
.cap .on {{ color: {Y}; }}
"""


def card_html(i, cue):
    k = cue["card"]
    if k == "big":
        body = f'<div class="big">{esc(cue["big"])}</div><div class="sub">{esc(cue.get("text",""))}</div>'
    elif k in ("table", "list", "checks"):
        mark = {"table": "=", "list": "&#10003;", "checks": "&#10007;"}[k]
        col = {"table": "#555", "list": "#1b9e4b", "checks": R}[k]
        rows = "".join(f'<div class="row r{i}_{j}"><b style="color:{col}">{mark}</b><span>{esc(r)}</span></div>' for j, r in enumerate(cue["rows"]))
        body = (f'<div class="lbl">{esc(cue.get("label",""))}</div>' if cue.get("label") else "") + rows
    elif k == "title":
        body = f'<div class="lbl">TODAY\'S LECTURE</div><div class="txt">{esc(cue.get("text",""))}</div>'
    elif k == "close":
        body = f'<div class="lbl">YOUR TURN</div><div class="txt">{esc(cue.get("text",""))}</div>'
    else:
        lbl = cue.get("label") or (f'{cue["n"]} OF {cue["of"]}' if cue.get("n") else "")
        body = (f'<div class="lbl">{esc(lbl)}</div>' if lbl else "") + f'<div class="txt">{esc(cue.get("text",""))}</div>'
    body = body.replace("\n", "<br>")                      # "\n" in card text = forced line break
    return f'<div class="card" id="c{i}">{body}<div class="stamp" id="s{i}"></div></div>'


def caption_pages(rows):
    """3-word pages; words timed by character share inside each spoken piece."""
    pages = []
    for r in rows:
        words = r["caption"].split()
        if not words: continue
        dur = r["edit_out"] - r["edit_in"] - 0.16
        lens = [max(2, len(re.sub(r"[^\w']", "", w))) for w in words]; tot = sum(lens)
        t = r["edit_in"] + 0.06; times = []
        for L in lens: times.append(t); t += dur * L / tot
        for s in range(0, len(words), 3):
            pw = words[s:s + 3]; pt = times[s:s + 3]
            end = times[s + 3] if s + 3 < len(words) else r["edit_out"]
            pages.append({"words": pw, "times": pt, "t0": pt[0], "t1": end})
    return pages


def build(spec, name, mock, stills=None):
    rows = spec["rows"]; D = spec["duration"]; n_items = sum(1 for r in rows if r["cue"] and r["cue"].get("card") == "item" and r["cue"].get("n"))
    cards, js, cur = [], [], None
    # Frame-1 hook owns the card zone (and the captions) until the first real card; a title card that would
    # sit under it is dropped, since the TV already shows the lecture title on frame 1.
    f1_out = 0.0
    if spec.get("frame1"):
        later = [r["edit_in"] for r in rows if (r["cue"] or {}).get("card") and r["edit_in"] >= 0.3]
        f1_out = min(2.5, (later[0] - 0.45) if later else 2.5)   # gone before the first card lands
    for i, r in enumerate(rows):
        cue = r["cue"] or {}
        if cue.get("card") and r["edit_in"] < f1_out:
            continue
        if cue.get("card"):
            if cue.get("n"): cue["of"] = n_items
            cards.append(card_html(i, cue))
            if cue.get("instant"):   # already on screen at this time (a flash-forward opening: frame 1 shows it whole)
                js.append(f'tl.set("#c{i}",{{opacity:1,y:0,scale:1}},{r["edit_in"]:.3f});')
            else:
                js.append(f'tl.fromTo("#c{i}",{{opacity:0,y:60,scale:.94}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{r["edit_in"]:.3f});')
            if cue["card"] in ("table", "list", "checks"):
                for j, _ in enumerate(cue["rows"]):
                    if cue.get("instant"): js.append(f'tl.set(".r{i}_{j}",{{opacity:1,x:0}},{r["edit_in"]:.3f});')
                    else: js.append(f'tl.fromTo(".r{i}_{j}",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{r["edit_in"] + 0.25 + j * 0.45:.3f});')
            if cur is not None:
                js.append(f'tl.to("#c{cur}",{{opacity:0,y:-30,duration:SOFT.dur,ease:SOFT.ease}},{max(0, r["edit_in"] - 0.12):.3f});')
            cur = i
        if cue.get("hide") and cur is not None:
            js.append(f'tl.to("#c{cur}",{{opacity:0,y:-30,duration:SOFT.dur,ease:SOFT.ease}},{r["edit_in"]:.3f});'); cur = None
        if cue.get("stamp") and cur is not None:
            js.append(f'document.getElementById("s{cur}").textContent = {json.dumps(cue["stamp"])};')
            js.append(f'tl.fromTo("#s{cur}",{{opacity:0,scale:2.2,rotation:-16}},{{opacity:1,scale:1,rotation:-7,duration:STAMP.dur,ease:STAMP.ease}},{r["edit_in"] + 0.05:.3f});')
    if cur is not None and not spec.get("hold_end"):   # hold_end: hard cut out (a flash-forward that cuts into the reel)
        js.append(f'tl.to("#c{cur}",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(0, D - 0.9):.3f});')   # fully gone by the last frame
    # captions
    caps = []
    for p_i, p in enumerate(caption_pages(rows)):
        if p["t0"] < f1_out:  # frame-1 hook owns the opening; no captions under it
            if p["t1"] - f1_out < 0.3: continue
            p = dict(p, t0=f1_out + 0.02)   # a page still running when the hook clears picks up right away
        ws = "".join(f'<span class="w" id="w{p_i}_{k}">{esc(w)}</span>' for k, w in enumerate(p["words"]))
        caps.append(f'<div class="cap" id="p{p_i}">{ws}</div>')
        js.append(f'tl.set("#p{p_i}",{{opacity:1}},{p["t0"]:.3f}); tl.set("#p{p_i}",{{opacity:0}},{p["t1"]:.3f});')
        for k, t in enumerate(p["times"]):
            js.append(f'tl.set("#w{p_i}_{k}",{{className:"w on"}},{t:.3f}); tl.set("#w{p_i}_{k}",{{className:"w"}},{(p["times"][k+1] if k + 1 < len(p["times"]) else p["t1"]):.3f});')
    f1 = ""
    if spec.get("frame1"):
        lines = "<br>".join(f"<span>{esc(l)}</span>" for l in spec["frame1"].split("\n"))
        kick = spec.get("kicker", "TODAY'S LECTURE")      # null in the EDL = no kicker (non-lecture reels)
        kick_html = f'<div class="kick"><i></i>{esc(kick)}</div>' if kick else ""
        f1 = f'<div class="f1" id="f1">{kick_html}<div class="hook">{lines}</div></div>'
        js.append(f'tl.set("#f1",{{opacity:1}},0); tl.to("#f1",{{opacity:0,y:-30,duration:SOFT.dur,ease:SOFT.ease}},{f1_out:.3f});')
    if mock:
        bg = f'<img id="bg" class="media" src="{esc(stills[0])}"/>'
    else:
        bg = (f'<video id="aroll" class="media clip" src="../assets/{name}_cut.mp4" muted playsinline data-start="0" '
              f'data-duration="{D:.3f}" data-track-index="0"></video>')
    return f"""<!doctype html>
<html lang="en" data-resolution="portrait"><head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script><style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="{W}" data-height="{H}">
<div>{bg}</div>
{''.join(cards)}
{''.join(caps)}
{f1}
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
    edl, proj, name = sys.argv[1], sys.argv[2], sys.argv[3]
    mock = "--mock" in sys.argv
    spec = json.load(open(edl))
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    stills = [f"../assets/stills/{name}_{i:03d}.jpg" for i in range(len(spec["rows"]))]
    out = f"{proj}/compositions/{name}{'.mock' if mock else ''}.html"
    open(out, "w").write(build(spec, name, mock, stills))
    print(out)


if __name__ == "__main__":
    main()
