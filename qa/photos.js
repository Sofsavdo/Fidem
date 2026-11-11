// 1) photos stored with a dead/old backend host still load from the CURRENT backend
// 2) a user without a profile photo gets the upload screen instead of the app
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
(async () => {
  const b = await chromium.launch();
  let ok = true;
  const check = (name, cond) => { console.log((cond ? 'PASS ' : 'FAIL ') + name); if (!cond) ok = false; };
  const open = async (rewrite) => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['qa@fidem.uz'].token);
    const imgHosts = new Set();
    page.on('request', (r) => { if (r.url().includes('/api/files/')) imgHosts.add(new URL(r.url()).host); });
    await rewrite(page);
    await page.goto(APP + '/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    return { page, imgHosts, ctx };
  };
  // 1) legacy absolute host in candidate photo urls
  let r = await open(async (page) => {
    await page.route('**/api/candidates?*', async (route) => {
      const res = await route.fetch(); const j = await res.json();
      j.forEach((c) => { if (c.photo_url) c.photo_url = c.photo_url.replace(/^.*(\/api\/files\/)/, 'https://old-dead-backend.example.com$1'); });
      await route.fulfill({ response: res, json: j });
    });
  });
  check('legacy-host photos are requested from the current backend only', r.imgHosts.size > 0 && ![...r.imgHosts].some((h) => h.includes('old-dead')));
  await r.ctx.close();
  // 2) no photo -> gate
  r = await open(async (page) => {
    await page.route('**/api/auth/me', async (route) => {
      const res = await route.fetch(); const j = await res.json(); j.photo_url = null;
      await route.fulfill({ response: res, json: j });
    });
  });
  check('photo-less user sees the upload gate', await r.page.locator('[data-testid=photo-required]').count() === 1);
  check('...and not the candidate feed', await r.page.locator('[data-testid^=candidate-card-]').count() === 0);
  await r.page.screenshot({ path: __dirname + '/shots/photo_gate.png' });
  await r.ctx.close();
  await b.close();
  process.exit(ok ? 0 : 1);
})();
