// AI conversation partners in the browser: labelled card, real people first,
// profile note, free chat (no paywall), pinned assistant, admin switch.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101', API = 'http://127.0.0.1:18100/api';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const adm = (await (await fetch(API + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'admin@fidem.uz', password: 'AdminQa#2026' }) })).json()).token;
  const H = (t) => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + t });
  await fetch(API + '/admin/ai-personas', { method: 'POST', headers: H(adm), body: JSON.stringify({ enabled: true }) });
  await new Promise((r) => setTimeout(r, 1500));
  const st = await (await fetch(API + '/admin/ai-personas', { headers: H(adm) })).json();
  check('admin: 20 AI characters, switched on', st.enabled && st.personas === 20);

  const feed = await (await fetch(API + '/candidates?limit=60', { headers: H(U['m3@fidem.uz'].token) })).json();
  const firstAi = feed.findIndex((c) => c.is_ai);
  check('feed has labelled AI women', feed.some((c) => c.is_ai && c.gender === 'female'));
  check('real people come first', firstAi > 0 && feed.slice(0, firstAi).every((c) => !c.is_ai) && feed.slice(firstAi).every((c) => c.is_ai));
  check('AI always online', feed.filter((c) => c.is_ai).every((c) => c.online));
  check('assistant not in the feed', !feed.some((c) => c.id === 'ai_assistant'));

  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['m3@fidem.uz'].token);
  const ai = feed[firstAi];
  await page.goto(APP + '/candidate/' + ai.id, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('profile: AI note', (await page.locator('[data-testid=profile-ai-note]').count()) === 1);
  check('profile: no family-contact button', (await page.locator('[data-testid=profile-family]').count()) === 0);
  await page.screenshot({ path: OUT + '/ai_profile.png' });

  await page.goto(APP + '/chat/' + ai.id, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('chat: AI badge + note', (await page.locator('[data-testid=chat-ai-badge]').count()) === 1 && (await page.locator('[data-testid=chat-ai-note]').count()) === 1);
  check('chat: no contact-exchange button', (await page.locator('[data-testid=contact-share-open]').count()) === 0);
  check('chat: free user can type (no paywall)', await page.locator('[data-testid=chat-input]').isEnabled());
  await page.fill('[data-testid=chat-input]', 'Assalomu alaykum, qalaysiz?');
  await page.click('[data-testid=chat-send]');
  await page.waitForTimeout(1200);
  check('chat: message sent', (await page.locator('[data-testid=chat-history]').innerText()).includes('qalaysiz'));
  await page.screenshot({ path: OUT + '/ai_chat.png' });

  await page.goto(APP + '/messages', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('messages: assistant pinned', (await page.locator('[data-testid=assistant-row]').count()) === 1);
  await page.screenshot({ path: OUT + '/ai_messages.png' });
  await page.click('[data-testid=assistant-row]');
  await page.waitForTimeout(1500);
  check('assistant chat opens', (await page.locator('[data-testid=chat-input]').count()) === 1 && (await page.locator('[data-testid=chat-ai-badge]').count()) === 1);
  await page.screenshot({ path: OUT + '/ai_assistant.png' });

  await page.goto(APP + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.evaluate(() => { const el = document.querySelector('[data-testid=ai-badge]'); if (el) el.scrollIntoView({ block: 'center' }); });
  await page.waitForTimeout(500);
  check('feed card shows the AI badge', (await page.locator('[data-testid=ai-badge]').count()) > 0);
  await page.screenshot({ path: OUT + '/ai_feed.png' });

  await fetch(API + '/admin/ai-personas', { method: 'POST', headers: H(adm), body: JSON.stringify({ enabled: false }) });
  const feed2 = await (await fetch(API + '/candidates?limit=60', { headers: H(U['m3@fidem.uz'].token) })).json();
  check('switched off: gone from the feed', !feed2.some((c) => c.is_ai));
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
