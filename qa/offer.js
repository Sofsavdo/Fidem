// New offer: 1 day / 15 days / 1 month Premium, women free during the launch
// promo, upsells open the quick picker. Needs qa_server with QA_HAMYON=1.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const b = await chromium.launch();
  const mk = async (who) => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
    return { ctx, page };
  };
  const digits = (s) => (s || '').replace(/\D/g, '');

  // man: three periods, 15 days preselected, CTA follows the choice
  let { ctx, page } = await mk('m3@fidem.uz');
  await page.goto(APP + '/premium', { waitUntil: 'networkidle' });
  check('three periods shown', await page.locator('[data-testid^=period-]').count() === 3);
  let cta = await page.locator('[data-testid=buy-premium]').innerText();
  check('15 days preselected (49 900)', digits(cta).includes('49900'));
  await page.click('[data-testid=period-1]');
  cta = await page.locator('[data-testid=buy-premium]').innerText();
  check('1 day -> 9 900', digits(cta).includes('9900') && !digits(cta).includes('49900'));
  check('men see that women are active', await page.locator('[data-testid=women-active-note]').count() === 1);
  await page.screenshot({ path: __dirname + '/shots/offer_men.png', fullPage: true });
  let created = null;
  page.on('response', async (r) => { if (r.url().endsWith('/payments/create')) { try { created = await r.json(); } catch { /* */ } } });
  await page.click('[data-testid=buy-premium]');
  await page.waitForSelector('[data-testid=pay-sheet]', { timeout: 8000 }).catch(() => {});
  check('1-day purchase opens the transfer sheet for 9 900', created && created.amount === 9900);
  await ctx.close();

  // upsell opens the picker without leaving the screen
  ({ ctx, page } = await mk('m4@fidem.uz'));
  await page.goto(APP + '/saved?tab=likes', { waitUntil: 'networkidle' });
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('fidem:premium-picker', { detail: { source: 'test' } })));
  await page.waitForSelector('[data-testid=premium-picker]', { timeout: 5000 }).catch(() => {});
  check('picker opens over the current screen', await page.locator('[data-testid=premium-picker]').count() === 1 && page.url().includes('/saved'));
  await page.screenshot({ path: __dirname + '/shots/offer_picker.png' });
  await ctx.close();

  // woman: Premium is free, no buy button, badge on Me
  ({ ctx, page } = await mk('f2@fidem.uz'));
  await page.goto(APP + '/premium', { waitUntil: 'networkidle' });
  check('women see "Premium free" card', await page.locator('[data-testid=women-free-card]').count() === 1);
  check('women get no buy button', await page.locator('[data-testid=buy-premium]').count() === 0);
  await page.screenshot({ path: __dirname + '/shots/offer_women.png', fullPage: true });
  await page.click('[data-testid=nav-me]').catch(() => {});
  await page.waitForTimeout(800);
  check('Me shows the free badge', await page.locator('[data-testid=women-free-pill]').count() === 1);
  await ctx.close();
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
