// Hamyon card-transfer payment end to end (needs qa_server with QA_HAMYON=1 and
// fake_hamyon.py): buy Premium -> transfer sheet shows card + exact amount ->
// money "arrives" (signed complete callback) -> sheet confirms, plan is Premium.
// Then a 2nd user buying at the same time gets a different amount, the lost-
// callback path (status check) delivers, and a cancel ends cleanly.
const { chromium } = require('playwright');
const fs = require('fs');
const crypto = require('crypto');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const API = 'http://localhost:18100/api';
const SHOP_ID = '12', SHOP_KEY = 'qa-shop-key';
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');

async function complete(order, status = 'paid') {
  const st = await (await fetch('http://127.0.0.1:18102/payment/status?payment_id=' + order.hpid)).json();
  const body = new URLSearchParams({ payment_id: order.hpid, order_id: order.id, shop_id: SHOP_ID, amount: String(st.amount),
    status, paid_at: String(Math.floor(Date.now() / 1000)), reason: 'timeout', sign: md5(SHOP_ID + order.hpid + st.amount + SHOP_KEY) });
  return fetch(API + '/payments/hamyon/complete', { method: 'POST', body });
}
const me = async (who) => (await fetch(API + '/auth/me', { headers: { Authorization: 'Bearer ' + U[who].token } })).json();

(async () => {
  const b = await chromium.launch();
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const mk = async (who) => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
    return { ctx, page };
  };

  // 1) happy path through the UI
  let { ctx, page } = await mk('f1@fidem.uz');
  let created = null;
  page.on('response', async (r) => { if (r.url().endsWith('/payments/create')) { try { created = await r.json(); } catch { /* ignore */ } } });
  await page.goto(APP + '/premium', { waitUntil: 'networkidle' });
  await page.click('[data-testid=buy-premium]');
  await page.waitForSelector('[data-testid=pay-sheet]', { timeout: 8000 }).catch(() => {});
  check('transfer sheet opens', await page.locator('[data-testid=pay-sheet]').count() === 1);
  const sheetText = await page.locator('[data-testid=pay-sheet]').innerText().catch(() => '');
  check('sheet shows the card number', sheetText.includes('8600 0000 0000 0001'));
  check('sheet shows the exact amount', created && sheetText.replace(/\s/g, '').includes(String(created.pay_amount)));
  check('sheet shows a countdown', /\d:\d\d/.test(sheetText));
  await page.screenshot({ path: __dirname + '/shots/pay_sheet.png' });
  // the fake server is looked up by our payment id (sent to Hamyon as order_id)
  const r1 = await complete({ id: created.id, hpid: await hpidFor(created.id) });
  check('signed complete callback accepted', r1.status === 200);
  await page.waitForSelector('[data-testid=pay-success]', { timeout: 10000 }).catch(() => {});
  check('sheet switches to "payment received"', await page.locator('[data-testid=pay-success]').count() === 1);
  await page.screenshot({ path: __dirname + '/shots/pay_success.png' });
  check('user is Premium now', (await me('f1@fidem.uz')).plan === 'premium');
  await ctx.close();

  // 2) two open payments with the same price get different amounts
  const mkPay = async (who) => (await fetch(API + '/payments/create', { method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + U[who].token },
    body: JSON.stringify({ purpose: 'premium', months: 1 }) })).json();
  const a = await mkPay('f2@fidem.uz');
  const c = await mkPay('f3@fidem.uz');
  check('same price, different amounts (' + a.pay_amount + ' / ' + c.pay_amount + ')', a.pay_amount && c.pay_amount && a.pay_amount !== c.pay_amount);

  // 3) lost callback: Hamyon says paid, the app's status poll delivers
  await fetch('http://127.0.0.1:18102/qa/pay', { method: 'POST', body: new URLSearchParams({ order_id: a.id }) });
  const s = await (await fetch(API + '/payments/status/' + a.id, { headers: { Authorization: 'Bearer ' + U['f2@fidem.uz'].token } })).json();
  check('status check delivers when the callback was lost', s.status === 'success' && (await me('f2@fidem.uz')).plan === 'premium');

  // 4) cancel from the sheet
  ({ ctx, page } = await mk('f4@fidem.uz'));
  await page.goto(APP + '/premium', { waitUntil: 'networkidle' });
  await page.click('[data-testid=buy-premium]');
  await page.waitForSelector('[data-testid=pay-cancel]', { timeout: 8000 }).catch(() => {});
  page.once('dialog', (d) => d.accept());
  await page.click('[data-testid=pay-cancel]');
  await page.waitForSelector('[data-testid=pay-ended]', { timeout: 8000 }).catch(() => {});
  check('cancel ends the payment', await page.locator('[data-testid=pay-ended]').count() === 1);
  check('cancelled user stays free', (await me('f4@fidem.uz')).plan !== 'premium');
  await ctx.close();

  // 5) forged callback is refused
  const forged = await fetch(API + '/payments/hamyon/complete', { method: 'POST', body: new URLSearchParams({
    payment_id: 'x', order_id: c.id, shop_id: SHOP_ID, amount: String(c.pay_amount), status: 'paid', sign: 'f'.repeat(32) }) });
  check('forged callback refused (403)', forged.status === 403 && (await me('f3@fidem.uz')).plan !== 'premium');

  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();

async function hpidFor(orderId) {
  const res = await fetch('http://127.0.0.1:18102/qa/find?order_id=' + orderId);
  return (await res.json()).payment_id;
}
