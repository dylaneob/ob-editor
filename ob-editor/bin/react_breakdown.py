#!/usr/bin/env python3
"""Shot-by-shot breakdown for a reaction edit (HTML, images embedded). OB approves before any render.

  python3 react_breakdown.py WORK_DIR SOURCE.MP4 OUT.html

Run react_qc.py first: it supplies the edit's own transcript (the "Said" column), the word-loss
check and the list of removals with what was in them.
"""
import base64, html, io, json, os, re, subprocess, sys
from PIL import Image

W, SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; H = f"{W}/hf"; Q = f"{W}/qc"
LUT = f"{W}/lut.png" if os.path.exists(f"{W}/lut.png") else os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
cl = json.load(open(f"{W}/react_cutlist.json")); shots, total = cl["shots"], cl["total"]
evs = json.load(open(f"{W}/react_events.json"))["events"]
words = json.load(open(f"{W}/mic_words_clean.json"))["words"]                       # recording time
EW = [(x["offsets"]["from"] / 1000, x["text"].strip()) for x in json.load(open(f"{Q}/edit_words.json"))["transcription"]]
EW = [(t, w) for t, w in EW if w and not w.startswith(("[", "("))]                    # edit time
gate = sorted(json.load(open(f"{W}/gate.json")), key=lambda g: g["rec_in"])
qc = json.load(open(f"{Q}/wordqc.json")); removals = json.load(open(f"{Q}/removals.json"))
FILE = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC], capture_output=True, text=True).stdout)
NOTES = json.load(open(f"{W}/breakdown_notes.json")) if os.path.exists(f"{W}/breakdown_notes.json") else None
TOPIC = {int(k): v for k, v in NOTES["topics"].items()} if NOTES else {3: "Never eat anything white", 12: "Costco honey is fake", 4: "Snacks linked to cancer", 2: "13% more muscle from visualizing",
         14: "It's not calories in, calories out", 5: "Gardening gloves vs straps", 11: "Eat more to lose fat", 13: "Fruit makes you secretly fat",
         7: "Weight loss lowers your metabolism"}
esc = lambda s: html.escape(str(s or ""))
tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
tcs = lambda t: f"{int(t) // 60}:{int(t) % 60:02d}"
nrm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def r2e(t):
    for s in shots:
        if s["src_in"] <= t < s["src_out"]: return s["edit_in"] + t - s["src_in"]
        if t < s["src_in"]: return s["edit_in"]
    return shots[-1]["edit_out"]


def phrase_at(ph):
    toks, ws = ph.split(), [(a, nrm(w)) for a, b, w in words]
    for i in range(len(ws) - len(toks)):
        if all(ws[i + k][1] == toks[k] for k in range(len(toks))): return ws[i][0]
    raise SystemExit(f"phrase not found: {ph}")


def img64(path, w):
    im = Image.open(path).convert("RGB"); im.thumbnail((w, w))
    b = io.BytesIO(); im.save(b, "JPEG", quality=72); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def frame64(t, w=320):
    f = f"{Q}/_thumb.jpg"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", SRC, "-i", LUT, "-filter_complex",
                    f"[0:v]scale={w}:-2[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", "-q:v", "4", f], check=True)
    d = img64(f, w); os.remove(f); return d


def said(a, b):
    ws = [w for t, w in EW if a - 0.05 <= t < b - 0.05]
    return " ".join(ws) if len(ws) <= 24 else " ".join(ws[:13]) + " … " + " ".join(ws[-8:])


