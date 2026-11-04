// Loads a report inside a frame sandboxed like the preview panel's and checks the player and layout.
// Usage: PLAYWRIGHT=<path to node_modules/playwright> node check-report.cjs <out.html> <screenshot dir>
const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');

const [deck, shots] = process.argv.slice(2);
if (!shots) { console.error('usage: node check-report.cjs <out.html> <screenshot dir>'); process.exit(2); }
fs.mkdirSync(shots, { recursive: true });
const html = fs.readFileSync(deck);
const results = [];
const check = (name, ok, detail = '') => {
  results.push(ok);
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? `: ${detail}` : ''}`);
};

(async () => {
  const server = http.createServer((req, res) => {
    if (req.url === '/deck') { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end(html); return; }
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end('<!doctype html><body style="margin:0"><iframe id="f" sandbox="allow-scripts" src="/deck" style="border:0;width:100vw;height:100vh"></iframe>');
  }).listen(0);
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1100, height: 800 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(base, { waitUntil: 'load', timeout: 60000 });
  const f = page.frameLocator('#f');
  const count = await f.locator('#nav button').count();

  for (let i = 0; i < count; i += 1) {
    await f.locator('#nav button').nth(i).click();
    // Mid-exit, the old slide is still up and moving the right way.
    if (i > 0) {
      await page.waitForTimeout(120);
      const out = await f.locator('section.leaving > *').first().evaluate((el) => ({ name: getComputedStyle(el).animationName, x: new DOMMatrix(getComputedStyle(el).transform).m41 }));
      check(`slide ${i}: the old slide leaves to the left going forward`, out.name === 'slide-out' && out.x < 0, JSON.stringify(out));
    }
    await page.waitForTimeout(900);
    const title = await f.locator('#nav button').nth(i).innerText();
    const box = await f.locator('#next').boundingBox().catch(() => null);
    if (i < count - 1) check(`${title}: Next at the bottom right`, !!box && box.x + box.width > 1100 * 0.85 && box.y + box.height > 800 * 0.88, JSON.stringify(box));

    const layout = await f.locator('#main').evaluate((m) => {
      const page = m.querySelector('.page').getBoundingClientRect();
      const box = m.getBoundingClientRect();
      return {
        left: Math.round(page.left - box.left), right: Math.round(box.right - page.right),
        top: Math.round(page.top - box.top), bottom: Math.round(box.bottom - page.bottom),
        tall: m.scrollHeight > m.clientHeight,
        scrollTop: m.scrollTop,
        animation: getComputedStyle(m.querySelector('section.on > *')).animationName,
        headingLinks: m.querySelectorAll('section.on h1 a').length,
      };
    });
    check(`${title}: page is centered`, Math.abs(layout.left - layout.right) <= 1 && (layout.tall ? layout.scrollTop === 0 : Math.abs(layout.top - layout.bottom) <= 1), JSON.stringify(layout));
    check(`${title}: slide content animates in`, layout.animation === (i === 0 ? 'none' : 'slide-in'), layout.animation);
    check(`${title}: tickets stay out of the heading`, layout.headingLinks === 0);
    if (i > 0 && i === count - 1) {
      await f.locator('#back').click();
      await page.waitForTimeout(120);
      const out = await f.locator('section.leaving > *').first().evaluate((el) => new DOMMatrix(getComputedStyle(el).transform).m41);
      check('Back: the old slide leaves to the right', out > 0, String(out));
      await page.waitForTimeout(900);
      await f.locator('#nav button').nth(i).click();
      await page.waitForTimeout(900);
    }

    const video = f.locator('section.on video');
    if (await video.count()) {
      const r = await video.evaluate(async (v) => {
        const wait = (ms) => new Promise((res) => setTimeout(res, ms));
        await new Promise((res) => { if (v.readyState >= 1) res(); else v.addEventListener('loadedmetadata', res, { once: true }); });
        v.muted = false;
        return { duration: v.duration, controls: v.controls, width: v.videoWidth, error: v.error && v.error.message, wait: !!wait };
      });
      check(`${title}: video loads`, r.duration > 0 && !r.error && !r.controls, JSON.stringify(r));

      const paused = () => video.evaluate((v) => v.paused);
      await video.click();
      await page.waitForTimeout(800);
      check(`${title}: one click plays`, !(await paused()));
      const audio = await video.evaluate(async (v) => {
        await new Promise((res) => setTimeout(res, 1500));
        return { decoded: v.webkitAudioDecodedByteCount, t: v.currentTime };
      });
      check(`${title}: sound is decoded`, audio.decoded > 0, JSON.stringify(audio));
      await video.click();
      await page.waitForTimeout(300);
      check(`${title}: a second click pauses`, await paused());

      const list = await f.locator('section.on .steps').evaluate((l) => ({ h: l.clientHeight, full: l.scrollHeight, top: l.scrollTop }));
      const playerHeight = await f.locator('section.on .player').evaluate((p) => p.offsetHeight);
      check(`${title}: list stays within the player's height`, list.h <= Math.max(playerHeight, 180) + 2, JSON.stringify({ ...list, playerHeight }));

      const jumps = f.locator('section.on .jump');
      const n = await jumps.count();
      await jumps.nth(n - 1).click();
      await page.waitForTimeout(1200);
      await video.evaluate((v) => v.pause());
      const lit = await f.locator('section.on .jump.now').count();
      const scroll = await f.locator('section.on .steps').evaluate((l) => {
        const row = l.querySelector('.jump.now');
        const a = row && row.getBoundingClientRect();
        const b = l.getBoundingClientRect();
        return { inView: !!a && a.top >= b.top - 1 && a.bottom <= b.bottom + 1, scrollTop: l.scrollTop, text: row && row.innerText.slice(0, 40) };
      });
      check(`${title}: the current step is lit and scrolled into view`, lit === 1 && scroll.inView, JSON.stringify(scroll));
      await page.screenshot({ path: path.join(shots, `slide-${i}.png`) });

      await f.locator('section.on .full').click();
      await page.waitForTimeout(400);
      const fill = await f.locator('section.on .player').evaluate((p) => ({ w: p.offsetWidth, h: p.offsetHeight, filled: p.classList.contains('filled'), real: document.fullscreenElement === p, enabled: document.fullscreenEnabled }));
      check(`${title}: full screen fills the frame`, fill.w >= 1090 && fill.h >= 790, JSON.stringify(fill));
      await page.screenshot({ path: path.join(shots, `slide-${i}-full.png`) });
      await f.locator('section.on .full').click();
      await page.waitForTimeout(300);
    } else {
      await page.screenshot({ path: path.join(shots, `slide-${i}.png`) });
    }
  }
  check('no page errors', errors.length === 0, errors.join(' | ').slice(0, 300));
  await browser.close();
  server.close();
  console.log(`${results.filter(Boolean).length}/${results.length} checks passed`);
  process.exit(results.every(Boolean) ? 0 : 1);
})().catch((e) => { console.error('FAILED', e.message); process.exit(1); });
