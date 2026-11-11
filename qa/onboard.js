const { chromium } = require('playwright'); const fs = require('fs');
const APP = 'http://127.0.0.1:18101';
(async () => { try {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage(); const errs = [], apis = [];
  page.on('console', m => { if (m.type() === 'error' && !/ERR_(FAILED|TUNNEL|INTERNET|NAME)/.test(m.text())) errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + String(e).slice(0, 160)));
  page.on('response', r => { if (r.url().includes('18100') && r.status() >= 400) apis.push(`${r.status()} ${r.request().method()} ${r.url().split('18100')[1].split('?')[0]}`); });
  await page.addInitScript(() => { localStorage.removeItem('fidem_token'); localStorage.setItem('fidem_lang', 'uz'); });
  const email = `ob${Date.now() % 100000}@fidem.uz`;
  const t0 = Date.now();
  await page.goto(APP + '/auth', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '' + __dirname + '/shots/ob_00_auth.png' });
  await page.click('[data-testid=btn-mode-register]').catch(() => {});
  await page.fill('[data-testid=input-name]', 'Yangi Foydalanuvchi').catch(() => {});
  await page.fill('[data-testid=input-email]', email); await page.fill('[data-testid=input-password]', 'QaPass#2026');
  await page.screenshot({ path: '' + __dirname + '/shots/ob_01_register.png' });
  await page.click('[data-testid=btn-submit]'); await page.waitForTimeout(1800);
  console.log('after register url:', page.url());
  const log = [];
  for (let i = 0; i < 16; i++) {
    await page.waitForTimeout(500);
    const step = await page.evaluate(() => { const s = document.querySelector('[data-testid^="onboarding-step-"],[data-testid=consent-screen]'); return s ? s.getAttribute('data-testid') : 'none'; });
    const tids = await page.evaluate(() => [...document.querySelectorAll('[data-testid]')].map(e => e.getAttribute('data-testid')).filter(x => /^(ob|consent)/.test(x)));
    await page.screenshot({ path: `${__dirname}/shots/ob_${String(i + 2).padStart(2, '0')}_${step}.png` });
    log.push(`${step}: ${tids.join(' ')}`);
    // consent checkboxes
    for (const k of ['terms', 'privacy', 'intent']) { const c = page.locator(`[data-testid=consent-${k}]`); if (await c.count()) await c.first().click({ position: { x: 14, y: 14 } }).catch(() => {}); }
    
    const pick = async (id, text) => { const sel = page.locator(`[data-testid=${id}]`); if (!(await sel.count())) return; if (await sel.first().isDisabled().catch(() => false)) return; await sel.first().click().catch(() => {}); await page.waitForTimeout(250); const panel = page.locator(`[data-testid=${id}-panel] button, [data-testid=${id}-panel] [role=option], [data-testid=${id}-panel] li`); if (await panel.count()) { const t = text ? panel.filter({ hasText: text }) : panel; await (await t.count() ? t : panel).first().click().catch(() => {}); } await page.waitForTimeout(250); };
    await pick('ob-country', /Uzbekistan|O.zbekiston|Узбекистан/); await pick('ob-region'); await pick('ob-religion'); await pick('ob-searchcountry', /Uzbekistan|O.zbekiston|Узбекистан/); await pick('ob-searchregion');
    const fillIf = async (id, v) => { const l = page.locator(`[data-testid=${id}]`); if (await l.count()) await l.first().fill(v).catch(() => {}); };
    await fillIf('ob-name', 'Yangi Foydalanuvchi'); await fillIf('ob-height', '175'); await fillIf('ob-weight', '70'); await fillIf('ob-education', 'Oliy');
    await fillIf('ob-profession', 'Dasturchi'); await fillIf('ob-bio', 'Oilaga e\'tiborli, jiddiy.'); await fillIf('ob-lookingfor', 'Jiddiy munosabat'); await fillIf('ob-district', 'Yunusobod');
    await fillIf('ob-birth', '1994-05-05'); await fillIf('ob-agemin', '20'); await fillIf('ob-agemax', '40'); await fillIf('ob-childcount', '0');
    for (const o of ['ob-gender-male', 'ob-marital-single', 'ob-haschildren-false', 'ob-haschildren-no', 'ob-smoking-no', 'ob-alcohol-no', 'ob-relocation-false', 'ob-relocation-no']) { const l = page.locator(`[data-testid=${o}]`); if (await l.count()) await l.first().click().catch(() => {}); }
    const fileIn = page.locator('input[type=file]'); if (await fileIn.count()) { await fileIn.first().setInputFiles(__dirname + '/face.png').catch(() => {}); await page.waitForTimeout(1500); }
    const sel = page.locator('select'); for (let j = 0; j < await sel.count(); j++) { const opts = await sel.nth(j).locator('option').allTextContents(); if (opts.length > 1) await sel.nth(j).selectOption({ index: 1 }).catch(() => {}); }
    const nxt = page.locator('[data-testid=ob-next],[data-testid=consent-continue]'); if (!(await nxt.count())) break;
    await nxt.first().click().catch(() => {}); await page.waitForTimeout(700);
    if (!/onboarding/.test(page.url())) { console.log('left onboarding ->', page.url()); break; }
  }
  console.log(log.join('\n')); console.log('final url:', page.url(), 'elapsed(s):', ((Date.now() - t0) / 1000).toFixed(0));
  console.log('console errors:', [...new Set(errs)].slice(0, 5)); console.log('api 4xx/5xx:', [...new Set(apis)].slice(0, 8));
  await page.screenshot({ path: '' + __dirname + '/shots/ob_99_end.png' }); await b.close();
} catch (e) { console.log("SCRIPT ERROR:", String(e).slice(0,300)); } })();