def describe(e):
    t = e["type"]
    if t == "label": return f'Top-left label: <b>{esc(e["title"])}</b> / {esc(e.get("sub"))}'
    if t == "title": return '<b>"FACT OR CAP?"</b> slams in (the series device: every clip gets a verdict)'
    if t == "stamp": return f'Verdict stamp <b>{esc(e["text"])}</b>: "{esc(e.get("topic"))}"'
    if t == "pop": return f'Meme pop: <b>{esc(e["text"])}</b>'
    if t == "term": return f'Term label: <b>{esc(e["text"])}</b>: {esc(e.get("sub"))}'
    if t == "skip": return f'Time-skip card: <b>"{esc(e["text"])}"</b> (covers the cut search)'
    if t == "cite": return f'Citation card: <b>{esc(e["title"])}</b> ({esc(e["source"])}): "{esc(e["finding"])}"'
    if t == "ba": return '<b>Your Japan photo</b>, then <b>218 lb (Nov 27) → 185 lb (day 30)</b>, full screen'
    if t == "proof4": return '<b>Client M</b>, front + back, "Steep deficit", "Individual results vary"'
    if t == "montage": return f'Rapid-fire montage in the clip panel: all {len(e["items"])} account screenshots, "{esc(e["title"])}"'
    if t == "end": return f'End card: <b>{esc(e["title"])}</b> / {esc(e["line"])} / {esc(e.get("small"))}. You slide left, the card fills the right (no boxed PiP)'
    if t == "overlay": return esc(e.get("desc", "Images on your frame")) + (' · nothing around them, "Individual results vary" footnote' if e.get("foot") else " · nothing around them")
    if t == "study":
        st = e["study"]; ch = e.get("chart")
        return (f'{esc(st.get("tag", "Study"))} on screen: <b>{esc(st["journal"])} {esc(st["year"])}</b>, "{esc(st["finding"])}"'
                + (f' + animated chart: {esc(ch.get("title", ""))}' if ch else "") + ". Slides in on the right, you stay on the left")
    if t == "chart": return f'Animated chart: <b>{esc(e["chart"]["title"])}</b> ({esc(e["chart"].get("source", ""))}). Slides in on the right, you stay on the left'
    return t


# shot list
rows, started = [], set()
for i, s in enumerate(shots):
    ov = [e for e in evs if e["edit_in"] < s["edit_out"] - 0.02 and e["edit_out"] > s["edit_in"] + 0.02]
    cells = []
    for e in ov:
        if e["id"] in started: cells.append(f'<div class="cont">continues {e["id"]}</div>'); continue
        started.add(e["id"])
        imgs = "".join(f'<img class="mock" src="{img64(f"{H}/mocks/{n}.jpg", 640)}"/>' for n in [e["id"], e["id"] + "b", e["id"] + "c"] if os.path.exists(f"{H}/mocks/{n}.jpg"))
        hold = '<span class="tag t-held">HELD</span> <b class="warn">waits on your fact-check answer</b><br/>' if e.get("held") else ""
        cells.append(f'<div class="ev">{hold}<span class="tag t-{e["type"]}">{e["id"]}</span> {describe(e)}<div class="meta">{tc(e["edit_in"])} for {e["dur"]:.1f}s</div>{imgs}</div>')
    if s["layout"] == "insert":
        lay = f'<b>Insert</b>: {len(s["bites"])} of their fear-mongering soundbites, full screen'
        aud = "Their own sound, back to back. Your mic is off"
        rows.append(f'<tr><td class="n">{i + 1}</td><td class="tc">{tc(s["edit_in"])}<br/><span class="dim">{s["dur"]:.1f}s</span></td>'
                    f'<td class="tc dim">new</td><td>{lay}<div class="dim">{aud}</div></td><td class="words">{"<br/>".join(esc(chr(34) + b[3] + chr(34)) for b in s["bites"])}</td>'
                    f'<td><img class="still" src="{img64(f"{W}/stills/shot_{i:03d}.jpg", 360)}"/></td><td class="screen">{"".join(cells) or "<span class=dim>no graphics</span>"}</td></tr>')
        continue
    if s["layout"] == "split":
        lay = f'<b>Split</b>: you left, clip "{esc(TOPIC.get(s["k"], s["clip"][:20]))}" right'
        nsp = len(s.get("ob_speech", []))
        aud = "Clip audio (clean, from the file). Your mic muted" + (f", opens {nsp}x for you" if nsp else " the whole play")
    else:
        lay = "You, " + ("wide" if s["framing"] == "wide" else "punch-in 120%"); aud = "Your mic"
    rows.append(f'<tr><td class="n">{i + 1}</td><td class="tc">{tc(s["edit_in"])}<br/><span class="dim">{s["src_out"] - s["src_in"]:.1f}s</span></td>'
                f'<td class="tc dim">{tc(s["src_in"])}</td><td>{lay}<div class="dim">{aud}</div></td><td class="words">"{esc(said(s["edit_in"], s["edit_out"]))}"</td>'
                f'<td><img class="still" src="{img64(f"{W}/stills/shot_{i:03d}.jpg", 360)}"/></td><td class="screen">{"".join(cells) or "<span class=dim>no graphics</span>"}</td></tr>')

# YouTube chapters: intro, the first play of each clip, outro
chap, seen = [NOTES.get("chapter0", "0:00 Fact or cap?") if NOTES else "0:00 Fact or cap?"], set()
for s in shots:
    if s["layout"] == "split" and s["k"] not in seen and s["k"] in TOPIC:
        seen.add(s["k"]); chap.append(f'{tcs(max(0, s["edit_in"] - 1))} {TOPIC[s["k"]]}')
