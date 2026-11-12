// Guest mode in the browser: first question, 4 open photos, every action
// opens "finish registration", the assistant works, no photo URL leaks.
const { chromium } = require('playwright');
const APP = 'http://127.0.0.1:18101', API = 'http://127.0.0.1:18100/api';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const r = await (await fetch(API + '/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: `guest${Date.now()}@fidem.uz`, password: 'QaPass#2026', name: 'Mehmon' }) })).json();
  const token = r.token;
  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  const leaked = [];
  page.on('response', (res) => { if (res.url().includes('/api/files/') && res.status() === 200) leaked.push(res.url()); });
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, token);

  await page.goto(APP + '/', { waitUntil: 'networkidle' });
  check('first screen asks who they look for', (await page.locator('[data-testid=guest-start]').count()) === 1);
  await page.screenshot({ path: OUT + '/guest_start.png' });
  await page.click('[data-testid=guest-pick-female]');
  await page.waitForSelector('[data-testid^=candidate-card-]', { timeout: 15000 });
  await page.waitForTimeout(1200);
  const cards = await page.locator('[data-testid^=candidate-card-]').count();
  const locked = await page.locator('[data-testid=guest-locked-photo]').count();
  check(`feed opens (${cards} cards), guest banner shown`, cards >= 5 && (await page.locator('[data-testid=guest-banner]').count()) === 1);
  check(`only 4 cards show photos (${cards - locked} open, ${locked} locked)`, cards - locked === 4 && locked === cards - 4);
  await page.screenshot({ path: OUT + '/guest_feed.png' });

  const feed = await (await fetch(API + '/candidates?limit=60', { headers: { Authorization: 'Bearer ' + token } })).json();
  const lockedIds = feed.filter((c) => c.guest_locked).map((c) => c.id);
  check('locked profiles carry no photo URL', feed.filter((c) => c.guest_locked).every((c) => !c.photo_url && !(c.photos || []).length));

  const firstCard = page.locator('[data-testid^=candidate-save-]').first();
  await firstCard.click();
  await page.waitForSelector('[data-testid=register-sheet]', { timeout: 5000 });
  check('like opens "finish registration"', true);
  await page.screenshot({ path: OUT + '/guest_sheet.png' });
  await page.locator('[data-testid=register-sheet] >> text=Keyinroq').click();

  await page.goto(APP + '/candidate/' + lockedIds[0], { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('locked profile: photo button asks to register', (await page.locator('[data-testid=guest-unlock-photo]').count()) === 1);
  await page.click('[data-testid=profile-write]');
  await page.waitForTimeout(500);
  check('write opens the sheet', (await page.locator('[data-testid=register-sheet]').count()) === 1);
  await page.screenshot({ path: OUT + '/guest_profile.png' });

  await page.goto(APP + '/chat/' + lockedIds[0], { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('chat with a person: register gate', (await page.locator('[data-testid=chat-guest-gate]').count()) === 1);

  await page.goto(APP + '/chat/ai_assistant', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await page.fill('[data-testid=chat-input]', 'Bu ilova qanday ishlaydi?');
  await page.click('[data-testid=chat-send]');
  await page.waitForTimeout(1000);
  check('guest can ask the assistant', (await page.locator('[data-testid=chat-history]').innerText()).includes('qanday ishlaydi'));

  await page.goto(APP + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.locator('a[href="/me"]').last().click();
  await page.waitForTimeout(800);
  check('Me: finish-profile card', (await page.locator('[data-testid=me-guest]').count()) === 1);
  await page.click('[data-testid=me-guest-register]');
  await page.waitForTimeout(800);
  check('register button opens onboarding', page.url().endsWith('/onboarding'));

  const direct = await fetch(API + '/candidates/' + lockedIds[0], { headers: { Authorization: 'Bearer ' + token } }).then((x) => x.json());
  check('locked profile detail has no photo URL', !direct.photo_url && direct.guest_locked === true);
  const ids = new Set(leaked.map((u) => u.split('/api/files/')[1].split('?')[0]));
  console.log('   distinct photos loaded:', ids.size, leaked.length);
  check('page loaded at most the 4 open photos (+ the assistant avatar)', ids.size <= 5);
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
