// Measure the content box of full-frame cards (v3 "fill the frame", C4367 2026-10-20). For each id: load ID.mock.html, seek to near
// the card's end (everything has landed), undo the stage push and any fit, and take the union of the visible content's boxes
// (leaf elements and SVG shapes; full-frame containers and the background skipped). Prints JSON {id: [x0, y0, x1, y1]}.
// node fit_measure.js HF_DIR EVENTS.json ID ID ...
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [hf, evp, ...ids] = process.argv.slice(2);
const EV = Object.fromEntries(JSON.parse(fs.readFileSync(evp)).events.map(e => [e.id, e]));
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 3840, height: 2160, deviceScaleFactor: 0.25 });
  const out = {};
  for (const id of ids) {
    const e = EV[id]; if (!e) continue;
    await page.goto('file://' + hf + '/compositions/' + id + '.mock.html', { waitUntil: 'load' });
    await page.evaluate(async () => { await document.fonts.ready; });
    const box = await page.evaluate((t) => {
      const tl = window.__timelines.main; tl.seek(t);
      for (const sel of ['#stg', '#fit']) { const n = document.querySelector(sel); if (n) n.style.transform = 'none'; }
      const root = document.querySelector('#fit') || document.querySelector('#stg') || document.querySelector('#root');
      const SHAPES = new Set(['path', 'circle', 'rect', 'text', 'line', 'polyline', 'polygon', 'ellipse', 'img', 'video', 'use']);
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
      const vis = el => { for (let p = el; p && p !== document.body; p = p.parentElement) { const cs = getComputedStyle(p); if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false; } return true; };
      for (const el of root.querySelectorAll('*')) {
        const tag = el.tagName.toLowerCase();
        if (tag === 'svg' || tag === 'g' || tag === 'defs' || tag === 'br' || tag === 'span' && el.children.length) continue;
        const hasText = [...el.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
        const csx = getComputedStyle(el);
        const boxed = csx.backgroundColor !== 'rgba(0, 0, 0, 0)' || csx.backgroundImage !== 'none' || csx.boxShadow !== 'none';   // a paper, a frame, a bar
        const leaf = SHAPES.has(tag) || hasText || boxed;
        if (!leaf || !vis(el)) continue;
        const rects = [];
        if (boxed && !hasText && el.children.length) rects.push(el.getBoundingClientRect());   // a paper or frame holding other content
        else if (hasText && !SHAPES.has(tag)) {   // the text itself, not its (often full-width, centred) block
          for (const c of el.childNodes) if (c.nodeType === 3 && c.textContent.trim()) { const rg = document.createRange(); rg.selectNodeContents(c); rects.push(rg.getBoundingClientRect()); }
          const cs = getComputedStyle(el);   // a pill or label with its own background counts whole
          if (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.backgroundImage !== 'none') rects.push(el.getBoundingClientRect());
        } else rects.push(el.getBoundingClientRect());
        for (const r of rects) {
          if (r.width * r.height < 4 || (r.width > 3700 && r.height > 2000)) continue;
          x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); n++;
        }
      }
      return n ? [x0, y0, x1, y1] : null;
    }, Math.max(0, e.dur - 0.15));
    out[id] = box;
  }
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(err => { console.error(err); process.exit(1); });
