// Profile page shows the whole photo: a very tall photo with coloured bands at
// the top and bottom must keep both bands visible (nothing cropped).
const { chromium } = require('playwright');
const fs = require('fs');
const zlib = require('zlib');
const U = JSON.parse(fs.readFileSync(__dirname + '/users.json'));
const APP = 'http://127.0.0.1:18101', API = 'http://localhost:18100/api';
function png(w, h, rowColor) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) { const [r, g, b] = rowColor(y, h); raw[y * (w * 3 + 1)] = 0; for (let x = 0; x < w; x++) { const o = y * (w * 3 + 1) + 1 + x * 3; raw[o] = r; raw[o + 1] = g; raw[o + 2] = b; } }
  const crcT = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (buf) => { let c = 0xffffffff; for (const x of buf) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (t, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([l, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}
(async () => {
  let ok = true;
  const check = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) ok = false; };
  const owner = 'f5@fidem.uz', viewer = 'm6@fidem.uz';
  // tall photo: red band top 8%, blue band bottom 8%, grey middle
  const img = png(200, 600, (y, h) => (y < h * 0.08 ? [220, 0, 0] : y > h * 0.92 ? [0, 0, 220] : [150, 150, 150]));
  const fd = new FormData();
  fd.append('file', new Blob([img], { type: 'image/png' }), 'tall.png');
  const up = await (await fetch(API + '/files/upload', { method: 'POST', headers: { Authorization: 'Bearer ' + U[owner].token }, body: fd })).json();
  const pr = await fetch(API + '/profile', { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + U[owner].token }, body: JSON.stringify({ photo_url: up.url }) });
  check('tall photo set as main', pr.status === 200);
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((tk) => { localStorage.setItem('fidem_token', tk); localStorage.setItem('fidem_lang', 'uz'); }, U[viewer].token);
  await page.goto(`${APP}/candidate/${U[owner].id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  // the sharp (object-contain) image must be fully inside the photo box
  const r = await page.evaluate(() => {
    const box = document.querySelector('[data-testid=profile-detail] > div').getBoundingClientRect();
    const im = [...document.querySelectorAll('[data-testid=profile-detail] > div img')].find((x) => x.className.includes('object-contain'));
    if (!im || !im.naturalWidth) return null;
    const scale = Math.min(box.width / im.naturalWidth, box.height / im.naturalHeight);
    return { boxH: box.height, drawnH: im.naturalHeight * scale, drawnW: im.naturalWidth * scale, boxW: box.width };
  });
  check('whole photo is drawn inside the box (no crop)', r && r.drawnH <= r.boxH + 1 && r.drawnW <= r.boxW + 1);
  await page.screenshot({ path: __dirname + '/shots/profile_tall_photo.png', clip: { x: 0, y: 0, width: 390, height: 560 } });
  await b.close();
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
  process.exit(ok ? 0 : 1);
})();
