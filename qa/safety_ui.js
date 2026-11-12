// Browser check of the anti-fraud screens: gesture selfie, chat safety line,
// selfie gate for unverified women, contact typed -> exchange panel,
// incoming exchange request -> accept -> contacts shown.
// Run on a fresh seed (before qa/safety.py, which hides some profiles).
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const API = 'http://127.0.0.1:18100/api';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const b = await chromium.launch();
  const mk = async (who, lang = 'uz') => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
    await page.addInitScript(([t, l]) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', l); }, [U[who].token, lang]);
    return { ctx, page };
  };

  // unverified woman: gesture selfie on /verification, gate in chat, card on /premium
  let { ctx, page } = await mk('f6@fidem.uz');
  await page.goto(APP + '/verification', { waitUntil: 'networkidle' });
  check('women note shown', await page.locator('[data-testid=verify-women-note]').count() === 1);
  await page.click('[data-testid=verify-upload-selfie]');
  await page.waitForSelector('[data-testid=selfie-gesture]');
  const g = await page.locator('[data-testid=selfie-gesture]').innerText();
  check('gesture shown: ' + g.split('\n')[1], g.length > 20);
  check('front camera input', (await page.locator('[data-testid=verify-file-selfie]').getAttribute('capture')) === 'user');
  await page.screenshot({ path: OUT + '/ui-selfie.png' });
  await page.goto(APP + '/premium', { waitUntil: 'networkidle' });
  check('premium: selfie card for unverified woman', await page.locator('[data-testid=women-needs-selfie]').count() === 1);
  await page.goto(APP + '/chat/' + U['m0@fidem.uz'].id, { waitUntil: 'networkidle' });
  check('chat: selfie gate shown', await page.locator('[data-testid=chat-selfie-gate]').count() === 1);
  await page.screenshot({ path: OUT + '/ui-chat-gate.png' });
  await ctx.close();

  // verified premium man: safety line, typed contact opens the exchange panel
  const adm = (await (await fetch(API + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'admin@fidem.uz', password: 'AdminQa#2026' }) })).json()).token;
  const H = (t) => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + t });
  await fetch(`${API}/admin/users/${U['m1@fidem.uz'].id}`, { method: 'PATCH', headers: H(adm), body: JSON.stringify({ plan: 'premium' }) });
  ({ ctx, page } = await mk('m1@fidem.uz'));
  await page.goto(APP + '/chat/' + U['f3@fidem.uz'].id, { waitUntil: 'networkidle' });
  check('chat: safety line', (await page.locator('[data-testid=chat-safety]').innerText()).includes('pul'));
  await page.fill('[data-testid=chat-input]', 'telegramim @bobur_uz');
  await page.click('[data-testid=chat-send]');
  await page.waitForSelector('[data-testid=cx-panel]');
  check('typed contact kept in the input', (await page.inputValue('[data-testid=chat-input]')).includes('@bobur_uz'));
  check('exchange panel lists the conditions', (await page.locator('[data-testid=cx-panel] li').count()) === 5);
  check('request disabled before 10+10 messages', await page.locator('[data-testid=cx-request]').isDisabled());
  await page.screenshot({ path: OUT + '/ui-cx-panel.png' });
  await page.fill('[data-testid=chat-input]', 'kartamga pul tashlab bering');
  await page.click('[data-testid=chat-send]');
  await page.waitForTimeout(1200);
  check('money request toast', (await page.locator('[data-sonner-toast]').allInnerTexts()).join(' ').includes('Pul yoki karta'));
  await ctx.close();

  // incoming request in the UI: m4 (made premium + verified) asks f4 after 10+10
  await fetch(`${API}/admin/users/${U['m4@fidem.uz'].id}`, { method: 'PATCH', headers: H(adm), body: JSON.stringify({ plan: 'premium', verified_selfie: true }) });
  for (const [w, tg] of [['m4@fidem.uz', 'jasur_test'], ['f4@fidem.uz', 'sevara_test']]) {
    await fetch(`${API}/profile`, { method: 'PATCH', headers: H(U[w].token), body: JSON.stringify({ contact_telegram: tg }) });
  }
  for (let i = 0; i < 10; i++) {
    await fetch(`${API}/messages/send`, { method: 'POST', headers: H(U['m4@fidem.uz'].token), body: JSON.stringify({ to_user_id: U['f4@fidem.uz'].id, text: 'savol ' + i }) });
    await fetch(`${API}/messages/send`, { method: 'POST', headers: H(U['f4@fidem.uz'].token), body: JSON.stringify({ to_user_id: U['m4@fidem.uz'].id, text: 'javob ' + i }) });
  }
  const req = await fetch(`${API}/chat/contact-exchange/${U['f4@fidem.uz'].id}`, { method: 'POST', headers: H(U['m4@fidem.uz'].token) });
  check('API request ok', req.status === 200);
  ({ ctx, page } = await mk('f4@fidem.uz', 'ru'));
  await page.goto(APP + '/chat/' + U['m4@fidem.uz'].id, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid=cx-incoming]');
  check('incoming request text', /kontakt almashish|обменяться/.test(await page.locator('[data-testid=cx-incoming]').innerText()));
  await page.screenshot({ path: OUT + '/ui-cx-incoming.png' });
  await page.click('[data-testid=cx-accept]');
  await page.waitForSelector('[data-testid=cx-contacts]');
  check('accepted: his Telegram shown', (await page.locator('[data-testid=cx-contacts]').innerText()).includes('@jasur_test'));
  await page.screenshot({ path: OUT + '/ui-cx-accepted.png' });
  await ctx.close();

  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