end = next((e for e in evs if e["type"] == "end"), None)
if end: chap.append(f'{tcs(end["edit_in"])} Send me clips')

# mic openings during clips (edit time) for OB to check
gate_rows = []
for g in gate:
    if not g["ob_speech"]:
        gate_rows.append(f'<tr><td>{tc(r2e(g["rec_in"]))}</td><td>{esc(TOPIC.get(g["k"], ""))}</td><td class="dim">stays muted for this whole play</td></tr>'); continue
    for a, b in g["ob_speech"]:
        ws = " ".join(w for s_, e_, w in words if a <= (s_ + e_) / 2 < b)
        gate_rows.append(f'<tr><td>{tc(r2e(a))}</td><td>{esc(TOPIC.get(g["k"], ""))}</td><td class="words">opens {b - a:.1f}s: "{esc(ws[:170])}"</td></tr>')

# what was cut (2 s or more)
rem_rows = []
for j, r in enumerate(removals):
    if j == 0: what = "Before your first line: pre-roll" + (" and your false starts" if r["text"] else "")
    elif j == len(removals) - 1: what = "After your sign-off" + (f': "{esc(r["text"][:80])}"' if r["text"] else "")
    elif r["text"]: what = f'Low talking: "{esc(r["text"][:120])}"'
    else: what = "No speech"
    rem_rows.append(f'<tr><td class="tc">{tc(r["edit_at"])}</td><td class="tc">{r["len"]:.1f}s</td><td class="tc dim">{tc(r["rec_in"])}</td>'
                    f'<td><img class="thumb" src="{frame64((r["rec_in"] + r["rec_out"]) / 2)}"/></td><td>{what}</td></tr>')

# fact-check lines, located in the edit (sources: PubMed abstracts, DOIs linked)
FC = [("false no resources", "popcorn lung (stamp R10 held)", 'you call "linked to lung disease" false. It is real for factory workers who breathed the butter flavoring (diacetyl): "popcorn lung" (<a href="https://doi.org/10.1056/NEJMoa020300">Kreiss et al. 2002, NEJM</a>). That study was about breathing it at the plant, not eating popcorn. Keep the CAP stamp, drop it, or make it MISLEADING?'),
      ("class b", "cold cuts (card S01 on screen)", 'you say "class B, possibly causes cancer, not confirmed". WHO\'s cancer agency classes processed meat <b>Group 1, carcinogenic to humans</b> (<a href="https://www.iarc.who.int/wp-content/uploads/2018/07/pr240_E.pdf">IARC press release, 2015</a>). Following your rule (real numbers on screen even when they differ), card S01 shows that plus the dose: each 50 g a day raises the risk 18%, and IARC says the risk grows with the amount eaten, which backs your dose point. Keep the card, or cut the line?'),
      ("worse than if you weren't", "GLP-1", 'two-thirds regain is confirmed (card R21), but "that\'s worse than if you weren\'t on a GLP" isn\'t: a year after stopping they were still 5.6% down vs 0.1% on placebo (<a href="https://doi.org/10.1111/dom.14725">Wilding 2022</a>). Card R21 shows that chart on screen.'),
      ("didn't ruin it", "The Biggest Loser", '"they didn\'t ruin their metabolism". The 6-year follow-up found metabolism ~500 kcal/day below expected (<a href="https://doi.org/10.1002/oby.21538">Fothergill 2016</a>), but the slowdown <b>didn\'t predict who regained</b>: that version keeps your point. Card S05 puts both on screen.'),
      ("research shows there's no benefit", "reverse dieting research", 'you say research shows reverse dieting has no metabolic benefit. I found no study testing it (PubMed has case reports and interviews only), so there is no card. Keep the line or cut it?'),
      ("fructose does not cause", "fructose", '"fructose does not cause visceral fat". Fructose-sweetened drinks at 25% of calories did raise visceral fat in a trial (<a href="https://doi.org/10.1172/JCI37385">Stanhope 2009</a>). "Whole fruit doesn\'t make Americans fat" is safe. (The "Visceral fat" label R35 sits on this line.)'),
      ("we just went over", "slower metabolism for life (stamp R37 held)", 'the clip says someone who used to be heavier must eat less for life. In a 2020 trial the slowdown was about 90 to 110 kcal/day right after 8 weeks of dieting, half that once weight held steady, and gone at 1 year (<a href="https://doi.org/10.1093/ajcn/nqaa220">Martins et al. 2020</a>). So CAP holds for typical dieters, though the Biggest Loser study above found it lasting after extreme loss. I reworded the stamp from "Weight loss lowers your metabolism" (you agree you burn less at a lower weight) to "Slower metabolism for life". OK to use it?')]
