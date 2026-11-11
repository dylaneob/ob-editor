// Screenshots of a lecture_viz composition.
//   node viz_shots.js mock    COMP.mock.html SHOTS.json     SHOTS: [{"t": 6.2, "bg": "/abs/still.jpg", "out": "/abs/out.jpg"}]
//   node viz_shots.js overlay COMP.overlay.html OUTDIR FPS DURATION [SCALE]   -> OUTDIR/f_00000.png ... (transparent)
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [mode, comp, a3, a4, a5, a6] = process.argv.slice(2);
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  const scale = mode === 'overlay' ? parseFloat(a6 || '0.5') : 0.5;
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: scale });
  await page.goto('file://' + comp, { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  if (mode === 'mock') {
    const shots = JSON.parse(fs.readFileSync(a3, 'utf8')).sort((x, y) => x.t - y.t);
    for (const s of shots) {
      await page.evaluate(async (src, t, psrc) => {
        const bg = document.getElementById('bg');
        if (bg.getAttribute('src') !== src) await new Promise(res => { bg.onload = res; bg.src = src; });
        const pi = document.getElementById('panelimg');       // reaction reels: the clip frame inside the panel
        if (pi && psrc && pi.getAttribute('src') !== psrc) await new Promise(res => { pi.onload = res; pi.src = psrc; });
        window.__timelines.main.seek(t, false);
      }, 'file://' + s.bg, s.t, s.panel ? 'file://' + s.panel : null);
      await new Promise(r => setTimeout(r, 40));
      await page.screenshot({ path: s.out, type: 'jpeg', quality: 86 });
    }
    console.log('mock shots', shots.length);
  } else {
    const fps = parseFloat(a4), D = parseFloat(a5), n = Math.floor(D * fps + 1e-6);
    fs.mkdirSync(a3, { recursive: true });
    for (let k = 0; k < n; k++) {
      await page.evaluate(t => { window.__timelines.main.seek(t, false); }, k / fps);
      await page.screenshot({ path: a3 + '/f_' + String(k).padStart(5, '0') + '.png', omitBackground: true });
    }
    console.log('overlay frames', n);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
