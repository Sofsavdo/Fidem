// Nomzodlar: more than 30 people -> the list keeps loading as it scrolls, the
// count is the real one, and nobody shows twice.
const { chromium } = require('playwright');
const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
const OUT = process.env.OUT || '/tmp/claude-0';
(async () => {
  let ok = true;
  const check = (n, c, extra = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (extra ? '  ' + extra : '')); if (!c) ok = false; };
  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  page.on('pageerror', (e) => { console.log('PAGEERR', e.message); ok = false; });
  const calls = [];
  page.on('request', (r) => { const m = r.url().match(/\/api\/candidates\?(.*)$/); if (m) calls.push(m[1]); });
  await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['m1@fidem.uz'].token);
  await page.goto(APP + '/candidates', { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid=candidates-grid]');
  const cards = () => page.locator('[data-testid=candidates-grid] > *').count();
  const first = await cards();
  check('first page has 30 cards (plus promo cards)', first >= 30, `cards=${first}`);
  const header = await page.locator('h1').first().locator('xpath=following-sibling::*[1]').innerText().catch(() => '');
  check('header shows the real total, not 30', /6\d/.test(header) && !/^30 /.test(header.trim()), JSON.stringify(header.trim()));
  // scroll to the bottom: the next page loads by itself
  // (the page scrolls inside <main>, so bring the end-of-list marker into view)
  for (let i = 0; i < 6; i++) {
    const more = page.locator('[data-testid=candidates-more]');
    if (!(await more.count())) break;
    await more.scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);
  }
  await page.waitForLoadState('networkidle');
  const after = await cards();
  check('scrolling loads more people', after > first, `cards ${first} -> ${after}`);
  check('all 62 people end up on the page', (await page.locator('[data-testid^=candidate-card-]').count()) === 62);
  check('no "show more" once the list is complete', (await page.locator('[data-testid=candidates-more]').count()) === 0);
  check('requests used offset', calls.some((c) => /offset=30/.test(c)) && calls.some((c) => /limit=30/.test(c)), calls.join(' | '));
  const ids = await page.locator('[data-testid^=candidate-card-]').evaluateAll((els) => els.map((e) => e.getAttribute('data-testid')));
  check('nobody shown twice', ids.length === new Set(ids).size, `${ids.length} cards`);
  check('no horizontal scroll', await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
  await page.screenshot({ path: OUT + '/feed_paging.png' });
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
