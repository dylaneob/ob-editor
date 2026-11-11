#!/usr/bin/env python3
"""Shot-by-shot review page for OB's C4079 cardio (this-or-that) and C4080 food (tier list) reels, as a
claude.ai Artifact: OB taps his calls, copies one reply line, plays the music previews and scrolls every shot
on his phone. Reuses HEAD / JS from lecture_review_page.py and img64 / tc from lecture_breakdown.py (read only).

  python3 tier_review_page.py WORK OUT.html

WORK: CARDIO_edl.json + FOOD_edl.json (tier_edl.py, crops from tier_stills.py), C40xx_islands.json,
hf/mocks (tier_mocks.js), frames/grade_options.jpg, music_previews/*.mp3 (tier_music.py).
"""
import base64, html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecture_breakdown import img64, tc   # noqa: E402
from lecture_review_page import HEAD as LHEAD, JS as LJS   # noqa: E402

esc = lambda s: html.escape(str(s or ""), quote=True)
T = tc

EXTRA_CSS = """<meta name="claude:viewport-fit-sides" content="cover">
<style>
body { padding-inline: 0; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.flags { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--stamp); border-radius: 12px; padding: 12px 14px; }
.tracks { display: grid; gap: 10px; }
.track { display: grid; gap: 6px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 12px; background: var(--bg); min-width: 0; }
.track b { font-weight: 600; }
.track .pl { display: grid; grid-template-columns: 4.2em minmax(0, 1fr); gap: 6px 8px; align-items: center; font-size: 13px; color: var(--muted); }
.track audio { width: 100%; height: 36px; }
.f1 { display: grid; grid-template-columns: minmax(0, 46%) minmax(0, 1fr); gap: 14px; align-items: start; }
.f1 img { width: 100%; max-width: 300px; border-radius: 10px; display: block; }
.board { display: grid; gap: 4px; font-size: 14px; }
.board div { display: grid; grid-template-columns: 2.2em minmax(0, 1fr); gap: 8px; align-items: baseline; }
.board .t { font-family: var(--display); font-weight: 700; font-size: 17px; border-radius: 5px; text-align: center; color: #1b1b1b; }
.cuts { margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 14px; }
.cuts .tc { color: var(--muted); }
.pair.two { grid-template-columns: repeat(2, minmax(0, 1fr)); display: grid; }
.refs { margin: 0; padding-left: 18px; font-size: 14px; color: var(--muted); }
</style>
"""

TITLE = "Cardio and Food Reels"


def data_uri(path, mime): return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def head():
    h = LHEAD.replace("<title>Lecture Reels Review</title>", f"<title>{TITLE}</title>")
    h = h.replace("/* Layout: a call sheet. The 5 calls up top, then one contact-sheet strip per reel. Section heads borrow the reels' own yellow hook block. */",
                  "/* Layout: a call sheet. The 5 calls up top, then one shot strip per reel. Section heads borrow the lecture page's yellow block so OB knows the format. */")
    return h + EXTRA_CSS


def removals(spec, isl, min_s=2.0):
    """Every stretch of the take the edit skips that is 2 s or longer, with what was said there."""
    rows = sorted(spec["rows"], key=lambda r: r["src_in"]); out = []
    spans = [(0.0, rows[0]["src_in"])] + [(a["src_out"], b["src_in"]) for a, b in zip(rows, rows[1:])] + [(rows[-1]["src_out"], isl[-1]["end"] + 0.5)]
    for a, b in spans:
        if b - a < min_s: continue
        said = [x["text"] for x in isl if x["start"] >= a - 0.05 and x["end"] <= b + 0.05 and x["text"] and "BLANK" not in x["text"]]
        out.append((a, b, " / ".join(said)))
    return out


def card(item): return item if item.isupper() else item[:1].upper() + item[1:]