if NOTES: FC = NOTES["fact_checks"]
FC = sorted(((r2e(phrase_at(ph)), name, txt) for ph, name, txt in FC), key=lambda f: f[0])
fc_html = "".join(f'<li><b>{tc(t)} {name}</b>: {txt}</li>' for t, name, txt in FC)
held = [e["id"] for e in evs if e.get("held")]

# longest stretches with no clip on screen
runs, cur = [], []
for s in shots:
    if s["layout"] == "ob": cur.append(s)
    elif cur: runs.append(cur); cur = []
if cur: runs.append(cur)
runs.sort(key=lambda r: -(r[-1]["edit_out"] - r[0]["edit_in"]))
SHORT = {"R01": "intro", "R02": "intro", "R04": "white foods", "R05": "honey", "R06": "Costco prices", "R07": "honey", "R13": "fear marketing", "R18": "simple vs easy",
         "R19": "GLP-1 ads", "R20": "hunger", "R21": "GLP-1 regain", "R22": "calories in, calories out", "R23": "straps", "R24": "lose the ego", "R26": "BMR",
         "R27": "coma calories", "R28": "starvation mode", "R29": "your 215 lb", "R30": "your Japan story", "R31": "Client M", "R32": "reverse diet", "R33": "prime rib"}
if NOTES: SHORT = NOTES.get("short", {})
def topics(r):
    ids = [e["id"] for e in evs if r[0]["edit_in"] <= e["edit_in"] < r[-1]["edit_out"] and e["id"] in SHORT]
    return ", ".join(dict.fromkeys(SHORT[i] for i in ids)) or "talking"
pace = "; ".join(f'{tcs(r[0]["edit_in"])}-{tcs(r[-1]["edit_out"])} ({(r[-1]["edit_out"] - r[0]["edit_in"]) / 60:.1f} min: {topics(r)})' for r in runs[:3])

counts = {}
for e in evs: counts[e["type"]] = counts.get(e["type"], 0) + 1
n_proof = len({it[0] for e in evs if e["type"] == "overlay" for it in e["items"] if it[0][:2] in ("f_", "n_") or it[0] == "client_m4"})
nsplit = sum(1 for s in shots if s["layout"] == "split")
nclip = len(qc["clipped"])
qc_line = ("Word check passed: I re-transcribed the cut audio and compared it with the original word for word. No word is clipped at a cut."
           if not nclip else f'Word check: {nclip} spot(s) may clip a word: ' + "; ".join(f'{tc(c["edit"])} "{esc(c["missing"])}"' for c in qc["clipped"]))


import re as _re
def _at(m): return tc(r2e(phrase_at(m.group(1))))
if NOTES:
    if NOTES.get("qc_note"): qc_line, nclip = NOTES["qc_note"], 0
    TITLE = NOTES["title"]
    boxes = "".join(f'<div class="box"><b>{k}</b>{_re.sub(r"[{]at:([^}]+)[}]", _at, v)}</div>' for k, v in NOTES["boxes"])
    dec = "".join(f"<li>{_re.sub(r'[{]at:([^}]+)[}]', _at, d).replace('{pace}', pace)}</li>" for d in NOTES["decisions"])
    HEAD = (f'<h1>{esc(NOTES["title"])}</h1><div class="sub">{NOTES["sub"]}</div><div class="grid">'
            f'<div class="box"><b>Length</b>{tcs(FILE)} raw file → <strong>{tcs(total)}</strong> edit, {len(shots)} shots ({nsplit} clip plays, {len(shots) - nsplit} you)</div>'
            f'{boxes}<div class="box"><b>Cut check</b><span class="{"ok" if not nclip else "warn"}">{qc_line}</span></div>'
            f'<div class="box"><b>Graphics</b>{len(evs)}: ' + ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: -x[1])) + f'. {len(held)} held for your answer ({", ".join(held)}).</div></div>'
            f'<h2>Needs your answer</h2><div class="box"><ul>{dec}<li><span class="warn">Fact flags</span>: lines a commenter could disprove. The held cards above show the real number; these have no card. Keep or cut each:<ul>{fc_html}</ul></li></ul></div>')
    SOURCES = esc(NOTES["sources"])
