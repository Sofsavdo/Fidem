const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const publicRoutes = (process.argv[5]==='admin') ? [] : ['/welcome', '/about', '/faq', '/terms', '/privacy', '/auth'];
const authRoutes = (process.argv[5]==='admin') ? ['/admin'] : ['/', '/candidate/__F0__', '/messages', '/chat/__F0__', '/saved', '/saved?tab=viewers', '/saved?tab=interested', '/me', '/me/settings', '/privacy-center', '/announcements', '/gifts', '/premium?tab=plans', '/premium?tab=balance', '/settings', '/notifications', '/personality', '/prompts', '/stories', '/withdrawals', '/family', '/concierge', '/verification', '/referral', '/rankings'];
const who = process.argv[2] || 'qa@fidem.uz', lang = process.argv[3] || 'uz', tag = process.argv[4] || 'run';
const shots = process.argv[5] === 'shots' || process.argv[5] === 'admin';
const f0 = U['f0@fidem.uz'].id;
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, userAgent: 'Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile Safari/537.36' });
  const issues = []; const ext = new Set();
  const run = async (route, token) => {
    const page = await ctx.newPage();
    const errs = [], bad = [];
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource: net::ERR_(FAILED|TUNNEL|INTERNET|NAME)/.test(m.text())) errs.push(m.text().slice(0, 200)); });
    page.on('requestfailed', r => { const u = r.url(); if (!u.includes('127.0.0.1') && !u.includes('localhost')) ext.add(new URL(u).host); });
    page.on('pageerror', e => errs.push('PAGEERROR ' + String(e).slice(0, 200)));
    page.on('response', r => { const s = r.status(); if (s >= 400 && r.url().includes('18100')) bad.push(`${s} ${r.request().method()} ${r.url().replace('http://localhost:18100', '').split('?')[0]}`); });
    await page.addInitScript(([t, l]) => { try { if (t) localStorage.setItem('fidem_token', t); else localStorage.removeItem('fidem_token'); localStorage.setItem('fidem_lang', l); } catch (e) {} }, [token, lang]);
    const url = route.replace('__F0__', f0);
    try { await page.goto(APP + url, { waitUntil: 'networkidle', timeout: 25000 }); } catch (e) { errs.push('NAV ' + String(e).slice(0, 100)); }
    await page.waitForTimeout(900);
    const info = await page.evaluate(() => {
      const de = document.documentElement;
      const over = de.scrollWidth - de.clientWidth;
      const bodyText = document.body.innerText || '';
      const keys = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())) { const s = n.nodeValue.trim(); if (/^[a-z][a-z0-9]*(_[a-z0-9]+)+$/.test(s) && !n.parentElement.closest('script,style,code')) keys.push(s); }
      const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 2 && getComputedStyle(e).position !== 'fixed'; }).slice(0, 3).map(e => (e.tagName + '.' + String(e.className).slice(0, 40)));
      return { over, len: bodyText.length, keys: [...new Set(keys)].slice(0, 8), bad: /undefined|NaN|\[object Object\]/.test(bodyText) ? bodyText.match(/.{0,25}(undefined|NaN|\[object Object\]).{0,15}/)[0] : '', wide, path: location.pathname + location.search };
    });
    if (shots) { const nm = (tag + '_' + route.replace(/[^a-z0-9]+/gi, '_')).slice(0, 60); await page.screenshot({ path: `' + __dirname + '/shots/${nm}.png`, fullPage: false }); }
    const prob = [];
    if (errs.length) prob.push('console: ' + [...new Set(errs)].slice(0, 3).join(' || '));
    if (bad.length) prob.push('api: ' + [...new Set(bad)].slice(0, 4).join(', '));
    if (info.over > 1) prob.push(`h-overflow ${info.over}px (${info.wide.join(',')})`);
    if (info.keys.length) prob.push('raw-keys: ' + info.keys.join(','));
    if (info.bad) prob.push('bad-text: ' + info.bad);
    if (info.len < 40) prob.push('near-empty page');
    if (prob.length) issues.push(`${route} -> ${info.path}\n     ` + prob.join('\n     '));
    await page.close();
  };
  fs.mkdirSync(__dirname + '/shots', { recursive: true });
  for (const r of publicRoutes) await run(r, null);
  for (const r of authRoutes) await run(r, U[who].token);
  console.log(`== ${who} lang=${lang}: ${publicRoutes.length + authRoutes.length} pages, ${issues.length} with issues ==`);
  console.log(issues.join('\n')); console.log('external hosts blocked in sandbox:', [...ext].join(', '));
  await b.close();
})();