def screen(spec, i):
    kind = spec["board"]["kind"]; out = []
    evs = sorted((e for e in spec["events"] if e["shot"] == i), key=lambda e: e["edit"])
    pops = [e for e in sorted(spec["events"], key=lambda e: e["edit"]) if e["k"] == "pop"]
    if i == 0:
        if kind == "thisorthat":
            out.append("Title boxes, on from frame 1: " + " / ".join(spec["board_title"].split("\n")))
            out.append(f"{'Labels beside your head' if spec['board'].get('layout') == 'beside' else 'Cards'} on from frame 1: {spec['board']['hero']} or {card(pops[0]['item'])}")
        else:
            out.append("Title box, on from frame 1: " + spec["board_title"].replace("\n", " "))
            out.append("Board on from frame 1: empty S to F rows")
    base = len(out)
    for e in evs:
        at = T(e["edit"])
        if kind == "thisorthat":
            thing = "label" if spec["board"].get("layout") == "beside" else "card"
            if e["k"] == "pop":
                out.append(f"{at} {card(e['item'])} {thing} bumps as you say it" if pops.index(e) == 0 else f"{at} {card(e['item'])} {thing} swaps in on the right")
            elif e["k"] == "win": out.append(f"{at} green check above {spec['board']['hero']}" if thing == "label" else f"{at} green check and ring on {spec['board']['hero']}")
            elif e["k"] == "tag": out.append(f"{at} “longevity” tag under {card(spec['board']['rows'][e['row']])}")
            elif e["k"] == "cta": out.append(f"{at} {thing}s clear, CTA chip “comment {e['word']}” holds to the end")
        else:
            if e["k"] == "pop": out.append(f"{at} chip pops over your chest: {e['item']}")
            elif e["k"] == "place": out.append(f"{at} {e['item']} springs into {e['tier']}")
            elif e["k"] == "cta": out.append(f"{at} CTA chip “comment {e['word']}”, holds to the end")
    if len(out) == base: out.append(("Labels hold" if spec["board"].get("layout") == "beside" else "Cards hold") if kind == "thisorthat" else "Board holds")
    return out


def sound(r, last):
    s = []
    ein, eout = r.get("edges", ["edge", "edge"])
    if ein == "cont": s.append("starts mid-sentence, the words before it are cut")
    if eout == "cont": s.append("ends mid-sentence, the rest is cut")
    if r.get("keep_join"): s.append("runs straight into the next shot (joined at the quietest 10 ms)")
    elif last: s.append(f"{r['gap']:.1f} s of room tone to end on")
    else: s.append(f"{round(r['gap'] * 1000)} ms pause after" + (" with room tone, so the next take can't leak in" if r.get("fill") == "room" else ""))
    return "; ".join(s)


def board_html(spec):
    b = spec["board"]
    if b["kind"] == "tier":
        return "<div class='board'>" + "".join(
            f"<div><span class='t' style='background:{b['colors'][t]}'>{t}</span><span>{esc(', '.join(b['final'][t]))}</span></div>" for t in b["tiers"]) + "</div>"
    tags = {e["row"] for e in spec["events"] if e["k"] == "tag"}
    return "<div class='board'>" + "".join(
        f"<div><span class='t' style='background:#4ADE80'>{k + 1}</span><span>{esc(b['hero'])} or {esc(card(o))}: {esc(b['hero'].lower())}"
        f"{' (longevity tag on ' + esc(card(o)) + ')' if k in tags else ''}</span></div>" for k, o in enumerate(b["rows"])) + "</div>"


def call(k, short, detail, opts, extra=""):
    H = [f"<div class='call'><h3><b>{k}</b>{esc(short)}</h3><p>{esc(detail)}</p>{extra}<div class='opts' role='radiogroup' aria-label='{esc(short)}'>"]
    for j, (lab, tok) in enumerate(opts):
        rid = f"c{k}_{j}"
        H.append(f"<input type='radio' name='call{k}' id='{rid}' value='{esc(tok)}' data-default='{1 if j == 0 else 0}'{' checked' if j == 0 else ''}>"
                 f"<label for='{rid}'>{esc(lab)}{'<small>default</small>' if j == 0 else ''}</label>")
    H.append("</div></div>")
    return "".join(H)


