#!/usr/bin/env python3
"""The breakdown as a claude.ai Artifact page: OB taps his calls, copies one reply line, and scrolls every
shot on his phone. Same config as lecture_breakdown.py (decisions need "options": [{"label", "token"}]).

  python3 lecture_review_page.py CONFIG.json OUT.html
"""
import html, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecture_breakdown import img64, reel_rows, tc   # noqa: E402

esc = lambda s: html.escape(str(s or ""), quote=True)

HEAD = """<title>Lecture Reels Review</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
/* Layout: a call sheet. The 5 calls up top, then one contact-sheet strip per reel. Section heads borrow the reels' own yellow hook block. */
:root {
  --bg: #f4f4ef; --surface: #ffffff; --ink: #171714; --muted: #5d5c55; --line: #e1e0d6; --chip: #ebeae2;
  --hook: #f7dc3a; --hook-ink: #171714; --stamp: #c8352a;
  --display: "Barlow Condensed", "Arial Narrow", "Helvetica Neue", sans-serif;
  --body: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #121210; --surface: #1c1c19; --ink: #efeee7; --muted: #a7a69d; --line: #302f2a; --chip: #282722;
  --hook: #f7dc3a; --hook-ink: #171714; --stamp: #ff6b5e; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #121210; --surface: #1c1c19; --ink: #efeee7; --muted: #a7a69d; --line: #302f2a; --chip: #282722;
  --hook: #f7dc3a; --hook-ink: #171714; --stamp: #ff6b5e; color-scheme: dark }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); padding-inline: 16px; }
main { max-width: 760px; margin: 0 auto; padding-block: 20px 64px; display: grid; gap: 28px; }
h1, h2, h3 { font-family: var(--display); font-weight: 700; letter-spacing: .3px; margin: 0; text-wrap: balance; }
h1 { font-size: 40px; line-height: 1; text-transform: uppercase; }
.kick { font-family: var(--display); font-weight: 600; font-size: 15px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted); }
.lede { margin: 8px 0 0; max-width: 62ch; }
.hookhead { display: inline; background: var(--hook); color: var(--hook-ink); font-size: 27px; line-height: 1.25; text-transform: uppercase;
            padding: 3px 12px 0; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
section { display: grid; gap: 14px; }
.call { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 14px; display: grid; gap: 8px; min-width: 0; }
.call h3 { font-family: var(--body); font-weight: 600; font-size: 17px; letter-spacing: 0; }
.call h3 b { font-family: var(--mono); font-weight: 500; color: var(--muted); margin-right: 6px; }
.call p { margin: 0; color: var(--muted); font-size: 14px; }
.pair { display: grid; gap: 6px; }
.pair figure { margin: 0; display: grid; gap: 3px; }
.pair figcaption { font-family: var(--display); font-weight: 600; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); }
.pair img { width: 100%; border-radius: 8px; display: block; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.opts input { position: absolute; opacity: 0; pointer-events: none; }
.opts label { border: 1px solid var(--line); background: var(--chip); color: var(--ink); border-radius: 999px; padding: 7px 14px; font-size: 14px; cursor: pointer; }
.opts input:checked + label { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.opts input:focus-visible + label { outline: 2px solid var(--hook); outline-offset: 2px; }
.opts label small { opacity: .7; margin-left: 4px; }
.reply { position: sticky; bottom: calc(10px + env(safe-area-inset-bottom, 0px)); z-index: 2; background: var(--ink); color: var(--bg);
         border-radius: 14px; padding: 12px 14px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; box-shadow: 0 10px 30px rgba(0,0,0,.25); }
.reply output { flex: 1 1 220px; min-width: 0; font-family: var(--mono); font-size: 13.5px; }
.reply button { font: 600 14px var(--body); background: var(--hook); color: var(--hook-ink); border: 0; border-radius: 10px; padding: 9px 16px; cursor: pointer; }
.reply button:focus-visible { outline: 2px solid var(--bg); outline-offset: 2px; }
.reply .hint { flex-basis: 100%; font-size: 12.5px; opacity: .75; }
nav.reels { display: flex; flex-wrap: wrap; gap: 8px; }
nav.reels a { font-family: var(--display); font-weight: 600; font-size: 16px; letter-spacing: .6px; text-transform: uppercase; color: var(--ink);
              text-decoration: none; border: 1px solid var(--line); border-radius: 10px; padding: 6px 12px; background: var(--surface); }
.meta { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 14px; color: var(--muted); }
.meta b { color: var(--ink); font-weight: 600; }
.note { margin: 0; font-size: 14px; color: var(--muted); max-width: 62ch; }
.cap { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; font-size: 14px; white-space: pre-wrap; }
.cap .kick { display: block; margin-bottom: 4px; }
.shots { display: grid; }
.shot { display: grid; grid-template-columns: minmax(0, 36%) minmax(0, 1fr); gap: 12px; padding-block: 12px; border-top: 1px solid var(--line); }
.shot img { width: 100%; max-width: 210px; border-radius: 8px; display: block; background: #222; }
.shot .info { display: grid; gap: 4px; align-content: start; min-width: 0; }
.tcline { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px; font-size: 13px; color: var(--muted); }
.tcline .n { font-family: var(--display); font-weight: 700; font-size: 22px; color: var(--ink); line-height: 1; }
.tc { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.tag { font-family: var(--display); font-weight: 600; font-size: 13px; letter-spacing: .8px; text-transform: uppercase; border-radius: 6px; padding: 1px 7px; background: var(--chip); color: var(--ink); }
.tag.p { background: var(--ink); color: var(--bg); }
.say { font-weight: 600; }
.lab { font-family: var(--display); font-weight: 600; font-size: 12.5px; letter-spacing: 1.1px; text-transform: uppercase; color: var(--muted); margin-top: 2px; }
.scr { margin: 0; padding-left: 18px; font-size: 14px; }
.scr .fix, .scr .stamp { color: var(--stamp); font-weight: 600; }
.snd { font-size: 14px; color: var(--muted); }
.v { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 12px; }
ul.plain { margin: 0; padding-left: 18px; display: grid; gap: 4px; font-size: 14.5px; }
@media (max-width: 420px) { h1 { font-size: 34px; } .hookhead { font-size: 24px; } .shot { grid-template-columns: minmax(0, 40%) minmax(0, 1fr); } }
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
</style>
"""

