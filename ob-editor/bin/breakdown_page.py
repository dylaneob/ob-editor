#!/usr/bin/env python3
"""Shot-by-shot breakdown page for a long-form edit (2026-10-31; from C4402's story/review_page.py), the HTML OB approves before any
full render (memory feedback_shot_list_before_render). One row per event in edit order, grouped by chapter card: the mock still,
the edit time, the length, what it is. His open calls go on top as tap-to-pick questions with a copy-reply line.

Client photos never go on a published page: photo_overlay events from the proof folder (and any id in --hide) show a text
placeholder instead of the mock; the full contact sheet stays on the T7.

  python3 -I breakdown_page.py WORK OUT.html --title "..." --calls CALLS.json [--mocks review] [--hide ID,ID]

CALLS.json: {"intro": "...", "calls": [{"code": "R1", "q": "question", "opts": ["first = default", "..."]}, ...], "notes": ["...", ...]}
Mocks: WORK/<mocks>/NN_<ID>_M-SS.jpg (the stages helper's naming) or WORK/hf/mocks/<ID>.jpg (C4402's).
"""
import base64, glob, html, io, json, os, sys
from PIL import Image

W, OUT = os.path.abspath(sys.argv[1]), sys.argv[2]
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
TITLE = arg("--title", "Breakdown"); CALLS = json.load(open(arg("--calls"))) if arg("--calls") else {"calls": []}
MOCKS = arg("--mocks", "review"); HIDE = set(filter(None, (arg("--hide", "") or "").split(",")))
EV = sorted(json.load(open(f"{W}/events_resolved.json"))["events"], key=lambda e: e["edit_in"])
SEGS = json.load(open(f"{W}/cutlist.json"))["segments"]; TOTAL = SEGS[-1]["edit_out"]
esc = lambda s: html.escape(str(s or ""), quote=True)
tc = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"


def mock(eid):
    c = glob.glob(f"{W}/{MOCKS}/*_{eid}_*.jpg") + glob.glob(f"{W}/hf/mocks/{eid}.jpg")
    if not c: return ""
    im = Image.open(c[0]).convert("RGB"); im.thumbnail((720, 720))
    b = io.BytesIO(); im.save(b, "JPEG", quality=58, optimize=True); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


KIND = {"reel": "Footage + your words", "chapter": "Chapter card", "dotgrid": "Dot chart", "stat_bars": "Bar chart", "photo_overlay": "Photos beside you",
        "plate": "Your words on you", "end": "End card", "clip": "Clip, own sound", "insert": "Footage", "label": "Tag", "pills": "Tags",
        # 10-31 Dan Go types (C4400-2 seed oils, C4401-2 stages)
        "dgchapter": "Chapter card", "facequote": "Your words beside you", "split": "Split list", "dsplit": "Split list", "study": "Study card",
        "studyx": "Study card", "stage": "Stage track", "ffcover": "Your b-roll over a glance", "mclip": "Montage clip", "board": "The board",
        "photo_full": "Photo, full frame", "quote_doc": "Quote card"}
chs = [e for e in EV if e["type"] in ("chapter", "dgchapter")]  # dgchapter = the Dan Go numbered chapter card
bounds = [0.0] + [c["edit_in"] for c in chs] + [TOTAL + 1]
names = ["Open"] + [f'{c.get("kicker", "")} · {c.get("title", "")}'.strip(" ·") for c in chs]
secs = []
for k, nm in enumerate(names):
    a, b = bounds[k], bounds[k + 1]; rows = []
    for e in EV:
        if not (a - 0.01 <= e["edit_in"] < b - 0.01): continue
        client = e["id"] in HIDE or (e["type"] == "photo_overlay" and e.get("folder") == "proof")
        src = "" if client else mock(e["id"])
        pic = (f'<img src="{src}" alt="{esc(e["id"])} at {tc(e["edit_in"])}" loading="lazy">' if src else
               f'<div class="ph">{"Client photos: left off this page (they are in the T7 contact sheet)" if client else "No still yet"}</div>')
        rows.append(f'<article class="row">{pic}<div class="meta"><div class="line"><span class="tc">{tc(e["edit_in"])}</span>'
                    f'<span class="kind">{esc(KIND.get(e["type"], e["type"]))}</span><span class="dur">{e["edit_out"] - e["edit_in"]:.1f} s</span>'
                    f'<span class="id">{esc(e["id"])}</span></div><p>{e.get("desc", "")}</p></div></article>')
    secs.append(f'<section><h2>{esc(nm)} <span class="at">{tc(a)}</span></h2><div class="rows">{"".join(rows)}</div></section>')

