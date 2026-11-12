// Referral page: the Premium-days bonus card, then the Me card hint.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['m1@fidem.uz'].token);
  await page.goto(APP + '/referral', { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid=ref-bonus-days]');
  const txt = await page.locator('[data-testid=ref-bonus-days]').innerText();
  check('bonus card shows days and cap', /\+2 kun Premium/.test(txt) && /0 \/ 14/.test(txt) && !txt.includes('{'));
  check('no horizontal scroll', await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
  await page.screenshot({ path: OUT + '/referral_bonus.png' });
  // a woman is paid in Boost, not Premium days (Premium is free for her)
  const her = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  her.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  await her.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['f2@fidem.uz'].token);
  await her.goto(APP + '/referral', { waitUntil: 'networkidle' });
  await her.waitForSelector('[data-testid=ref-bonus-days]');
  const wtxt = await her.locator('[data-testid=ref-bonus-days]').innerText();
  check('woman sees the Boost bonus and its cap', /\+3 kun/.test(wtxt) && /Boost/.test(wtxt) && /0 \/ 21/.test(wtxt) && !/Premium/.test(wtxt) && !wtxt.includes('{'));
  check('woman: no horizontal scroll', await her.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
  await her.screenshot({ path: OUT + '/referral_bonus_woman.png' });
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
