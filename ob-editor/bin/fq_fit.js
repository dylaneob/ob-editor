// The largest font that keeps a quote card's approved line breaks in a narrower block (C4395 10-29: face_clear.py narrowed 22
// facequote cards to clear OB's face but kept their font, so 12 rewrapped badly: a lone ".", "out- / exercise", "500 / lb").
// Measured in Chrome with the card's own font, text-wrap:balance and underline span, laid out the way cards.py builds the block.
//   echo '{"font": ".../DINCondensed-Bold.ttf", "cards": [{"id": "M326", "rows": ["row html", ...], "fs0": 250, "w0": 1300, "w": 946, "fsNow": 250}]}' | node fq_fit.js
// -> {"M326": {"fs": 214, "kept": true, "lines": [["You'll keep", "doing."]], "now": [...]}}
// lines = the approved breaks (w0, fs0); now = the breaks at w with fsNow; a word split at its hyphen counts as a different break,
// and a size whose words overflow the block is never picked. kept false = no size down to the proportional one kept the breaks.
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');

(async () => {
  const job = JSON.parse(fs.readFileSync(0, 'utf8'));
  const font = fs.readFileSync(job.font).toString('base64');
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setContent(`<style>@font-face{font-family:'DINC';src:url(data:font/ttf;base64,${font})}*{margin:0;padding:0;box-sizing:border-box}
    .din{font-family:'DINC'}.u{position:relative;display:inline-block}</style><div id="blk" style="position:absolute;left:0;top:0"></div>`);
  await page.evaluate(async () => { await document.fonts.load("100px DINC"); });
  const out = await page.evaluate(cards => {
    const blk = document.getElementById('blk');
    const layout = (rows, w, f) => {
      blk.style.width = w + 'px';
      blk.innerHTML = rows.map(r => `<div class="din" style="font-size:${f}px;line-height:1.04;text-wrap:balance">${r}</div>`).join('');
      let over = false;
      const lines = [...blk.children].map(row => {
        over = over || row.scrollWidth > row.clientWidth + 1;
        const toks = [];
        for (const n of row.childNodes) {
          if (n.nodeType === 3) {
            for (const m of n.textContent.matchAll(/\S+/g)) {
              const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
              const b = [...r.getClientRects()].filter(x => x.width > 0);
              const split = b.length > 1 && Math.abs(b[b.length - 1].top - b[0].top) > f * 0.5;
              toks.push([b[0].top + b[0].height / 2, split ? '[SPLIT]' + m[0] : m[0]]);
            }
          } else { const b = n.getBoundingClientRect(); toks.push([b.top + b.height / 2, n.textContent]); }
        }
        const ls = [];
        for (const [y, t] of toks) { const k = Math.round((y - toks[0][0]) / (f * 1.04)); (ls[k] = ls[k] || []).push(t); }
        return ls.filter(Boolean).map(l => l.join(' '));
      });
      return { lines, over };
    };
    const res = {};
    for (const c of cards) {
      const want = JSON.stringify(layout(c.rows, c.w0, c.fs0).lines), low = Math.floor(c.fs0 * c.w / c.w0);
      let pick = null;
      for (let f = c.fs0; f >= low && pick === null; f--) {
        const l = layout(c.rows, c.w, f);
        if (!l.over && JSON.stringify(l.lines) === want) pick = f;
      }
      res[c.id] = { fs: pick === null ? low : pick, kept: pick !== null, lines: JSON.parse(want), now: layout(c.rows, c.w, c.fsNow || c.fs0).lines };
    }
    return res;
  }, job.cards);
  console.log(JSON.stringify(out));
  await browser.close();
})();
