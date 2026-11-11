// Regression: a sent message must appear exactly once even when the WebSocket
// echo reaches the sender BEFORE the HTTP response (we delay the response).
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['qa@fidem.uz'].token);
  let posts = 0;
  await page.route('**/api/messages/send', async (route) => {
    posts++;
    const res = await route.fetch();
    await new Promise((r) => setTimeout(r, 1500));   // WS echo lands first
    await route.fulfill({ response: res });
  });
  await page.goto(`${APP}/chat/${U['f0@fidem.uz'].id}`, { waitUntil: 'networkidle' });
  const text = 'dup check ' + Math.random().toString(36).slice(2, 8).replace(/[0-9]/g, 'x');
  await page.fill('[data-testid=chat-input]', text);
  await page.press('[data-testid=chat-input]', 'Enter');
  await page.press('[data-testid=chat-input]', 'Enter'); // fast second Enter must not double-send
  await page.waitForTimeout(3500);
  const count = await page.evaluate((t) => document.body.innerText.split(t).length - 1, text);
  console.log(`POSTs sent: ${posts}, bubbles shown: ${count}`);
  await b.close();
  process.exit(posts === 1 && count === 1 ? 0 : 1);
})();
