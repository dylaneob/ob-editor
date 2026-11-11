// Print the breakdown HTML to a phone-sized PDF (480 x 1040 px pages, set by the page's print CSS).
// node lecture_breakdown_pdf.js IN.html OUT.pdf
const puppeteer = require('/Users/YOU/ob-editor/node_modules/puppeteer');
const [inp, out] = process.argv.slice(2);
(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('file://' + inp, { waitUntil: 'load' });
  await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log('pdf', out);
})().catch(e => { console.error(e); process.exit(1); });
