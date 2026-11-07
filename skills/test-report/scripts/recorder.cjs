// Records one take of a browser test: video, fake cursor, captions held for exactly as long as their
// speech takes, and a timeline the encoder uses to lay the speech down afterwards.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const tts = require('./tts-client.cjs');

let config = null;
const states = new WeakMap();

function setup(options) {
  config = {
    viewport: { width: 1280, height: 800 },
    // Exact hosts a Flutter web build fetches from the internet: the CanvasKit wasm, fallback fonts and
    // the icon font CDN. Any other non-local host is answered with a stub and listed in take.outside.
    allowHosts: /^(www\.gstatic\.com|fonts\.gstatic\.com|fonts\.googleapis\.com|cdn\.jsdelivr\.net)$/,
    refuseUrls: null,
    narrate: true,
    ...options,
  };
  if (!config.chromium) throw new Error('setup needs { chromium }, from the project\'s own Playwright');
  if (!config.workDir) throw new Error('setup needs { workDir }');
  fs.mkdirSync(path.join(config.workDir, 'takes'), { recursive: true });
}

// Playwright video draws no cursor, and a viewer needs to see where each click lands.
// The caption sits 72px up, clear of anything at the very bottom of the frame.
const overlay = () => {
  const install = () => {
    if (document.getElementById('__report_cursor') || !document.body) return;
    const c = document.createElement('div');
    c.id = '__report_cursor';
    c.style.cssText = 'position:fixed;left:0;top:0;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;background:rgba(226,60,60,.85);border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.5);z-index:2147483647;pointer-events:none;transition:transform .12s';
    const b = document.createElement('div');
    b.id = '__report_caption';
    b.style.cssText = 'position:fixed;left:50%;bottom:72px;transform:translateX(-50%);max-width:88%;padding:9px 16px;border-radius:8px;background:rgba(15,20,30,.9);color:#fff;font:600 19px system-ui,sans-serif;z-index:2147483647;pointer-events:none;display:none;text-align:center';
    document.body.append(c, b);
    const move = (e) => { c.style.left = `${e.clientX}px`; c.style.top = `${e.clientY}px`; };
    window.addEventListener('pointermove', move, true);
    window.addEventListener('pointerdown', (e) => { move(e); c.style.transform = 'scale(1.9)'; }, true);
    window.addEventListener('pointerup', () => { c.style.transform = ''; }, true);
  };
  document.addEventListener('DOMContentLoaded', install);
  install();
};

async function open({ take, initScripts = [], viewport, contextOptions = {} }) {
  if (!config) throw new Error('call setup first');
  const size = viewport || config.viewport;
  const browser = await config.chromium.launch({ headless: true, args: ['--disable-gpu', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'] });
  const context = await browser.newContext({
    viewport: size,
    acceptDownloads: true,
    recordVideo: { dir: path.join(config.workDir, 'raw', take), size },
    ...contextOptions,
  });
  // Nothing may leave this machine except the allowed CDN hosts: no error reporting, no analytics, no
  // deployed backend. Every request passes through here so a refuseUrls match is caught even on an
  // allowed host (firestore.googleapis.com is a googleapis.com host too). A refused request is aborted
  // before it leaves the machine and recorded, and finish fails the take.
  const outside = [];
  const refused = [];
  await context.route('**/*', (route) => {
    const url = route.request().url();
    if (config.refuseUrls && config.refuseUrls.test(url)) {
      refused.push(url.slice(0, 100));
      return route.abort('blockedbyclient');
    }
    const host = new URL(url).hostname;
    if (!host || /^(localhost|127\.0\.0\.1)$/.test(host) || config.allowHosts.test(host)) return route.continue();
    outside.push(url.slice(0, 100));
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
  await context.addInitScript(overlay);
  for (const [fn, arg] of initScripts) await context.addInitScript(fn, arg);
  const page = await context.newPage();
  const state = { take, t0: Date.now(), cuts: [], captions: [], steps: [], viewport: size };
  states.set(page, state);
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 300)));
  return { browser, context, page, errors, outside, refused, state };
}

const stateOf = (page) => {
  const s = states.get(page);
  if (!s) throw new Error('page was not opened by recorder.open');
  return s;
};
const now = (s) => Date.now() - s.t0;

// Everything before this point (boot, sign-in) is cut from the video.
function begin(page) {
  const s = stateOf(page);
  s.cuts.push({ from: 0, to: now(s), fromStart: true });
}

// Runs fn and cuts its stretch from the video. A boot in the middle of a take, say.
async function skip(page, fn) {
  const s = stateOf(page);
  const from = now(s);
  const result = await fn();
  s.cuts.push({ from, to: now(s) });
  return result;
}

async function caption(page, text) {
  await page.evaluate((t) => {
    const b = document.getElementById('__report_caption');
    if (!b) return;
    b.textContent = t || '';
    b.style.display = t ? 'block' : 'none';
  }, text);
}

const GAP_MS = 250;

// Shows a caption and speaks it. It returns only after the speech has ended, plus a gap, so the next
// line cannot start early. options: { min: shortest hold in ms, speak: other words for the voice,
// for a caption a voice would read badly, like a URL }.
async function say(page, text, options = {}) {
  const s = stateOf(page);
  const min = typeof options === 'number' ? options : options.min || 0;
  const spoken = typeof options === 'object' && options.speak ? options.speak : text;
  if (!config.narrate) {
    await caption(page, text);
    await page.waitForTimeout(Math.max(min, 1800));
    return;
  }
  // Generating speech takes real time the viewer must not sit through, so that stretch is cut.
  const clip = await skip(page, () => tts.speak(spoken));
  await caption(page, text);
  const t = now(s);
  s.captions.push({ t, text, spoken, wav: clip.wav, ms: clip.ms });
  await page.waitForTimeout(Math.max(min, clip.ms + GAP_MS));
}

// One row per step, so a failed step ends up in the report as failed rather than vanishing.
function stepper(page) {
  const s = stateOf(page);
  return async (name, fn, { optional = false } = {}) => {
    const t = now(s);
    try {
      await fn();
      s.steps.push({ name, ok: true, t });
      console.log(`PASS ${name}`);
    } catch (e) {
      s.steps.push({ name, ok: false, t, error: String(e.message).slice(0, 300) });
      console.log(`FAIL ${name}: ${e.message}`);
      await page.screenshot({ path: path.join(config.workDir, 'takes', `fail-${s.take}-${s.steps.length}.png`) }).catch(() => {});
      if (!optional) throw e;
    }
  };
}

async function finish(session, extra = {}) {
  const { page, context, browser, state, errors, outside, refused } = session;
  const video = page.video();
  state.end = now(state);
  // A live voice process would keep node from ever exiting.
  tts.stop();
  await context.close();
  await browser.close();
  if (refused.length) {
    throw new Error(`${state.take}: take failed, the page requested a refused URL (blocked, never sent): ${[...new Set(refused)].join(', ')}`);
  }
  const raw = await video.path();
  const seconds = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw]).toString().trim());
  const take = { ...state, t0: undefined, raw, videoMs: Math.round(seconds * 1000), errors, outside: [...new Set(outside)], ...extra };
  fs.writeFileSync(path.join(config.workDir, 'takes', `${state.take}.json`), JSON.stringify(take, null, 1));
  console.log(`${state.take}: ${take.steps.filter((x) => x.ok).length}/${take.steps.length} steps passed, ${take.captions.length} lines, ${errors.length} page errors`);
  return take;
}

module.exports = { setup, open, begin, skip, caption, say, stepper, finish };