JS = """<script>
(function () {
  var out = document.getElementById('replytext'), btn = document.getElementById('copybtn');
  var KEY = 'ob-lecture-review-picks';
  function picks() {
    var parts = [], allDefault = true;
    document.querySelectorAll('.call').forEach(function (c) {
      var r = c.querySelector('input:checked'); if (!r) return;
      parts.push(r.value); if (r.dataset.default !== '1') allDefault = false;
    });
    return { text: (allDefault ? 'approved, all defaults (' : 'picks: ') + parts.join(', ') + (allDefault ? ')' : ''), parts: parts };
  }
  function render() {
    var p = picks(); out.textContent = p.text;
    try { var saved = {}; document.querySelectorAll('.call input:checked').forEach(function (r) { saved[r.name] = r.id; }); localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {}
  }
  try { var s = JSON.parse(localStorage.getItem(KEY) || '{}'); Object.keys(s).forEach(function (k) { var el = document.getElementById(s[k]); if (el) el.checked = true; }); } catch (e) {}
  document.querySelectorAll('.call input').forEach(function (r) { r.addEventListener('change', render); });
  btn.addEventListener('click', function () {
    var text = out.textContent;
    function selectIt() { var rg = document.createRange(); rg.selectNodeContents(out); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(rg); btn.textContent = 'Selected: copy it'; }
    try {
      navigator.clipboard.writeText(text).then(function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy reply'; }, 1800); }, selectIt);
    } catch (e) { selectIt(); }
  });
  render();
})();
</script>"""