else:
    TITLE = "C4353 Reaction Breakdown"
    HEAD = None  # C4353 default kept in qc backup; rebuild with the backup script for C4353
    SOURCES = ''
page = f"""<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{TITLE}</title>
<style>
:root {{ --bg:#f6f5f2; --fg:#151515; --dim:#777; --card:#fff; --line:#e3e0da; --y:#e9c400; --r:#d32f2f; --g:#2e7d32; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#111; --fg:#eee; --dim:#999; --card:#1a1a1a; --line:#2b2b2b; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 -apple-system,BlinkMacSystemFont,"Avenir Next",Helvetica,Arial,sans-serif; }}
.wrap {{ max-width:1400px; margin:0 auto; padding:24px 16px 80px; }} h1 {{ font-size:28px; margin:0 0 4px; }} h2 {{ font-size:20px; margin:34px 0 10px; }}
.sub {{ color:var(--dim); margin-bottom:18px; }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }}
.box {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
.box > b {{ display:block; font-size:13px; color:var(--dim); font-weight:600; text-transform:uppercase; letter-spacing:.04em; margin-bottom:4px; }}
.warn {{ color:var(--r); font-weight:700; }} .ok {{ color:var(--g); font-weight:700; }} ul {{ margin:6px 0 0 18px; padding:0; }} li {{ margin:6px 0; }}
pre {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; white-space:pre-wrap; font-size:14px; }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--card); }}
table {{ border-collapse:collapse; width:100%; }} .big {{ min-width:1100px; }} th, td {{ border-bottom:1px solid var(--line); padding:10px; vertical-align:top; text-align:left; }}
tr {{ break-inside:avoid; }}
th {{ background:var(--card); font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.05em; }}
.n {{ font-weight:700; width:34px; }} .tc {{ font-variant-numeric:tabular-nums; white-space:nowrap; width:70px; }} .dim {{ color:var(--dim); font-size:13px; }}
.words {{ width:260px; font-size:14px; }} .still {{ width:240px; border-radius:6px; display:block; }} .thumb {{ width:160px; border-radius:6px; display:block; }}
.mock {{ width:100%; max-width:420px; border-radius:6px; margin-top:8px; display:block; border:1px solid var(--line); }}
.ev {{ margin-bottom:10px; }} .meta {{ color:var(--dim); font-size:12px; margin-top:3px; }} .cont {{ color:var(--dim); font-size:13px; font-style:italic; }}
.tag {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 7px; border-radius:6px; background:#222; color:#fff; margin-right:4px; }}
.t-stamp {{ background:var(--r); }} .t-pop {{ background:#000; }} .t-term {{ background:#666; }} .t-cite, .t-skip {{ background:#2e5aac; }} .t-ba, .t-proof4 {{ background:#8e24aa; }} .t-montage {{ background:var(--g); }} .t-title {{ background:var(--y); color:#111; }} .t-held {{ background:var(--r); }}
a {{ color:inherit; }}
</style></head><body><div class="wrap">
{HEAD}<h2>YouTube chapters</h2><pre>{esc(chr(10).join(chap))}</pre>

<h2>What I cut (2 s or more)</h2>
<div class="sub">Everything else is kept. Pauses under 2 s that I shortened aren't listed.</div>
<div class="tablewrap"><table><tr><th>At (edit)</th><th>Length</th><th>Raw time</th><th>Frame</th><th>What it was</th></tr>{"".join(rem_rows)}</table></div>

<h2>Your mic during clips</h2>
<div class="sub">While a clip plays, your mic stays muted and opens only when you talk. These are the moments it opens and what it heard. If a line of yours is missing, tell me the time and I'll open the mic there.</div>
<div class="tablewrap"><table><tr><th>At (edit)</th><th>Clip</th><th>Mic</th></tr>{"".join(gate_rows)}</table></div>

<h2>Shot list</h2>
<div class="sub">Edit = time in the finished video. Raw = time in your camera file. "Said" is transcribed from the cut audio itself.</div>
<div class="tablewrap"><table class="big"><tr><th>#</th><th>Edit</th><th>Raw</th><th>Layout / audio</th><th>Said</th><th>Frame</th><th>On screen</th></tr>{"".join(rows)}</table></div>
<h2>Sources</h2><pre>{SOURCES}</pre>
</div></body></html>"""
open(OUT, "w").write(page)
print(OUT, f"{len(page) / 1e6:.1f} MB,", len(rows), "shots,", len(evs), "graphics,", len(rem_rows), "removals,", len(gate_rows), "mic rows; word check:", nclip)
