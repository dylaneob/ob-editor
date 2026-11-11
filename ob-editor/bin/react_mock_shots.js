// node react_mock_shots.js EVENTS.json PROJECT_DIR [ID ...]  -> mocks/<id>.jpg (+ <id>b/<id>c for multi-phase cards)
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [evPath, proj, ...only] = process.argv.slice(2);
const events = JSON.parse(fs.readFileSync(evPath, 'utf8')).events.filter(e => !only.length || only.includes(e.id));
function shots(e) {
  const D = e.dur;
  switch (e.type) {
    case 'ba': { const sw = Math.min(2.6, D * 0.35); return [[e.id, 1.0], [e.id + 'b', Math.min(D - 0.1, sw + 1.4)]]; }
    case 'montage': { const n = e.items_r.length, s = D / n; return [[e.id, s * 0.5], [e.id + 'b', s * 3.5], [e.id + 'c', s * 6.5]]; }
    case 'cite': return [[e.id, Math.min(D - 0.1, 2.2)]];
    case 'list': return [[e.id, Math.max(0.5, D - 0.75)]];
    case 'end': return [[e.id, Math.min(D - 0.1, 1.6)]];
    case 'study': return [[e.id, Math.min(D - 0.6, 4.2)]];
    case 'chart': return [[e.id, Math.max(0.5, D - 0.7)]];
    case 'overlay': {
      const ts = e.items_t, n = ts.length;
      if (e.layout === 'flash') return [[e.id, ts[Math.floor(n * 0.2)] + 0.12], [e.id + 'b', ts[Math.floor(n * 0.55)] + 0.12], [e.id + 'c', ts[Math.floor(n * 0.9)] + 0.12]];
      const waves = []; let cur = [ts[0]];   // one shot after each wave of images lands
      for (let i = 1; i < n; i++) { if (ts[i] - ts[i - 1] > 1.0) { waves.push(cur); cur = []; } cur.push(ts[i]); }
      waves.push(cur);
      return waves.slice(0, 3).map((w, k) => [e.id + ['', 'b', 'c'][k], Math.min(D - 0.35, w[w.length - 1] + 0.7)]);
    }
    case 'stamp': case 'title': return [[e.id, Math.min(D - 0.5, 0.9)]];
    default: return [[e.id, Math.min(D - 0.45, 1.1)]];
  }
}
(async () => {
  const b = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const p = await b.newPage(); p.setDefaultNavigationTimeout(180000); await p.setViewport({ width: 3840, height: 2160, deviceScaleFactor: 0.5 });
  for (const e of events) {
    await p.goto('file://' + proj + '/compositions/' + e.id + '.mock.html', { waitUntil: 'load' });
    await p.evaluate(async () => { await document.fonts.ready; });
    for (const [name, t] of shots(e)) {
      await p.evaluate(t => { window.__timelines.main.seek(t); return true; }, t);
      await new Promise(r => setTimeout(r, 120));
      await p.screenshot({ path: proj + '/mocks/' + name + '.jpg', type: 'jpeg', quality: 82 });
    }
    process.stdout.write(e.id + ' ');
  }
  await b.close(); console.log('\ndone', events.length);
})().catch(err => { console.error(err); process.exit(1); });