def build(cfg):
    H = [HEAD, "<main>"]
    H.append("<header><div class='kick'>Oct 15 shoot · 3 vertical lectures · nothing rendered yet</div><h1>Lecture Reels Review</h1>"
             "<p class='lede'>Every shot of all three reels is below: your real graded frame with the overlays mocked on top, what you say, and what's on screen. "
             "Tap your 5 calls, copy the reply line and paste it in chat. Defaults are already picked.</p></header>")
    H.append("<section aria-labelledby='calls'><h2 id='calls'><span class='hookhead'>Your 5 calls</span></h2>")
    for k, d in enumerate(cfg["decisions"], 1):
        H.append(f"<div class='call'><h3><b>{k}</b>{esc(d['short'])}</h3><p>{esc(d['detail'])}</p>")
        if d.get("imgs"):
            H.append("<div class='pair'>")
            names = ["Title before", "Title after", "Protein line before", "Protein line after"]
            from PIL import Image
            with tempfile.TemporaryDirectory() as td:
                for n, im in enumerate(d["imgs"]):
                    # each pair image is before (top) + 10 px gap + after (bottom): split so each half gets a label
                    src = Image.open(im); w, h = src.size; half = (h - 10) // 2
                    for part, box in ((0, (0, 0, w, half)), (1, (0, h - half, w, h))):
                        tmp = os.path.join(td, f"{k}_{n}_{part}.jpg"); src.crop(box).save(tmp, quality=85)
                        H.append(f"<figure><figcaption>{names[n * 2 + part]}</figcaption><img src='{img64(tmp, 760, 82)}' alt='{names[n * 2 + part]}'></figure>")
            H.append("</div>")
        H.append("<div class='opts' role='radiogroup'>")
        for j, o in enumerate(d["options"]):
            rid = f"c{k}_{j}"
            H.append(f"<input type='radio' name='call{k}' id='{rid}' value='{esc(o['token'])}' data-default='{1 if j == 0 else 0}'{' checked' if j == 0 else ''}>"
                     f"<label for='{rid}'>{esc(o['label'])}{'<small>default</small>' if j == 0 else ''}</label>")
        H.append("</div></div>")
    H.append("<div class='reply' aria-live='polite'><output id='replytext'></output><button type='button' id='copybtn'>Copy reply</button>"
             "<span class='hint'>Paste it in chat. Or just type \"approved\".</span></div></section>")
    H.append("<nav class='reels' aria-label='Reels'>" + "".join(f"<a href='#{rc['name'].lower()}'>{esc(rc['tab'])}</a>" for rc in cfg["reels"]) + "</nav>")
    for rc in cfg["reels"]:
        spec = json.load(open(rc["edl"])); rows, _ = reel_rows(spec)
        H.append(f"<section id='{rc['name'].lower()}' aria-labelledby='h_{rc['name']}'><h2 id='h_{rc['name']}'><span class='hookhead'>{esc(rc['title'])}</span></h2>")
        H.append(f"<div class='meta'><span><b class='tc'>{spec['duration']:.1f} s</b></span><span>{len(rows)} shots</span><span>take {esc(rc['take'])}</span>"
                 f"<span>hook: <b>{esc(spec['frame1'].replace(chr(10), ' '))}</b></span><span>grid cover: <b>{esc(spec.get('cover', ''))}</b></span></div>")
        H.append("<p class='note'>Captions run on every shot after the hook: 3 words at a time on your shirt, live word in yellow. Shots alternate wide and a 108% punch-in so the cuts don't jump.</p>")
        for n in rc.get("notes", []): H.append(f"<p class='note'>{esc(n)}</p>")
        if rc.get("caption_file") and os.path.exists(rc["caption_file"]):
            H.append(f"<div class='cap'><span class='kick'>Post caption on file</span>{esc(open(rc['caption_file']).read().strip())}</div>")
        elif rc.get("caption_note"):
            H.append(f"<div class='cap'><span class='kick'>Post caption</span>{esc(rc['caption_note'])}</div>")
        fixes = rc.get("tv_fix", {})
        H.append("<div class='shots'>")
        for s in rows:
            r, i = s["row"], s["i"]
            said = r["caption"] if r["caption"].startswith('"') else f"“{r['caption']}”"
            items = "".join(f"<li class='{'stamp' if x.startswith('Stamp') else ''}'>{esc(x)}</li>" for x in s["screen"])
            if str(i) in fixes.get("text", {}): items += f"<li class='fix'>{esc(fixes['text'][str(i)])}</li>"
            mock = os.path.join(rc["mocks"], f"{rc['name']}_{i:03d}.jpg")
            H.append(f"<article class='shot'><img src='{img64(mock, 300, 74)}' alt='Shot {i + 1} mockup'>"
                     f"<div class='info'><div class='tcline'><span class='n'>{i + 1}</span><span class='tc'>{tc(r['edit_in'])}–{tc(r['edit_out'])}</span>"
                     f"<span class='tag{' p' if i % 2 else ''}'>{'Punch 108%' if i % 2 else 'Wide'}</span><span class='tc'>src {tc(r['src_in'])}</span></div>"
                     f"<div class='say'>{esc(said)}</div><div class='lab'>On screen</div><ul class='scr'>{items}</ul>"
                     f"<div class='lab'>Sound</div><div class='snd'>{esc('; '.join(s['sound']))}</div></div></article>")
        H.append("</div>")
        tv = rc.get("trial_v")
        if tv:
            H.append(f"<div class='v shot'><img src='{img64(tv['img'], 300, 74)}' alt='Trial V opening'><div class='info'><div class='lab'>Trial version V</div><div>{esc(tv['desc'])}</div></div></div>")
        H.append("</section>")
    H.append("<section aria-labelledby='snd'><h2 id='snd'><span class='hookhead'>Sound, all three</span></h2><ul class='plain'>" + "".join(f"<li>{esc(a)}</li>" for a in cfg["audio"]) + "</ul></section>")
    H.append("<section aria-labelledby='aft'><h2 id='aft'><span class='hookhead'>After you say yes</span></h2><ul class='plain'>" + "".join(f"<li>{esc(a)}</li>" for a in cfg["after"]) + "</ul></section>")
    H.append("</main>" + JS)
    return "".join(H)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    tabs = {"L05": "Lecture 05", "L02": "Organic", "HZ": "Hormozi"}
    for rc in cfg["reels"]: rc["tab"] = tabs.get(rc["name"], rc["name"])
    open(sys.argv[2], "w").write(build(cfg))
    print(sys.argv[2], round(os.path.getsize(sys.argv[2]) / 1e6, 2), "MB")