def build(W):
    R = {n: json.load(open(f"{W}/{n}_edl.json")) for n in ("CARDIO", "FOOD")}
    ISL = {n: json.load(open(f"{W}/{R[n]['take']}_islands.json")) for n in R}
    M = f"{W}/hf/mocks"; P = f"{W}/music_previews"
    dc, df = R["CARDIO"]["duration"], R["FOOD"]["duration"]
    H = [head(), "<main>"]
    H.append(f"<header><div class='kick'>Oct 16 · C4079 + C4080 · nothing rendered yet</div><h1>{TITLE}</h1>"
             "<p class='lede'><b>Updated with your picks: 1 B, 2 chest, 3 tight, 4 captions, 5 Jazzy Frenchy.</b> Cardio is a this-or-that from your three TikToks: "
             "two dark cards on your chest, Walking on the left the whole time, each cardio swapping in on the right, and a green check on your pick. Food keeps the Dan Martell tier board. "
             "Both open on their two most controversial picks, and both now carry 3-word captions timed to your words. "
             f"Cardio runs {dc:.0f} s, food {df:.0f} s. Every shot below shows exactly what will render. If it all looks right, reply \"render\".</p></header>")
    H.append("<section aria-labelledby='calls'><h2 id='calls'><span class='hookhead'>Your 5 calls</span></h2>")
    g = img64(f"{W}/frames/grade_options.jpg", 760, 82)
    H.append(call(1, "Grade for both reels", "Top row is cardio, bottom row is food. B is the warm skin look you picked for the lectures and the night clips. The mocks below use B.",
                  [("B warm skin", "1 B"), ("A clean", "1 A"), ("C punchy", "1 C")],
                  f"<div class='pair'><figure><figcaption>Original · A clean · B warm skin · C punchy</figcaption><img src='{g}' alt='Grade options on one cardio and one food frame'></figure></div>"))
    cv = img64(f"{M}/CARDIO_001.jpg", 420, 80); cl = img64(f"{M}/CARDIO_019.jpg", 420, 80)
    H.append(call(2, "Cardio layout", "Your pick: cards on your chest, like the @notcoledasilva badges, with an \u201cor\u201d between them. "
                  "Walking stays on the left the whole time, like Denzel in the podcast one, and the captions run just under the cards.",
                  [("Cards on my chest", "2 chest"), ("Labels beside my head, like Joey's", "2 beside head")],
                  f"<div class='pair two'><figure><figcaption>Your pick lands</figcaption><img src='{cv}' alt='Walking or Stairmaster with a green check on Walking'></figure>"
                  f"<figure><figcaption>Longevity tag</figcaption><img src='{cl}' alt='Walking or HIIT with a longevity tag under HIIT'></figure></div>"))
    H.append(call(3, "Food length", f"Tight is {df:.0f} s: all 16 foods, one reason line each (your B30 rule puts lessons at 90 to 119 s). "
                  "Full keeps every reason you gave and runs about 2:15.",
                  [(f"Tight, {T(df)[:-2]}", "3 tight"), ("Full, about 2:15", "3 full")]))
    c1, c2 = img64(f"{M}/CARDIO_002.jpg", 380, 78), img64(f"{M}/FOOD_002.jpg", 380, 78)
    H.append(call(4, "Captions", "Your pick: 3-word captions, timed to each word as you say it. They sit under the cards on cardio, and above the board on food, stepping aside while a food chip is up. "
                  "Lowercase like the board, but tier letters and HIIT stay in caps.",
                  [("3-word captions", "4 captions"), ("No captions", "4 none")],
                  f"<div class='pair two'><figure><figcaption>Captions on, cardio</figcaption><img src='{c1}' alt='Cardio frame with captions'></figure>"
                  f"<figure><figcaption>Captions on, food</figcaption><img src='{c2}' alt='Food frame with captions'></figure></div>"))
    tracks = [("jazzyfrenchy", "Jazzy Frenchy", "light jazz, playful"), ("nineteen", "Nineteen", "upbeat, from its main groove at 0:26"), ("funk", "Funk anthem", "upbeat funk (Pixabay)")]
    th = ["<div class='tracks'>"]
    for tag, name, vibe in tracks:
        th.append(f"<div class='track'><div><b>{esc(name)}</b> <span class='snd'>{esc(vibe)}</span></div><div class='pl'>"
                  f"<span>Cardio</span><audio controls preload='none' src='{data_uri(f'{P}/CARDIO_{tag}.mp3', 'audio/mpeg')}'></audio>"
                  f"<span>Food</span><audio controls preload='none' src='{data_uri(f'{P}/FOOD_{tag}.mp3', 'audio/mpeg')}'></audio></div></div>")
    th.append("</div>")
    H.append(call(5, "Music", "Three of your saved tracks under the first 20 s of each reel (the new openers), with your real voice. The track sits about 16 dB under you and dips 5 dB more while you talk. "
                  "You said royalty-free doesn't matter on short form; only the funk anthem keeps boosting open.",
                  [("Jazzy Frenchy", "5 jazzy"), ("Nineteen", "5 nineteen"), ("Funk anthem", "5 funk"), ("No music, I'll add a sound in the app", "5 none")], "".join(th)))
    H.append("<div class='reply' aria-live='polite'><output id='replytext'></output><button type='button' id='copybtn'>Copy reply</button>"
             "<span class='hint'>Paste it in chat. Or just type \"approved\".</span></div></section>")
    H.append("<section aria-labelledby='before'><h2 id='before'><span class='hookhead'>Before you post</span></h2><div class='flags'><ul class='plain'>"
             "<li><b>ManyChat:</b> the CTAs say “comment cardio” and “comment food”, so the CARDIO and FOOD keywords have to exist in ManyChat first.</li>"
             "<li><b>Frame 1:</b> both new openers have you facing the camera. The old ones (bottled smoothies, running) had you looking down at the dog.</li>"
             "<li><b>Nothing numeric goes on screen.</b> Your spoken numbers check out: three cups of air-popped popcorn is about 93 to 100 calories (USDA, about 31 a cup).</li>"
             "</ul></div></section>")
    fr = R["FOOD"]["rows"]; soda = [i + 1 for i, r in enumerate(fr) if r["caption"].startswith(("They did a study", "and kept the weight off"))]
    H.append("<section aria-labelledby='claims'><h2 id='claims'><span class='hookhead'>Claims I checked</span></h2><ul class='plain'>"
             f"<li><b>Diet soda vs water</b> (food shots {soda[0]} to {soda[-1]}, your opener): true as you say it. Peters et al., Obesity 2014, 303 adults: the diet-drink group lost 5.95 kg vs 4.09 kg on water in 12 weeks "
             "(<a href='https://doi.org/10.1002/oby.20737'>doi 10.1002/oby.20737</a>). The 1-year follow-up kept 6.21 kg off vs 2.45 kg (<a href='https://doi.org/10.1002/oby.21327'>doi 10.1002/oby.21327</a>). "
             "The notes flag it as American Beverage Association funded. Source: PubMed.</li>"
             "<li><b>“Outdated 1995 satiety study”</b> (potato): Holt et al., Eur J Clin Nutr 1995 (PubMed 7498104), boiled potatoes scored highest of 38 foods. The year is right; “outdated” is your opinion.</li>"
             "<li><b>Left out of the tight cut:</b> “vitamin C aids in fat loss” (berries) and “choline helps stimulate your metabolism” (eggs). Both are weak; the full cut would put them back.</li>"
             "</ul></section>")
    H.append("<nav class='reels' aria-label='Reels'><a href='#cardio'>Cardio</a><a href='#food'>Food</a></nav>")
    notes = {
        "CARDIO": ["Opens on your two most controversial matchups: Stairmaster (you call it controversial yourself), then Pilates (“torture ritual”). "
                   "Then running, cycling, HIIT and jump rope in the order you filmed them. Your “Walking again” on Pilates still fits as the second round.",
                   "Shots alternate 115% and a 130% punch-in with your face centred, so the cuts don't jump. Full frame, no board and no blur. Captions run under the cards; they step aside for the CTA."],
        "FOOD": ["Opens on diet soda in S (backed by the study) and avocado in C (“everyone thinks it's extremely healthy”), your two most controversial calls. "
                 "The other 14 follow in the order you filmed them, one reason line each.",
                 "Shots alternate 115% and a 130% punch-in with your face centred. Below the board the video runs blurred, like the reference. "
                 "The S row stays one line until it fills, then springs into two. Captions sit above the board and step aside while a chip is up."]}
    refs = ("<div class='lab'>Format references (yours, 10-16)</div><ul class='refs'><li>@joeymiuccio, “This or that: leg day edition”: labels, green check on the pick</li>"
            "<li>@notcoledasilva, “Content creation: this or that”: white title boxes, two badges on the chest</li>"
            "<li>@pivotalconversations, “This or that: podcast guest edition”: the winner stays on, a new challenger each round</li></ul>")
    for n, label in (("CARDIO", "Cardio: this or that"), ("FOOD", "Food: ranking foods for fat loss")):
        spec = R[n]; rows = spec["rows"]; tot = spec["board"]["kind"] == "thisorthat"
        H.append(f"<section id='{n.lower()}' aria-labelledby='h_{n}'><h2 id='h_{n}'><span class='hookhead'>{esc(label)}</span></h2>")
        H.append(f"<div class='meta'><span><b class='tc'>{spec['duration']:.1f} s</b></span><span>{len(rows)} shots</span><span>take {esc(spec['take'])}</span>"
                 f"<span>title: <b>{esc(' / '.join(spec['board_title'].split(chr(10))) if tot else spec['board_title'].replace(chr(10), ' '))}</b></span></div>")
        for x in notes[n]: H.append(f"<p class='note'>{esc(x)}</p>")
        if tot: H.append(refs)
        H.append(f"<div class='f1'><img src='{img64(f'{M}/{n}_f1.jpg', 420, 80)}' alt='{n.title()} frame 1'><div><div class='lab'>Frame 1</div>"
                 f"<p class='note'>What people see before you say a word: {'the title boxes and your first matchup' if tot else 'the title box and the empty board'}.</p>"
                 f"<div class='lab'>{'Rounds' if tot else 'Finished board'}</div>{board_html(spec)}</div></div>")
        H.append("<div class='shots'>")
        for i, r in enumerate(rows):
            items = "".join(f"<li>{esc(x)}</li>" for x in screen(spec, i))
            punch = r["framing"] == "punch"
            H.append(f"<article class='shot'><img src='{img64(f'{M}/{n}_{i:03d}.jpg', 300, 74)}' alt='Shot {i + 1} mockup'>"
                     f"<div class='info'><div class='tcline'><span class='n'>{i + 1}</span><span class='tc'>{T(r['edit_in'])} to {T(r['edit_out'])}</span>"
                     f"<span class='tag{' p' if punch else ''}'>{'Punch 130%' if punch else 'Wide 115%'}</span><span class='tc'>src {T(r['src_in'])}</span></div>"
                     f"<div class='say'>“{esc(r['caption'])}”</div><div class='lab'>On screen</div><ul class='scr'>{items}</ul>"
                     f"<div class='lab'>Sound</div><div class='snd'>{esc(sound(r, i == len(rows) - 1))}</div></div></article>")
        H.append("</div>")
        rm = removals(spec, ISL[n])
        H.append("<div class='lab'>What's cut (every stretch of 2 s or more)</div><ul class='cuts'>" + "".join(
            f"<li><span class='tc'>src {T(a)} to {T(b)} ({b - a:.1f} s)</span> {esc(said) if said else '<i>pause</i>'}</li>" for a, b, said in rm) + "</ul></section>")
    H.append("<section aria-labelledby='snd'><h2 id='snd'><span class='hookhead'>Sound, both reels</span></h2><ul class='plain'>"
             "<li>Your mic only. Pauses after sentences are cut to about 0.08 s, 0.03 s mid-sentence, and pieces that run on in your take are joined at the quietest 10 ms.</li>"
             "<li>Whisper medium heard every word of both scripts in the finished voice tracks; the only differences are wording (“gonna” / “going to”, “nut” / “not”). "
             "Every mid-sentence cut was checked side by side: the kept side ends whole and the cut side starts where it should.</li>"
             "<li>No sound effects, per your rule. Music is your pick above. Mastered to −14 LUFS.</li></ul></section>")
    H.append("<section aria-labelledby='aft'><h2 id='aft'><span class='hookhead'>After you say yes</span></h2><ul class='plain'>"
             "<li>I render both reels one at a time, once no other render is running on the Mac.</li>"
             "<li>Then a frame and loudness check on each, and a finals page with both files.</li></ul></section>")
    H.append("</main>" + LJS.replace("ob-lecture-review-picks", "ob-tier-review-picks"))
    return "".join(H)


if __name__ == "__main__":
    W, out = sys.argv[1], sys.argv[2]
    doc = build(W)
    if "—" in doc: sys.exit("em dash on the page")
    open(out, "w").write(doc)
    print(out, round(os.path.getsize(out) / 1e6, 2), "MB")
