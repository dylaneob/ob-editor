// Is every looking-away moment covered? Plays a lecture_viz overlay comp forward (as the renderer does) and, at each
// eyes-down sample from gaze_scan.py, checks that a full-screen cover (.adcard or .adproof) is fully visible.
//   node cover_check.js COMP.overlay.html GAZE.json [MARGIN_S]
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [comp, gazeFile, M] = process.argv.slice(2);
const margin = parseFloat(M || '0.05');
const g = JSON.parse(fs.readFileSync(gazeFile, 'utf8'));
const times = [];
for (const r of g.away) for (let t = r.t0 - margin; t <= r.t1 + margin + 1e-6; t += 0.05) times.push(+t.toFixed(3));
times.sort((a, b) => a - b);
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 0.25 });
  await page.goto('file://' + comp, { waitUntil: 'load' });
  const bad = await page.evaluate((times) => {
    const eff = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; };
    const covers = [...document.querySelectorAll('.adcard, .adproof')];
    const out = [];
    for (const t of times) {
      window.__timelines.main.seek(Math.max(0, t), false);
      if (!covers.some(c => eff(c) > 0.95)) out.push(t);
    }
    return out;
  }, times);
  const runs = [];
  for (const t of bad) { const r = runs[runs.length - 1]; if (r && t - r[1] < 0.06) r[1] = t; else runs.push([t, t]); }
  console.log(`${times.length} eyes-down checks, ${bad.length} uncovered` + (runs.length ? ': ' + runs.map(r => `${r[0].toFixed(2)}-${r[1].toFixed(2)}`).join(', ') : ''));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
