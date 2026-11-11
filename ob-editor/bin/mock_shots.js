// Screenshot each mock composition at its "settled" moment for the shot breakdown.
// node mock_shots.js EVENTS_RESOLVED.json PROJECT_DIR [ID ...]
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const fs = require('fs');
const [evPath, proj, ...only] = process.argv.slice(2);
const events = JSON.parse(fs.readFileSync(evPath, 'utf8')).events.filter(e => !only.length || only.includes(e.id));

const SIDE = new Set(['photo','equation','stat_ratio','stat_bars','stat_list','stat_columns','stat_count','stat_equals','proof','poster','study','chart_line','end','shots','bowl','meal','belly','tape','cycle']);
function settle(e) {
  const t = settle0(e);
  return SIDE.has(e.type) && !e.full ? Math.max(0.6, Math.min(t, e.dur - 0.6)) : t;  // never catch the exit slide (full cards have none)
}
function settle0(e) {
  if (e.settle_t != null) return e.settle_t;   // reel_cards (10-29) store their own: the last line landed
  const D = e.dur, last = a => (a && a.length ? Math.max(...a) : 0);
  const EXPL = new Set(['clip','photo_full','num','math','dose','coins','timeline','title','disclaimer','wall','versus','checklist','scissors','detector','find','slider','insert']);   // C4367 explainer cards
  if (e.type === 'scissors' && e.snip_only) return D - 0.1;
  if (e.type === 'photo_full' && e.anim === 'sponge') return Math.min(D - 0.1, ((e.at_t || {}).dissolve || 4) + 1.5);   // before the sponge slides out
  if (e.type === 'quote') return Math.max(0.6, D - 0.15);   // v4: lines land as he says them; shoot the finished card
  if (e.type === 'selfquote') return Math.min(D - 0.35, ((e.at_t || {}).q || 0.1) + 0.8);
  if (e.type === 'facequote') return Math.max(0.5, Math.min(D - 0.3, last(Object.values(e.at_t || {})) + 0.75));   // C4367 v4: every line landed, before the fade
  if (e.type === 'doc') return Math.min(D - (e.full ? 0.1 : 0.35), ((e.at_t || {}).hl || 0.6) + 1.0);   // the recap: shoot it after the scissors leave
  if (EXPL.has(e.type)) return Math.min(D - 0.1, Math.max(0.6, last(Object.values(e.at_t || {})), e.type === 'clip' ? (e.quote_at || 0) : 0) + 0.9
                                       + (e.type === 'num' && e.count !== false ? 0.6 : 0));   // a count-up runs ~1.1 s: shoot it finished
  switch (e.type) {
    case 'myths_overlay': return Math.min(D - 0.1, last(e.items_t) + 1.0);
    case 'photo_overlay': return Math.min(D - 0.35, last(e.items_t) + 0.6);
    case 'pills': return Math.min(D - 0.35, last(e.items_t) + 0.6);
    case 'shots': return Math.min(D - 0.1, last(e.shots_t) + 0.9);
    case 'bowl': return Math.min(D - 0.1, last(e.steps_t) + 1.9);
    case 'photo': return e.photos_t ? Math.min(D - 0.1, last(e.photos_t) + 0.7) : Math.min(D - 0.1, 1.2);
    case 'study': return Math.min(D - 0.6, (e.hl_t || 1.1) + 1.7);
    case 'chart_line': return Math.min(D - 0.6, Math.max(3.2, last(e.callouts_t) + 1.0));
    case 'myths': return Math.min(D - 0.1, last(e.items_t) + 1.0);
    case 'split': return Math.min(D - 0.5, last(e.items_t) + 0.5);
    case 'equation': return Math.min(D - 0.1, (e.right_t || D * 0.5) + 0.5);
    case 'stat_columns': return Math.min(D - 0.1, last(e.cols_t) + 0.6);
    case 'stat_count': return Math.min(D - 0.05, (e.to_t || D * 0.6) + 1.4);
    case 'stat_equals': return Math.min(D - 0.1, last(e.rows_t) + 0.5);
    case 'stat_bars': return Math.min(D - 0.1, Math.max(2.6, last(e.bars_t) + 1.6));
    case 'stat_list': case 'proof': return Math.min(D - 0.1, 2.6);
    case 'meal': return Math.min(D - 0.1, Math.max(last(e.rows_t), e.note_t || 0, last(e.foods_t), e.fx_t || 0) + 1.2);  // food plates and salt/steam land late
    case 'tape': return Math.min(D - 0.1, last(e.rows_t) + 0.8);
    case 'belly': return Math.min(D - 0.1, Math.max(last(e.labels_t) + 0.9, e.mode === 'mri' ? 2.8 : 0));
    case 'cycle': return Math.min(D - 0.1, Math.max(last(e.items_t), e.title_t || 0) + 1.2);  // the title can land after the last step
    case 'proof_quote': return Math.min(D - 0.1, 1.5);
    case 'poster': return D * 0.6;
    case 'end': return Math.min(D - 0.1, 1.6);
    default: return Math.min(D - 0.1, 1.2);
  }
}

// Reveal time of the first item that reuses an already-filled slot (non-flash photo_overlay), else null.
function wave2(e) {
  if (e.type !== 'photo_overlay' || (e.layout || '').startsWith('flash') || !e.items_t) return null;
  const seen = new Set();
  for (let i = 0; i < e.items.length; i++) {
    if (seen.has(e.items[i][1])) return e.items_t[i];
    seen.add(e.items[i][1]);
  }
  return null;
}

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 3840, height: 2160, deviceScaleFactor: 0.5 });
  for (const e of events) {
    const url = 'file://' + proj + '/compositions/' + e.id + '.mock.html';
    await page.goto(url, { waitUntil: 'load' });
    await page.evaluate(async () => { await document.fonts.ready; });
    const w2 = wave2(e);  // a photo_overlay second wave gets its own shot, taken just before it cuts in
    const shots = e.type === 'proof_pages' ? [[e.id, Math.max(1.6, (e.page2_t || e.dur / 2) - 0.45)], [e.id + 'b', Math.min(e.dur - 0.1, (e.page2_t || e.dur / 2) + 1.4)]]
                : w2 !== null ? [[e.id, Math.max(0.6, w2 - 0.15)], [e.id + '_w2', settle(e)]]
                : [[e.id, settle(e)]];
    for (const [name, t] of shots) {
      await page.evaluate(t => { window.__timelines.main.seek(t); return true; }, t);
      await new Promise(r => setTimeout(r, 120));
      await page.screenshot({ path: proj + '/mocks/' + name + '.jpg', type: 'jpeg', quality: 82 });
    }
    process.stdout.write(e.id + ' ');
  }
  await browser.close();
  console.log('\ndone', events.length);
})().catch(err => { console.error(err); process.exit(1); });