qs = []
for c in CALLS.get("calls", []):
    opts = "".join(f'<label><input type="radio" name="{esc(c["code"])}" value="{esc(o)}"{" checked" if i == 0 else ""}>{esc(o)}</label>' for i, o in enumerate(c["opts"]))
    qs.append(f'<div class="q" data-code="{esc(c["code"])}"><p><span class="code">{esc(c["code"])}</span>{c["q"]}</p><div class="opts">{opts}</div></div>')
notes = "".join(f"<li>{n}</li>" for n in CALLS.get("notes", []))
default_line = " · ".join(f'{c["code"]} {c["opts"][0]}' for c in CALLS.get("calls", []))
page = f"""<title>{esc(TITLE)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500;600&display=swap">
<style>
:root{{--bg:#f4f2ee;--card:#fffdf9;--ink:#1d1b18;--mute:#6b665e;--line:#e2ddd4;--acc:#b98f00;--accbg:#fff4c7;--chip:#efeae1;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#15140f;--card:#1f1d18;--ink:#f1ede4;--mute:#a59f93;--line:#34312a;--acc:#f7dc3a;--accbg:#3a3313;--chip:#2a2721;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#15140f;--card:#1f1d18;--ink:#f1ede4;--mute:#a59f93;--line:#34312a;--acc:#f7dc3a;--accbg:#3a3313;--chip:#2a2721;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);font:15px/1.5 Inter,system-ui,sans-serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 70px}}
main{{max-width:980px;margin:0 auto;display:flex;flex-direction:column;gap:20px}}
h1,h2{{font-family:"Barlow Condensed",Inter,sans-serif;margin:0;text-wrap:balance}} h1{{font-size:32px}} h2{{font-size:24px;margin-bottom:10px}}
.at{{color:var(--mute);font-size:16px;font-family:Inter,sans-serif;font-weight:500}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:10px;min-width:0}}
.q{{border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:8px}} p{{margin:0}}
.code{{font-family:"Barlow Condensed",sans-serif;font-weight:700;color:var(--acc);margin-right:6px;font-size:16px}}
.opts{{display:flex;flex-wrap:wrap;gap:8px}} .opts label{{display:flex;gap:6px;align-items:center;border:1px solid var(--line);border-radius:99px;padding:6px 12px;cursor:pointer;font-size:14px}}
.opts label:has(input:checked){{border-color:var(--acc);background:var(--accbg)}} .opts input{{accent-color:var(--acc)}}
ul{{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:5px}} .sub{{color:var(--mute)}}
.rows{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column;min-width:0}}
.row img{{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:var(--chip)}}
.ph{{aspect-ratio:16/9;display:grid;place-items:center;text-align:center;padding:12px;background:var(--chip);color:var(--mute);font-size:13px}}
.meta{{padding:9px 11px 11px;display:flex;flex-direction:column;gap:5px;font-size:13.5px}}
.line{{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}} .tc{{font-weight:600;font-variant-numeric:tabular-nums}}
.kind{{background:var(--chip);border-radius:99px;padding:1px 8px;font-size:12px}} .dur,.id{{color:var(--mute);font-size:12px}}
.reply{{position:sticky;bottom:12px;background:var(--ink);color:var(--bg);border-radius:14px;padding:12px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.reply code{{flex:1;min-width:0;font-size:14px;word-break:break-word}} .reply button{{background:var(--acc);color:#1d1b18;border:0;border-radius:10px;padding:8px 14px;font-weight:600;cursor:pointer}}
</style>
<main>
<header class="card"><h1>{esc(TITLE)}</h1><p>{CALLS.get("intro", "")}</p></header>
<section class="card"><h2>Your calls</h2><p class="sub">Tap your picks, then copy the reply line at the bottom and send it to me. If you skip one, I go with the first option.</p>{"".join(qs)}</section>
{f'<section class="card"><h2>Notes</h2><ul>{notes}</ul></section>' if notes else ''}
{"".join(secs)}
<div class="reply"><code id="line">{esc(default_line)}</code><button id="cp" type="button">Copy</button></div>
</main>
<script>
(function(){{var line=document.getElementById('line'),btn=document.getElementById('cp');
function build(){{var p=[];document.querySelectorAll('.q').forEach(function(q){{var v=q.querySelector('input:checked');if(v)p.push(q.dataset.code+' '+v.value)}});line.textContent=p.join(' · ')}}
document.addEventListener('change',build);
btn.addEventListener('click',function(){{var t=line.textContent;function sel(){{var r=document.createRange();r.selectNodeContents(line);var s=getSelection();s.removeAllRanges();s.addRange(r);btn.textContent='Selected'}}
if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(function(){{btn.textContent='Copied'}},sel);else sel()}});build()}})();
</script>"""
open(OUT, "w").write(page)
print(f"{OUT}: {len(EV)} events, {sum(1 for e in EV if e['id'] in HIDE or (e['type'] == 'photo_overlay' and e.get('folder') == 'proof'))} client-photo rows hidden, {os.path.getsize(OUT) / 1e6:.1f} MB")
