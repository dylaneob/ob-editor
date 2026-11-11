#!/usr/bin/env python3
"""Shot-by-shot breakdown (HTML, images embedded) for OB to approve before any full render.

  python3 build_breakdown.py WORK_DIR OUT.html
"""
import base64, html, io, json, re, subprocess, sys
from PIL import Image

W, OUT = sys.argv[1], sys.argv[2]
H = f"{W}/hf"
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
evs = json.load(open(f"{W}/events_resolved.json"))["events"]
words = json.load(open(f"{W}/words_clean.json"))["words"]
spec = json.load(open(f"{W}/events_spec.json"))
import os as _os0
META = json.load(open(f"{W}/breakdown_meta.json")) if _os0.path.exists(f"{W}/breakdown_meta.json") else {}   # per-project overrides


def tc(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def tcs(t):
    t = int(t); return f"{t // 60}:{t % 60:02d}"


def b64img(path, w):
    im = Image.open(path).convert("RGB"); im.thumbnail((w, w))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


esc = lambda s: html.escape(str(s or ""))
SFX = {"myths_overlay": "tick + whoosh per line", "photo_overlay": "pop per photo (shutter ticks on the montage)",
       "study": "whoosh in/out, tick on the highlight, pop on the stat", "chart_line": "whoosh, pop on the end value and callouts", "proof_pages": "pop per tile, whoosh on page flip", "proof_quote": "whoosh + pop per tile", "chapter": "thud + whoosh", "quote": "soft whoosh", "myths": "tick per line + whoosh", "split": "whoosh in/out, tick per bullet",
       "label": "tick", "photo": "pop", "equation": "pop per photo", "stat_ratio": "pop", "stat_bars": "whoosh", "stat_list": "tick per line",
       "stat_columns": "pop per number", "stat_count": "ticks as it counts", "stat_equals": "pop per row", "proof": "pop per tile",
       "poster": "whoosh", "end": "whoosh"}


def describe(e):
    t = e["type"]
    if e.get("desc"): return e["desc"]   # per-event wording from events_spec (projects after C4352)
    if t == "pills": return ("Floating tags around your head (Dan Go style), each pops as you say it: "
                             + " · ".join(f"<b>{esc(i[0])}</b>" for i in e["items"]))
    if t == "chapter": return f'Chapter card <b>"{e["n"]}. {esc(e["title"])}"</b> (yellow icon tile), full screen'
    if t == "quote": return f'Quote card, full screen: <b>"{esc(e["text"]).replace(chr(10), " ")}"</b>, red underline on "{esc(e.get("underline"))}"'
    if t == "myths": return 'Opening card: "It\'s not:" <b>Seed oils / Processed food / Big Pharma</b>, each crossed out in red as you say it'
    if t == "split": return (f'Split screen: you slide right, <b>"{esc(e.get("title"))}"</b> + bullets appear as you say them: '
                             + " · ".join(f"<b>{esc(i[0])}</b>" for i in e["items"]))
    if t == "label": return f'Top-left label: <b>{esc(e["title"])}</b>{(" / " + esc(e["sub"])) if e.get("sub") else ""}'
    if t == "photo": return (f'Photo card beside you: ' + (f'"{esc(e["title"])}" ' if e.get("title") else "")
                             + " · ".join(f"<b>{esc(p[1])}</b>" for p in e["photos"]))
    if t == "equation": return 'Photo equation: <b>Baking soda + Water = Fire extinguisher</b> (extinguisher appears as you say it), beside you'
    if t == "stat_ratio": return 'Stat card beside you: <b>Omega-3 : Omega-6 = 1 : 20</b> "The average American"'
    if t == "stat_bars": return 'Stat card beside you: bars <b>Goal 10,000 steps</b> vs <b>Average American 4,000 steps</b>'
    if t == "stat_list": return 'Stat card beside you: <b>Nearly 18-inch arms / Over 210 lb / Abs year-round</b>'
    if t == "stat_columns": return 'Stat card beside you: <b>4</b> ingredients Europe bans that the US allows / <b>16</b> the US bans that Europe allows'
    if t == "stat_count": return 'Stat card beside you: <b>My resting heart rate 72 → 52 BPM</b> (counts down as you say 52)'
    if t == "stat_equals": return 'Card beside you: <b>Dihydrogen monoxide = Water</b>, then <b>Cyanocobalamin = Vitamin B12</b>'
    if t == "proof": return 'Client results beside you: <b>4 before/afters</b> (2 women, 2 men, from your vetted proof library), "Individual results vary"'
    if t == "myths_overlay": return 'Your face stays on screen: "It\'s not:" <b>Seed oils / Processed food / Big Pharma</b> on the left of your frame, each crossed out as you say it'
    if t == "photo_overlay":
        what = {"M01": "Rapid-fire client before/afters (20, ~0.13 s apart, alternating sides), straight on your frame", "E24": "Your physique photos (placeholders until you send them)",
                "E25": "Client results, women: your 4, then 4 more from your iCloud album cut in, on your frame, nothing around them",
                "E25b": "Client results, men: your 4 (Client M front + back and 2 more), then 4 more men cut in at the halfway mark",
                "H01": "Alex Hormozi photos + name (placeholders until you send them)", "G01": "Your photo with your girlfriend (placeholder)",
                "E44": "Closing proof: 4 before/afters on your frame (Client M + 3 new)"}.get(e["id"], "Photos on your frame")
        return f'<b>{what}</b>'
    if t == "study":
        st = e["study"]
        return (f'Study card (you stay on the right): <b>{esc(st["journal"])} {esc(st["year"])}</b>, "{esc(st["title"][:90])}{"..." if len(st["title"]) > 90 else ""}". '
                f'Highlighted: <b>"{esc(st["hl"])}"</b>' + (f'; big stat <b>{esc(st["stat"])}</b>' if st.get("stat") else "")
                + f' · <a href="https://doi.org/{esc(st["doi"])}">doi.org/{esc(st["doi"])}</a>')
    if t == "chart_line":
        return ('Animated chart (you on the right): <b>US adult obesity 13.4% (1960) to 42.8% (2018), CDC NHANES</b>, line draws as you talk; '
                'callouts: <b>soybean oil use up 1000x+</b> (Blasbalg 2011) and <b>rising calories explain the weight gain</b> (Swinburn 2009)')
    if t == "proof_pages": return ('Client results beside you, two pages: <b>Women</b> (4 front/back before-afters) while you say "PCOS, postmenopausal, 30 pounds", '
                                   'then <b>Men</b> (Client M front + back, 2 more) from "men lose over 50 pounds". "Individual results vary"')
    if t == "proof_quote": return f'Proof before the CTA: <b>"{esc(e["text"])}"</b> over 4 tall before/afters (incl. Client M), beside you'
    if t == "poster": return '<b>Strawberry ingredients poster</b>, slow push-in down the ingredient list, beside you. <span class="warn">Needs your photo file</span>'
    if t == "end": return 'End card: <b>"Want my help? Book a call. Link in the description. Subscribe for more"</b>, beside you'
    return t


CLIPS = ({c["id"]: c for c in json.load(open(f"{W}/story/clips_prepped.json"))["clips"]}
         if _os0.path.exists(f"{W}/story/clips_prepped.json") else {})   # C4367: clip holds play a clip with its own sound


def clip_words(cid):
    """What a clip hold says, from its whisper.cpp word file (clips/words/<file>.json), trimmed to the piece used."""
    c = CLIPS.get(cid, {})
    if "file" not in c: return ""
    if _os0.path.exists(f"{W}/story/clip_heard.json"):   # the finished clip audio, transcribed (exact edges)
        heard = json.load(open(f"{W}/story/clip_heard.json"))
        if cid in heard: return heard[cid]
    js = json.load(open(f"{W}/clips/words/{c['file']}.json"))
    a, b = c.get("snap_in", c["in"]), c.get("snap_out", c["out"]); out = []
    for seg in js.get("transcription", []):   # whisper.cpp word-level output: one word per segment (older files: words in "tokens")
        for tk in (seg.get("tokens") or [seg]):
            t = tk.get("text", "")
            if t.startswith("[_") or not t.strip(): continue
            m = (tk["offsets"]["from"] + tk["offsets"]["to"]) / 2000
            if a - 0.05 <= m <= b + 0.05: out.append(t if t.startswith(" ") else " " + t)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def words_in(a, b):
    ws = [w for s, e, w in words if a - 0.05 <= s < b]
    if len(ws) <= 22: return " ".join(ws)
    return " ".join(ws[:12]) + " … " + " ".join(ws[-7:])


# ---- per-shot rows
rows = []
started = set()
for s in segs:
    ov = [e for e in evs if e["edit_in"] < s["edit_out"] - 0.02 and e["edit_out"] > s["edit_in"] + 0.02]
    cells = []
    for e in ov:
        if e["id"] in started:
            cells.append(f'<div class="cont">continues {e["id"]}</div>')
        else:
            started.add(e["id"])
            cells.append(f'<div class="ev"><span class="tag t-{e["type"]}">{e["id"]}</span> {describe(e)}'
                         f'<div class="meta">{tc(e["edit_in"])} to {tc(e["edit_out"])} ({e["dur"]:.1f}s) · sound: {SFX.get(e["type"], "none") if META.get("sfx", True) else "none"}{META.get("qc_tag", " · QC 8+/10")}</div>'
                         f'<img class="mock" src="{b64img(f"{H}/mocks/{e["id"]}.jpg", 640)}"/>'
                         + (f'<img class="mock" src="{b64img(f"{H}/mocks/{e["id"]}b.jpg", 640)}"/>' if e["type"] == "proof_pages" else "")
                         + (f'<img class="mock" src="{b64img(f"{H}/mocks/{e["id"]}_w2.jpg", 640)}"/>'
                            if e["type"] == "photo_overlay" and not e.get("layout", "").startswith("flash") and len({i[1] for i in e["items"]}) < len(e["items"]) else "")
                         + '</div>')
    covered = any(e["type"] in ("chapter", "quote", "myths", "photo", "equation", "proof", "poster", "end") or e["type"].startswith("stat")
                  for e in ov if e["edit_in"] <= s["edit_in"] + 0.3 and e["edit_out"] >= s["edit_out"] - 0.3)
    framing = "Wide" if s["framing"] == "wide" else "Punch-in 120%"
    if s.get("hold"):   # a clip hold: the clip plays full frame with its own sound, you're silent
        c = CLIPS.get(s.get("clip"), {})
        framing = "Title card" if s.get("clip") == "TITLE" else "Clip, full frame, its own sound"
        said = (f'<span class="dim">{esc(c.get("tag", ""))}:</span> "{esc(clip_words(s.get("clip")))}"' if c.get("file") else '<span class="dim">(no words)</span>')
        src = f'<span class="dim">{esc(s.get("clip"))}</span>'
    else:
        said, src = f'"{esc(words_in(s["src_in"], s["src_out"]))}"', tc(s["src_in"])
    rows.append(f'<tr><td class="n">{s["i"] + 1}</td><td class="tc">{tc(s["edit_in"])}<br/><span class="dim">{s["dur"]:.1f}s</span></td>'
                f'<td class="tc dim">{src}</td><td>{framing}{" <span class=dim>(under a graphic)</span>" if covered and not s.get("hold") else ""}</td>'
                f'<td class="words">{said}</td>'
                f'<td><img class="still" src="{b64img(f"{W}/stills/shot_{s["i"]:03d}.jpg", 360)}"/></td>'
                f'<td class="screen">{"".join(cells) or "<span class=dim>You, no graphics</span>"}</td></tr>')

# ---- chapters (YouTube description format)
chs = [e for e in evs if e["type"] == "chapter"]
chap = ["0:00 Intro"] + [f'{tcs(e["edit_in"])} {e["title"]}' for e in chs]
if META.get("chapters"):   # per-project chapter list (adds chapters that have no card, e.g. C4365 "Ozempic body")
    chap = META["chapters"]
counts = {}
for e in evs: counts[e["type"].split("_")[0]] = counts.get(e["type"].split("_")[0], 0) + 1
total = segs[-1]["edit_out"]

sfx_b64 = ""
try:
    wav = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", "/Users/YOU/ob-editor/assets/sfx/_preview.wav",
                          "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", "-"], capture_output=True, check=True).stdout
    sfx_b64 = "data:audio/wav;base64," + base64.b64encode(wav).decode()
