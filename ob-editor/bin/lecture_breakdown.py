#!/usr/bin/env python3
"""Shot-by-shot approval doc for lecture reels: one self-contained HTML (images inlined, phone-friendly)
plus a PDF printed from it. OB approves this before any full render (hard rule, 2026-10-16).

  python3 lecture_breakdown.py CONFIG.json OUT.html
  node lecture_breakdown_pdf.js OUT.html OUT.pdf

CONFIG: {"title", "date", "intro": [..], "decisions": [{"q", "detail", "img"?, "default"}], "changes": [..],
         "audio": [..], "after": [..],
         "reels": [{"name", "title", "edl", "mocks", "take", "grade", "caption_file"?, "notes": [..],
                    "tv_fix": {"rows": [..], "text"}?, "trial_v": {"desc", "img"}}]}
"""
import base64, html, io, json, os, sys
from PIL import Image

esc = lambda s: html.escape(str(s or ""), quote=True)


def img64(path, w=360, q=78):
    im = Image.open(path).convert("RGB")
    if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def tc(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:04.1f}"


def card_desc(c):
    k = c.get("card")
    t = c.get("text", "").replace("\n", " ")
    if k == "big": return f'{c.get("big")} / {t}'
    if k in ("table", "list", "checks"):
        mark = {"table": "=", "list": "✓", "checks": "✗"}[k]
        return (f'{c["label"]}: ' if c.get("label") else "") + " · ".join(f"{mark} {r}" for r in c["rows"])
    lbl = {"title": "TODAY'S LECTURE", "close": "YOUR TURN"}.get(k) or c.get("label", "")
    return (f"{lbl}: " if lbl else "") + t


def reel_rows(spec):
    rows = spec["rows"]
    later = [r["edit_in"] for r in rows if (r["cue"] or {}).get("card") and r["edit_in"] >= 0.3]
    f1_out = min(2.5, (later[0] - 0.45) if later else 2.5) if spec.get("frame1") else 0.0
    out, cur = [], None
    for i, r in enumerate(rows):
        cue = r["cue"] or {}
        screen, sound = [], []
        if i == 0 and spec.get("frame1"):
            kick = spec.get("kicker", "TODAY'S LECTURE")
            screen.append("Hook (burned in on frame 1): " + (kick + " · " if kick else "") + spec["frame1"].replace("\n", " "))
            if cue.get("card"):
                screen.append(f"(Card skipped: the TV already shows it) {card_desc(cue)}")
        if cue.get("card") and r["edit_in"] >= f1_out:
            screen.append("Card in: " + card_desc(cue)); cur = cue
            sound.append("pop as the card lands")
            if cue["card"] in ("table", "list", "checks"): sound.append(f"tick x{len(cue['rows'])} as rows land")
        elif cue.get("hide"):
            screen.append("Card out"); cur = None
        elif cur is not None and not (i == 0 and spec.get("frame1")):
            screen.append("Card stays: " + card_desc(cur))
        if cue.get("stamp") and cur is not None:
            screen.append(f"Stamp slams on the card: {cue['stamp']}"); sound.append("thud on the stamp")
        if r["edit_in"] <= f1_out < r["edit_out"] + r.get("gap", 0) and spec.get("frame1"):
            sound.append(f"soft whoosh as the hook clears ({tc(f1_out)})")
        out.append({"i": i, "row": r, "screen": screen or ["No card, captions only"], "sound": sound or ["voice only"]})
    return out, f1_out


CSS = """
:root { --ink:#141414; --mute:#666; --line:#e4e4e4; --acc:#d4a900; --red:#d32f2f; --bg:#fff; --soft:#f6f6f3; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 18px 16px 60px; }
h1 { font-size: 24px; line-height: 1.2; margin: 6px 0 4px; }
h2 { font-size: 20px; margin: 34px 0 6px; padding-top: 14px; border-top: 3px solid var(--ink); }
h3 { font-size: 16px; margin: 22px 0 8px; }
p, li { margin: 4px 0; }
ul { padding-left: 20px; margin: 6px 0; }
.sub { color: var(--mute); font-size: 14px; }
.box { background: var(--soft); border-radius: 12px; padding: 12px 14px; margin: 10px 0; }
.dec { border-left: 5px solid var(--acc); }
.dec b.q { display: block; font-size: 16px; margin-bottom: 2px; }
.dec .def { font-size: 13px; color: var(--mute); margin-top: 4px; }
.pair img { width: 100%; border-radius: 8px; display: block; margin-top: 6px; }
.tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .4px; padding: 1px 7px; border-radius: 6px; background: #eee; margin-right: 4px; }
.tag.p { background: #111; color: #fff; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 14px; color: var(--mute); margin: 4px 0 10px; }
.meta b { color: var(--ink); }
.shot { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); break-inside: avoid; page-break-inside: avoid; }
.shot img { width: 34%; max-width: 200px; height: auto; border-radius: 8px; align-self: flex-start; background: #222; }
.info { flex: 1; min-width: 0; }
.hd { font-size: 13px; color: var(--mute); margin-bottom: 4px; }
.hd b { color: var(--ink); font-size: 15px; margin-right: 6px; }
.say { font-weight: 600; margin: 2px 0 6px; }
.lab { font-size: 11px; font-weight: 800; letter-spacing: .6px; color: var(--mute); text-transform: uppercase; margin-top: 4px; }
.scr li, .snd { font-size: 14px; }
.snd { color: #333; }
.fix { color: var(--red); font-weight: 600; }
@media (max-width: 520px) { body { font-size: 14px; } .shot img { width: 40%; } h1 { font-size: 21px; } }
@media print { @page { size: 480px 1040px; margin: 14px; } main { padding: 0; } h2 { break-before: page; } .shot img { width: 38%; } }
"""


