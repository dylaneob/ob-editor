// Grid cover for a lecture reel: the graded frame + the cover line in the reel's own yellow hook style.
// node lecture_cover.js BG.jpg "LINE 1|LINE 2" OUT.jpg FONTS_DIR
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [bg, text, out, fonts] = process.argv.slice(2);
const lines = text.split('|').map(l => `<span>${l.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</span>`).join('<br>');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: DINC; src: url('file://${fonts}/DINCondensed-Bold.ttf'); }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; height: 1920px; overflow: hidden; background: #000; }
img { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }
.block { position: absolute; left: 0; right: 0; top: 980px; text-align: center; }
.kick { display: inline-flex; gap: 14px; align-items: center; background: rgba(12,12,12,.9); color: #fff; border-radius: 16px;
        padding: 14px 24px 9px; font-family: DINC; font-size: 46px; letter-spacing: 2px; margin-bottom: 20px; }
.kick i { width: 16px; height: 16px; border-radius: 50%; background: #F7DC3A; display: inline-block; margin-top: -5px; }
.hook span { display: inline; background: #F7DC3A; color: #111; font-family: DINC; font-size: 150px; line-height: 1.12;
             padding: 12px 28px 0; box-decoration-break: clone; -webkit-box-decoration-break: clone; box-shadow: 0 22px 60px rgba(0,0,0,.5); }
</style></head><body><img src="file://${bg}"><div class="block"><div class="kick"><i></i>TODAY'S LECTURE</div><div class="hook">${lines}</div></div></body></html>`;
(async () => {
  const b = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const p = await b.newPage(); await p.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  const tmp = out + '.html'; fs.writeFileSync(tmp, html);
  await p.goto('file://' + tmp, { waitUntil: 'load' }); await p.evaluate(async () => { await document.fonts.ready; return true; });
  await p.screenshot({ path: out, type: 'jpeg', quality: 93 }); fs.unlinkSync(tmp);
  await b.close(); console.log('cover', out);
})().catch(e => { console.error(e); process.exit(1); });
