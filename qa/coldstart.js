// Cold start on a stale /me must land on Nomzodlar; tapping the Me tab afterwards still works.
const { chromium } = require('playwright'); const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
(async () => {
  const b = await chromium.launch(); let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['qa@fidem.uz'].token);
  await p.goto('http://127.0.0.1:18101/me', { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
  check('cold start on /me opens Nomzodlar', new URL(p.url()).pathname === '/' && await p.locator('[data-testid=open-filter]').count() === 1);
  await p.click('[data-testid=nav-me]'); await p.waitForTimeout(400);
  check('Me tab still opens Me', new URL(p.url()).pathname === '/me');
  await p.goto('http://127.0.0.1:18101/saved?tab=interested', { waitUntil: 'networkidle' }); await p.waitForTimeout(400);
  check('deep link with query is respected', p.url().includes('/saved?tab=interested'));
  await b.close(); process.exit(ok ? 0 : 1);
})();
