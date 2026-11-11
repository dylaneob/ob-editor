// Flicker check for a lecture_viz overlay page: every element with an id, effective opacity (own x ancestors) at each
// frame; flags anything that goes visible -> hidden -> visible again within 0.8 s (a spring still running under a fade).
//   node viz_flicker.js COMP.overlay.html DURATION [FPS]
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const [comp, D, FPS] = process.argv.slice(2);
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 0.25 });
  await page.goto('file://' + comp, { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  const fps = parseFloat(FPS || '29.97'), n = Math.floor(parseFloat(D) * fps);
  const series = await page.evaluate(async (n, fps) => {
    const els = [...document.querySelectorAll('[id]')].filter(e => !['root'].includes(e.id) && !/^(w\d|p\d)/.test(e.id));
    const eff = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; };
    const out = {}; els.forEach(e => out[e.id] = []);
    for (let k = 0; k < n; k++) { window.__timelines.main.seek(k / fps, false); els.forEach(e => out[e.id].push(eff(e))); }
    return out;
  }, n, fps);
  let bad = 0;
  for (const [id, v] of Object.entries(series)) {
    let state = 'off', offAt = -1;
    for (let k = 0; k < v.length; k++) {
      if (state === 'off' && v[k] > 0.5) { if (offAt >= 0 && (k - offAt) / fps < 0.8) { console.log(`FLICKER ${id}: hidden at ${(offAt / fps).toFixed(2)} s, back at ${(k / fps).toFixed(2)} s`); bad++; } state = 'on'; }
      else if (state === 'on' && v[k] < 0.05) { state = 'off'; offAt = k; }
    }
  }
  console.log(`checked ${Object.keys(series).length} elements x ${n} frames: ${bad} flicker(s)`);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
