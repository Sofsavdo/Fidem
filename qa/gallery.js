// Top bar has no balance/VIP; gallery: add 2 extra photos in Me via the UI, then
// another user swipes through 3 photos on that profile; remove works.
const { chromium } = require('playwright');
const fs = require('fs');
const zlib = require('zlib');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101';
// tiny valid PNG (solid colour) generated in-process
function png(r, g, b) {
  const w = 64, h = 64, raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; for (let x = 0; x < w; x++) { const o = y * (w * 3 + 1) + 1 + x * 3; raw[o] = r; raw[o + 1] = g; raw[o + 2] = b; } }
  const crcT = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (buf) => { let c = 0xffffffff; for (const x of buf) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (t, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([l, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}
(async () => {
  const b = await chromium.launch();
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const mk = async (who) => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => { localStorage.setItem('fidem_token', t); localStorage.setItem('fidem_lang', 'uz'); }, U[who].token);
    return { ctx, page };
  };
  // owner adds photos
  let { ctx, page } = await mk('qa@fidem.uz');
  await page.goto(APP + '/me', { waitUntil: 'networkidle' });
  check('top bar has no balance pill', await page.locator('[data-testid=topbar-balance]').count() === 0);
  check('top bar has no VIP badge', !(await page.locator('[data-testid=mobile-topbar]').innerText()).includes('VIP'));
  await page.setInputFiles('[data-testid=gallery-input]', [
    { name: 'a.png', mimeType: 'image/png', buffer: png(200, 50, 50) },
    { name: 'b.png', mimeType: 'image/png', buffer: png(50, 200, 50) },
  ]);
  await page.waitForFunction(() => document.querySelectorAll('[data-testid=gallery-item]').length === 2, null, { timeout: 15000 }).catch(() => {});
  check('two extra photos appear in the gallery', await page.locator('[data-testid=gallery-item]').count() === 2);
  await page.screenshot({ path: __dirname + '/shots/gallery_me.png' });
  await ctx.close();
  // visitor swipes
  ({ ctx, page } = await mk('f0@fidem.uz'));
  await page.goto(APP + '/candidate/' + U['qa@fidem.uz'].id, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  check('visitor sees 3 slides (dots)', await page.locator('[data-testid=photo-dots] span').count() === 3);
  await page.click('[data-testid=photo-next]');
  await page.waitForTimeout(300);
  const wide = await page.locator('[data-testid=photo-dots] span').nth(1).evaluate((e) => e.className.includes('w-6'));
  check('tapping next moves to the 2nd photo', wide);
  await page.screenshot({ path: __dirname + '/shots/gallery_detail.png' });
  await ctx.close();
  // owner removes one
  ({ ctx, page } = await mk('qa@fidem.uz'));
  await page.goto(APP + '/me', { waitUntil: 'networkidle' });
  await page.click('[data-testid=gallery-remove] >> nth=0');
  await page.waitForFunction(() => document.querySelectorAll('[data-testid=gallery-item]').length === 1, null, { timeout: 10000 }).catch(() => {});
  check('removing a photo works', await page.locator('[data-testid=gallery-item]').count() === 1);
  await ctx.close();
  await b.close();
  process.exit(ok ? 0 : 1);
})();
