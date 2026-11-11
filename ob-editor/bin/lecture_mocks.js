// Screenshot every shot of a lecture reel mock: the shot's graded still + the overlay state at that moment.
// node lecture_mocks.js EDL.json PROJECT_DIR NAME
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [edlPath, proj, name] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(edlPath, 'utf8'));

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 0.5 });
  await page.goto('file://' + proj + '/compositions/' + name + '.mock.html', { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  for (let i = 0; i < spec.rows.length; i++) {
    const r = spec.rows[i], cue = r.cue || {};
    const len = r.edit_out - r.edit_in;
    const t = (cue.card || cue.stamp) ? Math.min(r.edit_out - 0.05, r.edit_in + Math.min(0.9, len * 0.8)) : r.edit_in + len / 2;
    const src = '../assets/stills/' + name + '_' + String(i).padStart(3, '0') + '.jpg';
    await page.evaluate(async (src, t) => {
      const bg = document.getElementById('bg');
      await new Promise(res => { bg.onload = res; bg.src = src; if (bg.complete) res(); });
      window.__timelines.main.seek(t); return true;
    }, src, t);
    await new Promise(r => setTimeout(r, 60));
    await page.screenshot({ path: proj + '/mocks/' + name + '_' + String(i).padStart(3, '0') + '.jpg', type: 'jpeg', quality: 84 });
  }
  await browser.close();
  console.log('done', name, spec.rows.length);
})().catch(e => { console.error(e); process.exit(1); });
