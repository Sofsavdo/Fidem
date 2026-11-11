// Filter: country/region/district are all pickers; district list follows the region.
const { chromium } = require('playwright'); const fs = require('fs');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
(async () => {
  const b = await chromium.launch(); let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U['qa@fidem.uz'].token);
  await p.goto('http://127.0.0.1:18101/', { waitUntil: 'networkidle' });
  await p.click('[data-testid=open-filter]');
  check('district is disabled until a region is chosen', await p.locator('[data-testid=filter-district-disabled]').count() === 1);
  await p.click('[data-testid=filter-region]');
  await p.click("[data-testid=\"filter-region-opt-Toshkent shahri\"]");
  await p.click('[data-testid=filter-district]');
  check('district list is a picker with Tashkent districts', await p.locator('[data-testid="filter-district-opt-Chilonzor"]').count() === 1
    && await p.locator('input[data-testid=filter-district]').count() === 0);
  await p.click('[data-testid="filter-district-opt-Chilonzor"]');
  await p.screenshot({ path: __dirname + '/shots/district_sheet.png' });
  await p.click('[data-testid=filter-region]');
  await p.click('[data-testid="filter-region-opt-Samarqand"]');
  check('changing region clears the district', !(await p.locator('[data-testid=filter-district]').innerText()).includes('Chilonzor'));
  await p.click('[data-testid=filter-district]');
  check('district list follows the new region', await p.locator('[data-testid="filter-district-opt-Urgut"]').count() === 1);
  await p.click('[data-testid="filter-district-opt-Urgut"]');
  await p.click('[data-testid=filter-apply]'); await p.waitForTimeout(500);
  check('chosen district shows as an active filter chip', (await p.locator('[data-testid=active-filter-chips]').innerText()).includes('Urgut'));
  await b.close(); process.exit(ok ? 0 : 1);
})();
