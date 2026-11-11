// Screenshot every shot of a tier reel mock: the shot's graded still + the board state at that moment.
// node tier_mocks.js PROJECT_DIR NAME [COMP]     (COMP defaults to NAME; "NAME.caps" for the captions option)
// Shot times come from PROJECT_DIR/NAME_layout.json (tier_cards.py --mock). Also writes NAME_f1.jpg (frame 1).
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [proj, name, comp0] = process.argv.slice(2);
const comp = comp0 || name;
const lay = JSON.parse(fs.readFileSync(proj + '/' + name + '_layout.json', 'utf8'));
const only = process.env.SHOTS ? process.env.SHOTS.split(',').map(Number) : null;

(async () => {
  const browser = await puppeteer.launch({ headless: true, timeout: 180000, protocolTimeout: 180000, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 0.5 });
  await page.goto('file://' + proj + '/compositions/' + comp + '.mock.html', { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; return true; });
  const shots = [['f1', 0]].concat(lay.mock_times.map((t, i) => [String(i).padStart(3, '0'), t]));
  const tag = comp === name ? name : comp.replace('.', '_');
  fs.mkdirSync(proj + '/mocks', { recursive: true });
  for (const [id, t] of shots) {
    if (only && !(id === 'f1' ? only.includes(-1) : only.includes(Number(id)))) continue;
    const src = '../assets/stills/' + name + '_' + id + '.jpg';
    await page.evaluate(async (src, t) => {
      const bg = document.getElementById('bg');
      await new Promise(res => { bg.onload = res; bg.src = src; if (bg.complete) res(); });
      window.__timelines.main.seek(t); return true;
    }, src, t);
    await new Promise(r => setTimeout(r, 60));
    await page.screenshot({ path: proj + '/mocks/' + tag + '_' + id + '.jpg', type: 'jpeg', quality: 86 });
  }
  await browser.close();
  console.log('done', tag, shots.length);
})().catch(e => { console.error(e); process.exit(1); });
