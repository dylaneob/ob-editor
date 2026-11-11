// Proof frames: screenshot one mock composition at several times and tile them, to check an animation frame by frame.
// node frames_at.js HF_DIR EVENT_ID t1,t2,... OUT.jpg   (HF_DIR/compositions/<id>.mock.html; times in card seconds)
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const { execFileSync } = require('child_process');
const [hf, id, times, out] = process.argv.slice(2);
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 3840, height: 2160, deviceScaleFactor: 0.25 });
  await page.goto('file://' + hf + '/compositions/' + id + '.mock.html', { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  const files = [];
  for (const t of times.split(',').map(Number)) {
    await page.evaluate(t => { window.__timelines.main.seek(t); return true; }, t);
    await new Promise(r => setTimeout(r, 120));
    const f = `${out}.${t.toFixed(2)}.png`;
    await page.screenshot({ path: f });
    files.push([t, f]);
  }
  await browser.close();
  // tile with labels (python/PIL)
  const py = `import sys
from PIL import Image, ImageDraw, ImageFont
fs = sys.argv[2:]; ims = [Image.open(f) for f in fs]; w, h = ims[0].size; cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
s = Image.new('RGB', (cols * w, rows * h)); d = ImageDraw.Draw(s); f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
for i, (p, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * w, (i // cols) * h; s.paste(im, (x, y)); t = p.rsplit('.', 2)[-2]
    d.rectangle((x, y, x + 120, y + 34), fill=(0, 0, 0)); d.text((x + 6, y + 3), 't=' + p.split('.png')[0].split('.', 1)[1][-6:], font=f, fill=(255, 220, 0))
s.save(sys.argv[1], quality=85)
import os
[os.remove(p) for p in fs]`;
  execFileSync('python3', ['-I', '-c', py, out, ...files.map(f => f[1])]);
  console.log('frames', out);
})().catch(e => { console.error(e); process.exit(1); });
