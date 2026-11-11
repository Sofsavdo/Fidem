// Family contact button: a Premium user without a family number on file gets
// a small form (not a dead "error" toast), saves it and the request goes out.
const { chromium } = require('playwright');
const fs = require('fs');
const crypto = require('crypto');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const API = 'http://localhost:18100/api';
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const H = (who) => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + U[who].token });
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const who = process.env.WHO || 'm4@fidem.uz', target = 'f4@fidem.uz';
  // make the asker Premium through the (fake) Hamyon flow
  const pay = await (await fetch(API + '/payments/create', { method: 'POST', headers: H(who), body: JSON.stringify({ purpose: 'premium', months: 1 }) })).json();
  const hp = await (await fetch('http://127.0.0.1:18102/qa/find?order_id=' + pay.id)).json();
  await fetch(API + '/payments/hamyon/complete', { method: 'POST', body: new URLSearchParams({ payment_id: hp.payment_id, order_id: pay.id, shop_id: '12', amount: String(hp.amount), status: 'paid', sign: md5('12' + hp.payment_id + hp.amount + 'qa-shop-key') }) });

  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((tk) => { localStorage.setItem('fidem_token', tk); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
  await page.goto(`${APP}/candidate/${U[target].id}`, { waitUntil: 'networkidle' });
  await page.click('[data-testid=profile-family]');
  await page.waitForSelector('[data-testid=family-sheet]', { timeout: 5000 }).catch(() => {});
  check('missing family number opens the form', await page.locator('[data-testid=family-sheet]').count() === 1);
  await page.screenshot({ path: __dirname + '/shots/family_sheet.png' });
  await page.fill('[data-testid=family-phone]', '+998 90 123 45 67');
  await page.fill('[data-testid=family-name]', 'Onam');
  await page.click('[data-testid=family-save-send]');
  await page.waitForTimeout(1200);
  const mine = await (await fetch(API + '/family/mine', { headers: H(who) })).json();
  check('request was sent', (mine.sent || []).some((r) => r.to_user_id === U[target].id && r.status === 'pending'));
  await page.click('[data-testid=profile-family]');
  await page.waitForTimeout(800);
  const toastTxt = await page.locator('[data-sonner-toast]').allInnerTexts();
  check('second tap says it was already sent', toastTxt.some((x) => /allaqachon/.test(x)));
  // the (free) receiver can accept after adding their number
  await fetch(API + '/family/contacts', { method: 'PATCH', headers: H(target), body: JSON.stringify({ parent_phone: '+998907654321', parent_name: 'Otam' }) });
  const rid = (mine.sent || []).find((r) => r.to_user_id === U[target].id).id;
  const acc = await fetch(API + '/family/respond/' + rid, { method: 'POST', headers: H(target), body: JSON.stringify({ accept: true }) });
  check('free receiver can accept', acc.status === 200);
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
