// node html2pdf.js IN.html OUT.pdf  -> landscape Letter, light theme, backgrounds on
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: true }); const p = await b.newPage();
  await p.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
  await p.goto('file://' + process.argv[2], { waitUntil: 'load', timeout: 180000 });
  await p.addStyleTag({ content: 'tr{break-inside:avoid} .tablewrap{overflow:visible!important} table{min-width:0!important} th{position:static!important} audio{display:none}' });
  await p.pdf({ path: process.argv[3], format: 'Letter', landscape: true, printBackground: true, scale: 0.72,
                margin: { top: '0.35in', bottom: '0.35in', left: '0.3in', right: '0.3in' } });
  await b.close();
})().catch(e => { console.error(e.message); process.exit(1); });