def build(cfg):
    H = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{esc(cfg['title'])}</title><style>{CSS}</style></head><body><main>"]
    H.append(f"<h1>{esc(cfg['title'])}</h1><div class='sub'>{esc(cfg['date'])}</div>")
    for p in cfg.get("intro", []): H.append(f"<p>{esc(p)}</p>")
    H.append("<h3>Needs your call</h3>")
    for k, d in enumerate(cfg["decisions"], 1):
        H.append(f"<div class='box dec'><b class='q'>{k}. {esc(d['q'])}</b>{esc(d['detail'])}")
        for im in d.get("imgs", []):
            H.append(f"<div class='pair'><img src='{img64(im, 900, 82)}' alt=''></div>")
        H.append(f"<div class='def'>If you say nothing: {esc(d['default'])}</div></div>")
    H.append("<h3>What changed since the last mockups</h3><ul>" + "".join(f"<li>{esc(c)}</li>" for c in cfg["changes"]) + "</ul>")
    H.append("<h3>Sound, all three</h3><ul>" + "".join(f"<li>{esc(a)}</li>" for a in cfg["audio"]) + "</ul>")
    for rc in cfg["reels"]:
        spec = json.load(open(rc["edl"]))
        rows, f1_out = reel_rows(spec)
        H.append(f"<h2>{esc(rc['title'])}</h2>")
        H.append(f"<div class='meta'><span><b>{spec['duration']:.1f} s</b></span><span>{len(rows)} shots</span>"
                 f"<span>take {esc(rc['take'])}</span><span>grade {esc(rc['grade'])}</span></div>")
        H.append(f"<div class='meta'><span>Frame-1 hook: <b>{esc(spec['frame1'].replace(chr(10), ' '))}</b></span>"
                 f"<span>Grid cover: <b>{esc(spec.get('cover', ''))}</b></span></div>")
        if rc.get("caption_file") and os.path.exists(rc["caption_file"]):
            cap = open(rc["caption_file"]).read().strip()
            H.append(f"<div class='box'><div class='lab'>Post caption (from {esc(os.path.basename(os.path.dirname(rc['caption_file'])))})</div>"
                     f"<div style='white-space:pre-wrap;font-size:14px'>{esc(cap)}</div></div>")
        elif rc.get("caption_note"):
            H.append(f"<div class='box'><div class='lab'>Post caption</div>{esc(rc['caption_note'])}</div>")
        H.append("<p class='sub'>Captions run on every shot after the hook: 3 words at a time on your shirt, live word in yellow. Shots alternate wide and a 108% punch-in so the cuts don't jump.</p>")
        for n in rc.get("notes", []): H.append(f"<p class='sub'>{esc(n)}</p>")
        fix_rows = set(rc.get("tv_fix", {}).get("rows", []))
        for s in rows:
            r, i = s["row"], s["i"]
            frm = "Wide" if i % 2 == 0 else "Punch-in 108%"
            mock = os.path.join(rc["mocks"], f"{rc['name']}_{i:03d}.jpg")
            H.append("<div class='shot'>")
            H.append(f"<img src='{img64(mock)}' alt='shot {i + 1}'>")
            H.append("<div class='info'>")
            H.append(f"<div class='hd'><b>{i + 1}</b>{tc(r['edit_in'])} to {tc(r['edit_out'])} "
                     f"<span class='tag{' p' if i % 2 else ''}'>{frm}</span> source {tc(r['src_in'])} to {tc(r['src_out'])}</div>")
            said = r["caption"] if r["caption"].startswith('"') else f"“{r['caption']}”"
            H.append(f"<div class='say'>{esc(said)}</div>")
            H.append("<div class='lab'>On screen</div><ul class='scr'>" + "".join(f"<li>{esc(x)}</li>" for x in s["screen"]))
            if i in fix_rows: H.append(f"<li class='fix'>{esc(rc['tv_fix']['text'][str(i)] if isinstance(rc['tv_fix']['text'], dict) else rc['tv_fix']['text'])}</li>")
            H.append("</ul>")
            H.append(f"<div class='lab'>Sound</div><div class='snd'>{esc('; '.join(s['sound']))}</div>")
            H.append("</div></div>")
        tv = rc.get("trial_v")
        if tv:
            H.append(f"<h3>Trial variant V for this lecture</h3><div class='shot'><img src='{img64(tv['img'])}' alt=''>"
                     f"<div class='info'>{esc(tv['desc'])}</div></div>")
    H.append("<h2>After you say yes</h2><ul>" + "".join(f"<li>{esc(a)}</li>" for a in cfg["after"]) + "</ul>")
    H.append("</main></body></html>")
    return "".join(H)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    open(sys.argv[2], "w").write(build(cfg))
    print(sys.argv[2], round(os.path.getsize(sys.argv[2]) / 1e6, 1), "MB")
