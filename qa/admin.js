// Admin panel audit: open every section on a phone-sized screen, collect console
// errors, failing API calls, raw i18n keys / undefined / NaN, horizontal overflow,
// and a screenshot per section (qa/shots/admin_<id>.png).
const { chromium } = require('playwright');
const fs = require('fs');
const APP = 'http://127.0.0.1:18101';
const IDS = ['ceo','ai','growth','revenue','dashboard','analytics','users','broadcast','anons','payments','p2p','verifications','withdrawals','referrals','messages','concierge','fraud','reports','auditlog'];
(async () => {
  const r = await fetch('http://127.0.0.1:18100/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'admin@fidem.uz', password: 'AdminQa#2026' }) });
  const token = (await r.json()).token;
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  let errs = [], bad = [];
  page.on('console', (m) => { if (m.type() === 'error' && !/ERR_(TUNNEL|FAILED|INTERNET|NAME)/.test(m.text())) errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)));
  page.on('response', (res) => { if (res.status() >= 400 && res.url().includes('18100')) bad.push(`${res.status()} ${res.request().method()} ${res.url().replace('http://localhost:18100', '').split('?')[0]}`); });
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, token);
  await page.goto(APP + '/admin', { waitUntil: 'networkidle' });
  const report = [];
  await page.click('[data-testid=admin-mobile-menu-open]');
  report.push({ id: 'menu: no gift shop entry', errs: [], api: [], over: 0, bad: '', keys: [], legacy: (await page.locator('[data-testid=admin-mobile-tab-giftshop]').count()) ? ['giftshop tab still shown'] : [] });
  await page.click('[data-testid=admin-mobile-menu-close]');
  for (const id of IDS) {
    errs = []; bad = [];
    await page.click('[data-testid=admin-mobile-menu-open]');
    await page.click(`[data-testid=admin-mobile-tab-${id}]`);
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(700);
    const info = await page.evaluate(() => {
      const t = document.body.innerText || '';
      const keys = (t.match(/\b[a-z]+(?:_[a-z0-9]+){1,}\b/g) || []).filter((k) => !/^(qa|f\d|m\d)/.test(k)).slice(0, 6);
      return { over: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        bad: (t.match(/.{0,20}(undefined|NaN|\[object Object\]).{0,10}/) || [''])[0], keys, len: t.length,
        legacy: (t.match(/.{0,25}\b(VIP|Click|CLICK|P2P|Concierge|Standard)\b.{0,25}/g) || []).slice(0, 4) };
    });
    await page.screenshot({ path: `${__dirname}/shots/admin_${id}.png`, fullPage: false });
    report.push({ id, errs: [...new Set(errs)].slice(0, 3), api: [...new Set(bad)].slice(0, 4), ...info });
  }
  for (const x of report) {
    const p = [];
    if (x.errs.length) p.push('console: ' + x.errs.join(' || '));
    if (x.api.length) p.push('api: ' + x.api.join(', '));
    if (x.over > 1) p.push('h-overflow ' + x.over + 'px');
    if (x.bad) p.push('bad-text: ' + x.bad);
    if (x.keys.length) p.push('raw-keys?: ' + x.keys.join(','));
    if (x.legacy.length) p.push('legacy wording: ' + x.legacy.join(' | '));
    console.log((p.length ? '!! ' : 'ok ') + x.id + (p.length ? '\n     ' + p.join('\n     ') : ''));
  }
  await b.close();
})();
