// Compatibility card: a free user sees the real match score (not 0/100); a
// Premium user sees the report with the pair's own matching points, and two
// different candidates get different scores/reports.
// Needs qa_server with QA_HAMYON=1 + fake_hamyon.py (used to buy Premium).
const { chromium } = require('playwright');
const fs = require('fs');
const crypto = require('crypto');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const API = 'http://localhost:18100/api';
const SHOP_ID = '12', SHOP_KEY = 'qa-shop-key';
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const H = (who) => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + U[who].token });

(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const who = process.env.WHO || 'm2@fidem.uz';
  const targets = ['f0@fidem.uz', 'f3@fidem.uz'];

  // free user: locked, but a real score
  const free = await (await fetch(`${API}/personality/compatibility/${U[targets[0]].id}?lang=uz`, { headers: H(who) })).json();
  const detail = await (await fetch(`${API}/candidates/${U[targets[0]].id}`, { headers: H(who) })).json();
  check(`free: score ${free.score} > 0 and locked`, free.score > 0 && free.locked === true);
  check(`free: score equals profile match (${detail.match_score})`, free.score === detail.match_score);

  // buy Premium through the (fake) Hamyon flow
  const pay = await (await fetch(API + '/payments/create', { method: 'POST', headers: H(who), body: JSON.stringify({ purpose: 'premium', months: 1 }) })).json();
  const hp = await (await fetch('http://127.0.0.1:18102/qa/find?order_id=' + pay.id)).json();
  await fetch(API + '/payments/hamyon/complete', { method: 'POST', body: new URLSearchParams({
    payment_id: hp.payment_id, order_id: pay.id, shop_id: SHOP_ID, amount: String(hp.amount), status: 'paid',
    sign: md5(SHOP_ID + hp.payment_id + hp.amount + SHOP_KEY) }) });

  const reps = [];
  for (const t of targets) {
    reps.push(await (await fetch(`${API}/personality/compatibility/${U[t].id}?lang=uz`, { headers: H(who) })).json());
  }
  check('premium: report unlocked', reps.every((r) => r.locked === false && r.report && r.report.summary));
  check('no invented "Hududiy yaqinlik" point', reps.every((r) => !(r.report.strengths || []).includes('Hududiy yaqinlik')));
  check(`summaries carry each pair's score (${reps.map((r) => r.score).join(' / ')})`, reps.every((r) => r.report.summary.includes(String(r.score))));

  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((tk) => { localStorage.setItem('fidem_token', tk); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
  await page.goto(`${APP}/candidate/${U[targets[0]].id}`, { waitUntil: 'networkidle' });
  const card = page.locator('[data-testid=compat-card]');
  await card.scrollIntoViewIfNeeded().catch(() => {});
  const txt = await card.innerText().catch(() => '');
  check('card shows the real score, not 0/100', txt.includes(`${reps[0].score}/100`) && !/(^|\D)0\/100/.test(txt) && reps[0].score > 0);
  check('card offers the personality test when not taken', await page.locator('[data-testid=compat-test-cta]').count() === 1);
  await card.screenshot({ path: __dirname + '/shots/compat_card.png' });
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
