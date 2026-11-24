// Account flows through the real UI: forgot password, add email + password to a
// Telegram-style account, delete the account (wrong password must NOT sign the
// person out), and the public /delete-account page.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101', API = 'http://127.0.0.1:18100/api';
const MAIL = process.env.QA_MAIL_FILE || '/tmp/claude-0/qa_mail.jsonl';
const OUT = process.env.OUT || '/tmp/claude-0';
const lastCode = (to) => {
  const rows = fs.readFileSync(MAIL, 'utf8').trim().split('\n').map((l) => JSON.parse(l)).filter((m) => m.to === to);
  return rows.length ? rows[rows.length - 1].text.match(/\b(\d{6})\b/)[1] : null;
};
const post = (path, body, token) => fetch(API + path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: JSON.stringify(body) });
(async () => {
  let ok = true;
  const check = (n, c, extra = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (extra ? '  ' + extra : '')); if (!c) ok = false; };
  const b = await chromium.launch();
  const mk = async (token) => {
    const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
    page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
    await page.addInitScript((t) => { if (t) localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, token || '');
    return page;
  };
  const noScroll = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);

  // ---- 1. forgot password
  const email = 'm5@fidem.uz';
  const fp = await mk(null);
  await fp.goto(APP + '/auth', { waitUntil: 'networkidle' });
  await fp.click('[data-testid=btn-forgot]');
  await fp.fill('[data-testid=forgot-email]', email);
  await fp.click('[data-testid=forgot-submit]');
  await fp.waitForSelector('[data-testid=forgot-code]');
  const code = lastCode(email);
  check('a reset code was emailed', /^\d{6}$/.test(code || ''));
  await fp.fill('[data-testid=forgot-code]', code);
  await fp.fill('[data-testid=forgot-password]', 'Yangi#Parol77');
  await fp.screenshot({ path: OUT + '/account_forgot.png' });
  await fp.click('[data-testid=forgot-submit]');
  await fp.waitForURL((u) => !u.pathname.startsWith('/auth'), { timeout: 15000 }).catch(() => {});
  check('reset signs the person in', !new URL(fp.url()).pathname.startsWith('/auth'), fp.url());
  check('old password no longer works', (await post('/auth/login', { email, password: 'QaPass#2026' })).status === 401);
  check('new password works', (await post('/auth/login', { email, password: 'Yangi#Parol77' })).status === 200);
  check('weak password is refused on sign-up', (await post('/auth/register', { email: 'weak@fidem.uz', password: '1234', name: 'W' })).status === 400);

  // ---- 2. Telegram-style account adds an email + password
  const tg = await (await fetch(API + '/qa/telegram-user', { method: 'POST' })).json();
  const ep = await mk(tg.token);
  await ep.goto(APP + '/me/settings', { waitUntil: 'networkidle' });
  await ep.waitForSelector('[data-testid=email-login]');
  await ep.fill('[data-testid=email-login-email]', 'tg-person@fidem.uz');
  await ep.click('[data-testid=email-login-send]');
  await ep.waitForSelector('[data-testid=email-login-code]');
  await ep.fill('[data-testid=email-login-code]', lastCode('tg-person@fidem.uz'));
  await ep.fill('[data-testid=email-login-password]', 'Telegram#Parol1');
  await ep.screenshot({ path: OUT + '/account_email.png' });
  await ep.click('[data-testid=email-login-confirm]');
  await ep.waitForSelector('[data-testid=email-login-done]');
  check('email is attached and shown as verified', /tg-person@fidem.uz/.test(await ep.locator('[data-testid=email-login-done]').innerText()));
  const relog = await post('/auth/login', { email: 'tg-person@fidem.uz', password: 'Telegram#Parol1' });
  check('the SAME account now signs in with email + password', relog.status === 200 && (await relog.json()).user_id === tg.id);
  check('settings: no horizontal scroll', await noScroll(ep));

  // ---- 3. deleting an account
  const email6 = 'm6@fidem.uz';
  const dp = await mk(U[email6].token);
  await dp.goto(APP + '/me/settings', { waitUntil: 'networkidle' });
  await dp.click('[data-testid=acc-delete-open]');
  await dp.waitForSelector('[data-testid=acc-delete-word]');
  check('confirm button is disabled until the word is typed', await dp.locator('[data-testid=acc-delete-confirm]').isDisabled());
  await dp.fill('[data-testid=acc-delete-word]', 'delete');
  await dp.fill('[data-testid=acc-delete-password]', 'wrong-password');
  await dp.screenshot({ path: OUT + '/account_delete.png' });
  await dp.click('[data-testid=acc-delete-confirm]');
  await dp.waitForTimeout(1200);
  check('wrong password: still on the page and still signed in', dp.url().includes('/me/settings') && !!(await dp.evaluate(() => localStorage.getItem('fidem_token'))));
  check('the account still exists after a wrong password', (await post('/auth/login', { email: email6, password: 'QaPass#2026' })).status === 200);
  await dp.fill('[data-testid=acc-delete-password]', 'QaPass#2026');
  await dp.click('[data-testid=acc-delete-confirm]');
  await dp.waitForURL(/\/welcome/, { timeout: 15000 }).catch(() => {});
  check('after deleting the app returns to the welcome page', dp.url().includes('/welcome'), dp.url());
  await dp.waitForLoadState('networkidle').catch(() => {});
  await dp.waitForTimeout(1500);
  // (the welcome page makes a fresh, empty cache of its own; what matters is that nothing of the person is left)
  check('this device keeps no session and no trace of the person', await dp.evaluate(([id, name]) => {
    if (localStorage.getItem('fidem_token')) return false;
    const cache = localStorage.getItem('fidem-query-cache') || '';
    return !cache.includes(id) && !cache.includes(name);
  }, [U[email6].id, 'Rustam']));
  check('the deleted account cannot sign in', (await post('/auth/login', { email: email6, password: 'QaPass#2026' })).status === 401);
  const stale = await fetch(API + '/auth/me', { headers: { Authorization: 'Bearer ' + U[email6].token } });
  check('its old token is refused (401)', stale.status === 401);
  const hidden = await fetch(API + '/candidates?limit=60', { headers: { Authorization: 'Bearer ' + U['qa@fidem.uz'].token } });
  check('and it is gone from everyone else\'s feed', !(await hidden.json()).some((c) => c.id === U[email6].id));

  // ---- 4. the public page
  const pp = await mk(null);
  await pp.goto(APP + '/delete-account', { waitUntil: 'networkidle' });
  await pp.waitForSelector('[data-testid=delete-account-page]');
  const txt = await pp.locator('[data-testid=delete-account-page]').innerText();
  check('public page explains the steps and offers sign-in', /Hisobni o'chirish/.test(txt) && (await pp.locator('[data-testid=delete-account-signin]').count()) === 1);
  check('public page: no horizontal scroll', await noScroll(pp));
  await pp.screenshot({ path: OUT + '/account_public.png' });

  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
