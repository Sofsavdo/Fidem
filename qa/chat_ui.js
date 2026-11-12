// Chat UX: openers on an empty chat, question deck, reply quote, reactions
// (seen live by the other side), typing indicator, day divider, assistant chips.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101', API = 'http://127.0.0.1:18100/api';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const adm = (await (await fetch(API + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'admin@fidem.uz', password: 'AdminQa#2026' }) })).json()).token;
  await fetch(`${API}/admin/users/${U['m1@fidem.uz'].id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + adm }, body: JSON.stringify({ plan: 'premium' }) });
  const b = await chromium.launch();
  const mk = async (who) => {
    const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
    page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
    await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
    return page;
  };
  const him = await mk('m1@fidem.uz'), her = await mk('f2@fidem.uz');
  await him.goto(APP + '/chat/' + U['f2@fidem.uz'].id, { waitUntil: 'networkidle' });
  await him.waitForTimeout(1200);
  check('empty chat shows openers', (await him.locator('[data-testid=chat-openers]').count()) === 1);
  await him.screenshot({ path: OUT + '/chat_openers.png' });
  await him.click('[data-testid=opener-0]');
  await him.waitForTimeout(1000);
  check('tapping an opener sends it at once', (await him.locator('[data-testid^=msg-]').filter({ hasText: 'Assalomu' }).count()) >= 1 && (await him.inputValue('[data-testid=chat-input]')) === '');

  await her.goto(APP + '/chat/' + U['m1@fidem.uz'].id, { waitUntil: 'networkidle' });
  await her.waitForTimeout(1200);
  check('day divider shown', (await her.locator('[data-testid=day-divider]').count()) >= 1);
  // typing: she types, he sees "yozmoqda"
  await her.type('[data-testid=chat-input]', 'Va alaykum', { delay: 40 });
  await him.waitForTimeout(800);
  check('he sees "yozmoqda…"', (await him.locator('[data-testid=chat-status]').innerText()).includes('yozmoqda') && (await him.locator('[data-testid=typing-bubble]').count()) === 1);
  await him.screenshot({ path: OUT + '/chat_typing.png' });
  // she replies with a quote
  const first = her.locator('[data-testid^=msg-]').filter({ hasText: 'Assalomu' }).first();
  await first.click();
  await her.click('[data-testid=msg-reply]');
  check('reply preview above the input', (await her.locator('[data-testid=reply-preview]').count()) === 1);
  await her.fill('[data-testid=chat-input]', 'Va alaykum assalom! Ha, Toshkentdanman 😊');
  await her.click('[data-testid=chat-send]');
  await her.waitForTimeout(1000);
  check('sent message carries the quote', (await her.locator('[data-testid=msg-quote]').count()) === 1);
  await him.waitForTimeout(800);
  check('he sees her answer with the quote', (await him.locator('[data-testid=msg-quote]').count()) === 1);
  // she reacts ❤️ to his message; he sees it live
  await first.click();
  await her.locator('[data-testid=msg-actions] >> text=❤️').click();
  await him.waitForTimeout(1000);
  check('reaction shows on both sides', (await her.locator('[data-testid=msg-reactions]').count()) === 1 && (await him.locator('[data-testid=msg-reactions]').count()) === 1);
  // question deck
  await him.click('[data-testid=question-deck-open]');
  await him.waitForSelector('[data-testid=question-deck]');
  const before = await him.locator('[data-testid^=msg-]').count();
  await him.locator('[data-testid=question-deck] button', { hasText: '?' }).nth(1).click();
  await him.waitForTimeout(1000);
  check('tapping a deck question sends it at once', (await him.locator('[data-testid^=msg-]').count()) > before && (await him.locator('[data-testid=question-deck]').count()) === 0);
  await him.screenshot({ path: OUT + '/chat_after.png' });
  await her.screenshot({ path: OUT + '/chat_her.png' });

  await him.goto(APP + '/chat/ai_assistant', { waitUntil: 'networkidle' });
  await him.waitForTimeout(1000);
  check('assistant: quick question chips', (await him.locator('[data-testid=assistant-chips] button').count()) === 4);
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
