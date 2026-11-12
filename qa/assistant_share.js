// FIDEM assistant (pinned in Messages, free, labelled) + profile share link.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101', API = 'http://127.0.0.1:18100/api';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const H = (t) => ({ Authorization: 'Bearer ' + t });
  const feed = await (await fetch(API + '/candidates?limit=60', { headers: H(U['m3@fidem.uz'].token) })).json();
  check('no AI in the candidate feed', !feed.some((c) => c.is_ai));

  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  await page.addInitScript((t) => {
    localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz');
    window.__shared = null;
    navigator.share = (d) => { window.__shared = d; return Promise.resolve(); };
  }, U['m3@fidem.uz'].token);

  await page.goto(APP + '/messages', { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);
  check('assistant pinned in Messages', (await page.locator('[data-testid=assistant-row]').count()) === 1);
  await page.click('[data-testid=assistant-row]');
  await page.waitForTimeout(1500);
  check('assistant chat: AI badge + note', (await page.locator('[data-testid=chat-ai-badge]').count()) === 1 && (await page.locator('[data-testid=chat-ai-note]').count()) === 1);
  check('assistant chat: no contact button, free to type', (await page.locator('[data-testid=contact-share-open]').count()) === 0 && await page.locator('[data-testid=chat-input]').isEnabled());
  await page.fill('[data-testid=chat-input]', 'Premium qancha turadi?');
  await page.click('[data-testid=chat-send]');
  await page.waitForTimeout(1200);
  check('assistant chat: question sent', (await page.locator('[data-testid=chat-history]').innerText()).includes('Premium qancha'));
  await page.screenshot({ path: OUT + '/assistant_chat.png' });

  await page.goto(APP + '/candidate/' + U['f0@fidem.uz'].id, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.click('[data-testid=profile-share]');
  await page.waitForTimeout(500);
  const shared = await page.evaluate(() => window.__shared);
  const fid = U['f0@fidem.uz'].id;
  check('share: link points to the bot with the profile', !!shared && /^https:\/\/t\.me\/[A-Za-z0-9_]+\?start=share_/.test(shared.url) && shared.url.endsWith(fid));
  console.log('   shared url:', shared && shared.url);
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