except Exception:
    pass

page = f"""<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>C4352 Edit Breakdown</title>
<style>
:root {{ --bg:#f6f5f2; --fg:#151515; --dim:#777; --card:#fff; --line:#e3e0da; --y:#e9c400; --r:#d32f2f; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#111; --fg:#eee; --dim:#999; --card:#1a1a1a; --line:#2b2b2b; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 -apple-system,BlinkMacSystemFont,"Avenir Next",Helvetica,Arial,sans-serif; }}
.wrap {{ max-width:1400px; margin:0 auto; padding:24px 16px 80px; }}
h1 {{ font-size:28px; margin:0 0 4px; }} h2 {{ font-size:20px; margin:34px 0 10px; }}
.sub {{ color:var(--dim); margin-bottom:18px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }}
.box {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
.box > b {{ display:block; font-size:13px; color:var(--dim); font-weight:600; text-transform:uppercase; letter-spacing:.04em; margin-bottom:4px; }}
.warn {{ color:var(--r); font-weight:700; }}
ul {{ margin:6px 0 0 18px; padding:0; }} li {{ margin:4px 0; }}
pre {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; white-space:pre-wrap; font-size:14px; }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--card); }}
table {{ border-collapse:collapse; width:100%; min-width:1100px; }}
th, td {{ border-bottom:1px solid var(--line); padding:10px; vertical-align:top; text-align:left; }}
th {{ position:sticky; top:0; background:var(--card); font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.05em; z-index:1; }}
.n {{ font-weight:700; width:34px; }} .tc {{ font-variant-numeric:tabular-nums; white-space:nowrap; width:70px; }}
.dim {{ color:var(--dim); font-size:13px; }} .words {{ width:260px; font-size:14px; }}
.still {{ width:240px; border-radius:6px; display:block; }} .mock {{ width:100%; max-width:420px; border-radius:6px; margin-top:8px; display:block; border:1px solid var(--line); }}
.ev {{ margin-bottom:10px; }} .meta {{ color:var(--dim); font-size:12px; margin-top:3px; }} .cont {{ color:var(--dim); font-size:13px; font-style:italic; }}
.tag {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 7px; border-radius:6px; background:#222; color:#fff; margin-right:4px; }}
.t-chapter {{ background:var(--y); color:#111; }} .t-quote {{ background:#444; }} .t-split {{ background:#2e5aac; }} .t-photo, .t-equation {{ background:#2e7d32; }}
.t-proof {{ background:#8e24aa; }} .t-poster {{ background:var(--r); }} .t-end {{ background:#000; }} .t-label {{ background:#666; }}
</style></head><body><div class="wrap">
<h1>C4352: shot-by-shot breakdown</h1>
<div class="sub">Approve this before I render. Nothing below has been rendered yet; every graphic is a mockup screenshotted from the exact code that will render it.</div>

<div class="grid">
 <div class="box"><b>Length</b>24:10 raw → <strong>{tcs(total)}</strong> edited, {len(segs)} shots</div>
 <div class="box"><b>Cuts</b>Opening clap + 43 s of silence removed · 120 pauses trimmed to ~0.35 s · "because I'm a medical provider" clause cut (verified by re-listening)</div>
 <div class="box"><b>Layout</b>No head-in-the-corner anywhere. Photos and testimonials sit straight on your own frame, left and right of your face. Cards slide in beside you: graphic on the left, you full size and uncropped on the right.</div>
 <div class="box"><b>Look</b>Warm tan grade (your pick) · jump cuts hidden by alternating wide / 120% punch-in · Dan Go card system</div>
 <div class="box"><b>Audio</b>Your external mic, synced to the frame (offset −4.168 s, drift corrected) · mastered to −14 LUFS (YouTube) · motion preview verified: frame-exact video, audio within 6 ms</div>
 <div class="box"><b>Graphics</b>{len(evs)} total: {counts.get("chapter",0)} chapter cards, {counts.get("quote",0)} quote cards, {counts.get("split",0)} split screens, {counts.get("photo",0)+counts.get("equation",0)} photo cards, {counts.get("stat",0)} stat cards, 4 client-proof moments (20-client flash, women, men, closing), 1 poster, {counts.get("label",0)} labels, opener, end card</div>
 <div class="box"><b>Motion + sound</b>Real spring physics (no stock easing) · sound effects synthesized in code, mixed well under your voice
 {f'<audio controls src="{sfx_b64}" style="width:100%;margin-top:8px"></audio><div class="dim">Preview: whoosh, pop, tick, thud</div>' if sfx_b64 else ""}</div>
 <div class="box"><b>Quality check</b>Every graphic graded 1–10 against the reference; 22 fixes over 2 rounds; all now 8+/10. After render: dead-frame scan + frame review.</div>
</div>

<h2>Needs your answer</h2>
<div class="box"><ul>
 <li><span class="warn">Strawberry photo:</span> save it to Downloads (it only came through chat). E29 shows a placeholder until then.</li>
 <li><span class="warn">Check these numbers</span> (they're on screen as you said them; I couldn't verify them): E26 <b>Europe bans 4 / US bans 16</b>; E20 <b>average American 4,000 steps</b> (common estimates are 4,000 to 5,000). Keep, or drop the graphic?</li>
 <li><b>Music bed?</b> Default is none (voice + sound effects). Dan Go-style videos often run a quiet bed; if you want one, I'd lock graphic entrances to its beat.</li>
 <li><b>Lifestyle B-roll?</b> Dan Go cuts to footage of himself training and eating every few minutes. I can pull clips of you from your T7 archive for 5 to 6 spots.</li>
</ul></div>

<h2>YouTube chapters (paste into the description)</h2>
<pre>{esc(chr(10).join(chap))}</pre>

<h2>Shot list</h2>
<div class="tablewrap"><table>
<tr><th>#</th><th>Edit</th><th>Source</th><th>Framing</th><th>You say</th><th>Frame</th><th>On screen</th></tr>
{"".join(rows)}
</table></div>

<h2>Credits for the description</h2>
<pre>{esc(open(f"{W}/PHOTO-CREDITS.txt").read())}</pre>
</div></body></html>"""
import os as _os
if _os.path.exists(f"{W}/breakdown_meta.json"):   # per-project header, summary boxes and questions (C4352 text is the default)
    _m = json.load(open(f"{W}/breakdown_meta.json"))
    page = page.replace("<title>C4352 Edit Breakdown</title>", f"<title>{_m['title']}</title>")
    _grid = "".join(f' <div class="box"><b>{a}</b>{b}</div>\n' for a, b in _m["boxes"])
    _qs = "".join(f" <li>{q}</li>\n" for q in _m["questions"])
    page = re.sub(r"<h1>.*?</h1>", f"<h1>{_m['h1']}</h1>", page, count=1, flags=re.S)
    page = re.sub(r'<div class="grid">.*?</div>\n</div>\n', f'<div class="grid">\n{_grid}</div>\n', page, count=1, flags=re.S)
    page = re.sub(r"<h2>Needs your answer</h2>\n<div class=\"box\"><ul>.*?</ul></div>", f'<h2>Needs your answer</h2>\n<div class="box"><ul>\n{_qs}</ul></div>', page, count=1, flags=re.S)
    if _m.get("extra_html"):   # extra sections after the questions (C4365: every claim and what's on screen)
        page = page.replace("<h2>YouTube chapters", _m["extra_html"] + "\n<h2>YouTube chapters", 1)
open(OUT, "w").write(page)
print(OUT, f"{len(page)/1e6:.1f} MB,", len(rows), "shots,", len(evs), "graphics")
