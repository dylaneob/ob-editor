#!/usr/bin/env python3
"""Delivery page for finished lecture reels (claude.ai Artifact): phone-sized previews of each A master,
the V openings, covers, post captions with copy buttons, and the trial plan. Full files stay on T7.

  python3 lecture_finals_page.py CONFIG.json OUT_DIR
CONFIG: {"t7_dir", "reels": [{"name", "title", "a_preview", "v_preview", "cover", "caption_file"|None, "caption_note",
         "length", "v_desc"}], "qc": [..], "plan": [..]}
Writes OUT_DIR/index.html; previews and covers are published next to it via Artifact `files`.
"""
import html, json, os, sys

esc = lambda s: html.escape(str(s or ""), quote=True)

CSS = """<title>Oct 15 Lecture Reels</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
/* Layout: a delivery sheet. One strip per reel: the A master, its V opening, cover and post caption. Section heads use the reels' yellow hook block. */
:root {
  --bg: #f4f4ef; --surface: #ffffff; --ink: #171714; --muted: #5d5c55; --line: #e1e0d6; --chip: #ebeae2;
  --hook: #f7dc3a; --hook-ink: #171714; --ok: #1f7a43;
  --display: "Barlow Condensed", "Arial Narrow", "Helvetica Neue", sans-serif;
  --body: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #121210; --surface: #1c1c19; --ink: #efeee7; --muted: #a7a69d; --line: #302f2a; --chip: #282722;
  --hook: #f7dc3a; --hook-ink: #171714; --ok: #5fd28f; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #121210; --surface: #1c1c19; --ink: #efeee7; --muted: #a7a69d; --line: #302f2a; --chip: #282722;
  --hook: #f7dc3a; --hook-ink: #171714; --ok: #5fd28f; color-scheme: dark }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); padding-inline: 16px; }
main { max-width: 760px; margin: 0 auto; padding-block: 20px 64px; display: grid; gap: 30px; }
h1, h2 { font-family: var(--display); font-weight: 700; margin: 0; text-wrap: balance; }
h1 { font-size: 40px; line-height: 1; text-transform: uppercase; letter-spacing: .3px; }
.kick { font-family: var(--display); font-weight: 600; font-size: 15px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted); }
.lede { margin: 8px 0 0; max-width: 62ch; }
.hookhead { display: inline; background: var(--hook); color: var(--hook-ink); font-size: 27px; line-height: 1.25; text-transform: uppercase;
            padding: 3px 12px 0; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
section { display: grid; gap: 14px; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 14px; color: var(--muted); }
.meta b { color: var(--ink); font-weight: 600; }
.pair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; align-items: start; }
figure { margin: 0; display: grid; gap: 6px; min-width: 0; }
figcaption { font-family: var(--display); font-weight: 600; font-size: 14px; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); }
video, .cover { width: 100%; max-width: 100%; aspect-ratio: 9 / 16; border-radius: 12px; background: #000; display: block; }
.box { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px; display: grid; gap: 8px; min-width: 0; }
.cap { white-space: pre-wrap; font-size: 14px; margin: 0; }
.row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; }
button { font: 600 14px var(--body); background: var(--ink); color: var(--bg); border: 0; border-radius: 10px; padding: 8px 14px; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--hook); outline-offset: 2px; }
.files { font-family: var(--mono); font-size: 13px; overflow-x: auto; }
.files div { white-space: nowrap; }
ul.plain { margin: 0; padding-left: 18px; display: grid; gap: 4px; font-size: 14.5px; }
.ok::before { content: "✓ "; color: var(--ok); font-weight: 700; }
ul.qc { list-style: none; padding-left: 0; margin: 0; display: grid; gap: 4px; font-size: 14.5px; }
.lab { font-family: var(--display); font-weight: 600; font-size: 13px; letter-spacing: 1.1px; text-transform: uppercase; color: var(--muted); }
@media (max-width: 420px) { h1 { font-size: 34px; } .hookhead { font-size: 24px; } }
</style>
"""

JS = """<script>
document.querySelectorAll('button[data-copy]').forEach(function (b) {
  b.addEventListener('click', function () {
    var el = document.getElementById(b.dataset.copy), text = el.textContent;
    function sel() { var r = document.createRange(); r.selectNodeContents(el); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Selected: copy it'; }
    try { navigator.clipboard.writeText(text).then(function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy caption'; }, 1800); }, sel); }
    catch (e) { sel(); }
  });
});
</script>"""


def build(cfg):
    H = [CSS, "<main>"]
    H.append("<header><div class='kick'>Oct 15 shoot · 3 lectures · rendered and checked</div><h1>Oct 15 Lecture Reels</h1>"
             f"<p class='lede'>All three are done, with your 5 calls applied. The videos here are lighter previews so they play on your phone. "
             f"The full-quality files to post are on your T7, in <span class='files'>{esc(cfg['t7_dir'])}</span>.</p></header>")
    H.append("<section><h2><span class='hookhead'>How to post them</span></h2><ul class='plain'>" + "".join(f"<li>{esc(p)}</li>" for p in cfg["plan"]) + "</ul></section>")
    for k, rc in enumerate(cfg["reels"]):
        H.append(f"<section id='{esc(rc['name'].lower())}'><h2><span class='hookhead'>{esc(rc['title'])}</span></h2>")
        H.append(f"<div class='meta'><span><b>{esc(rc['length'])}</b></span><span>files: {esc(rc['name'])}_A.mp4 · {esc(rc['name'])}_V.mp4 · {esc(rc['name'])}_cover.jpg</span></div>")
        H.append("<div class='pair'>"
                 f"<figure><figcaption>A · the full reel</figcaption><video controls playsinline preload='metadata' poster='{esc(rc['cover'])}' src='{esc(rc['a_preview'])}'></video></figure>"
                 f"<figure><figcaption>Grid cover</figcaption><img class='cover' src='{esc(rc['cover'])}' alt='{esc(rc['title'])} cover'></figure></div>")
        H.append(f"<div class='pair'><figure><figcaption>V · opening only</figcaption><video controls playsinline preload='metadata' poster='{esc(rc.get('v_poster', ''))}' src='{esc(rc['v_preview'])}'></video></figure>"
                 f"<div class='box'><div class='lab'>What V changes</div><div>{esc(rc['v_desc'])}</div></div></div>")
        cap = open(rc["caption_file"]).read().strip() if rc.get("caption_file") and os.path.exists(rc["caption_file"]) else None
        if cap:
            H.append(f"<div class='box'><div class='row'><span class='lab'>Post caption</span><button type='button' data-copy='cap{k}'>Copy caption</button></div>"
                     f"<p class='cap' id='cap{k}'>{esc(cap)}</p></div>")
        else:
            H.append(f"<div class='box'><span class='lab'>Post caption</span><div>{esc(rc.get('caption_note', ''))}</div></div>")
        H.append("</section>")
    H.append("<section><h2><span class='hookhead'>Checked before you saw it</span></h2><ul class='qc'>" + "".join(f"<li class='ok'>{esc(q)}</li>" for q in cfg["qc"]) + "</ul></section>")
    H.append("</main>" + JS)
    return "".join(H)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1])); out = os.path.join(sys.argv[2], "index.html")
    open(out, "w").write(build(cfg)); print(out)
