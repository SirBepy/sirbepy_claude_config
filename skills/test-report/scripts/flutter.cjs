// Drives a Flutter web app through its semantics tree. Flutter draws text to a canvas, so these
// helpers click by coordinates taken from flt-semantics nodes, moving the mouse so the video shows it.
// The rules behind them: ~/.claude/refs/flutter-web-playwright.md.

async function arm(page, timeout = 60000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const n = await page.evaluate(() => {
      const count = document.querySelectorAll('flt-semantics').length;
      if (count > 0) return count;
      const el = document.querySelector('flt-semantics-placeholder');
      if (el) el.click();
      return 0;
    });
    if (n > 0) return;
    await page.waitForTimeout(400);
  }
  throw new Error('semantics stayed empty');
}

async function goto(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => !!document.querySelector('flutter-view'), null, { timeout: 90000 });
  await arm(page);
}

const inPage = ({ want, exact, role, maxW, any }) => {
  const low = want.toLowerCase();
  const sel = role ? `flt-semantics[role="${role}"]` : 'flt-semantics';
  const hits = [];
  for (const n of document.querySelectorAll(sel)) {
    const r = n.getBoundingClientRect();
    if (!r.width || !r.height || r.width > maxW) continue;
    if (!any && (r.y + r.height / 2 > innerHeight - 4 || r.y + r.height / 2 < 0)) continue;
    const label = (n.getAttribute('aria-label') || n.textContent || '').trim();
    const have = label.toLowerCase();
    if (exact ? have === low : have.includes(low)) hits.push({ label, x: r.x, y: r.y, w: r.width, h: r.height, disabled: n.getAttribute('aria-disabled') === 'true', role: n.getAttribute('role') });
  }
  // A parent node aggregates its children's text, so the shortest label is the real target.
  hits.sort((a, b) => a.label.length - b.label.length || a.w * a.h - b.w * b.h);
  return hits[0] || null;
};

const widthOf = (page) => page.viewportSize().width;
const heightOf = (page) => page.viewportSize().height;

async function find(page, want, { exact = false, role = null, timeout = 15000, any = false } = {}) {
  const deadline = Date.now() + timeout;
  while (true) {
    const hit = await page.evaluate(inPage, { want, exact, role, maxW: widthOf(page) - 40, any });
    if (hit) return hit;
    if (Date.now() > deadline) return null;
    await page.evaluate(() => {
      if (document.querySelectorAll('flt-semantics').length) return;
      const el = document.querySelector('flt-semantics-placeholder');
      if (el) el.click();
    }).catch(() => {});
    await page.waitForTimeout(250);
  }
}

async function wheel(page, dy, x = 700, y = 450) {
  await page.mouse.move(x, y, { steps: 6 });
  const step = Math.sign(dy) * 120;
  for (let left = Math.abs(dy); left > 0; left -= 120) {
    await page.mouse.wheel(0, step);
    await page.waitForTimeout(45);
  }
  await page.waitForTimeout(500);
}

// Scrolls Flutter's own scroll view until the node sits in the upper-middle of the window.
async function reveal(page, want, { exact = false, role = null, timeout = 15000, top = 300 } = {}) {
  const deadline = Date.now() + timeout;
  let lastMid = null;
  while (Date.now() < deadline) {
    const hit = await page.evaluate(inPage, { want, exact, role, maxW: widthOf(page) - 40, any: true });
    if (hit) {
      const mid = hit.y + hit.h / 2;
      const height = heightOf(page);
      if (mid > 110 && mid < height - 160) return hit;
      // At the end of the scroll view a low node can't move up any further.
      if (mid === lastMid && mid > 110 && mid < height - 40) return hit;
      lastMid = mid;
      await wheel(page, mid - top);
    } else {
      await page.waitForTimeout(250);
    }
  }
  throw new Error(`could not reveal ${JSON.stringify(want)}`);
}

async function moveClick(page, x, y) {
  await page.mouse.move(x, y, { steps: 14 });
  await page.waitForTimeout(220);
  await page.mouse.down();
  await page.waitForTimeout(70);
  await page.mouse.up();
}

async function click(page, want, opts = {}) {
  const hit = await find(page, want, opts);
  if (!hit) throw new Error(`no node matched ${JSON.stringify(want)}`);
  await moveClick(page, hit.x + (opts.dx ?? hit.w / 2), hit.y + (opts.dy ?? hit.h / 2));
  await page.waitForTimeout(opts.after ?? 700);
  return hit;
}

// A label above a field: 24px label, 8px gap, 52px field.
async function typeUnder(page, label, text, { offset = 34, exact = true, delay = 45 } = {}) {
  const hit = await find(page, label, { exact, timeout: 8000 });
  if (!hit) throw new Error(`no label ${JSON.stringify(label)}`);
  await moveClick(page, hit.x + 150, hit.y + hit.h + offset);
  await page.waitForSelector('input.flt-text-editing, textarea.flt-text-editing', { timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(200);
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.press('Delete');
  await page.keyboard.type(text, { delay });
  await page.waitForTimeout(300);
}

async function dump(page, tag = '') {
  const nodes = await page.evaluate(() => Array.from(document.querySelectorAll('flt-semantics')).map((n) => {
    const r = n.getBoundingClientRect();
    return { l: (n.getAttribute('aria-label') || n.textContent || '').trim().slice(0, 70), role: n.getAttribute('role'), dis: n.getAttribute('aria-disabled'), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
  }).filter((n) => n.w && n.l));
  console.log(`--- ${tag} (${nodes.length}) ${page.url()}`);
  for (const n of nodes) console.log(`${JSON.stringify(n.l)} ${n.role || ''}${n.dis === 'true' ? ' disabled' : ''} @${n.x},${n.y} ${n.w}x${n.h}`);
}

module.exports = { arm, goto, find, reveal, wheel, moveClick, click, typeUnder, dump };
