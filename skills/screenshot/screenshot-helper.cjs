const { getChromium } = require('../_shared/playwright-resolve.cjs');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { getSessionShotDir } = require('./session-shot-dir.cjs');

const args = process.argv.slice(2);
const get = (flag, def = null) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : def; };

// Allowlist, not a blocklist: a path must resolve (path.resolve, so ../ traversal and absolute
// paths are caught after resolution, never by string matching) inside THIS session's subfolder
// or the portfolio-keepers folder, or it is refused. A bare filename still auto-resolves into
// the session subfolder, so a caller never hand-builds the <pid>-<start-ticks> path itself.
function withinAllowlist(resolved, sessionDir) {
  const portfolioDir = path.resolve(process.cwd(), '.portfolio-data');
  const inSession = resolved === sessionDir || resolved.startsWith(sessionDir + path.sep);
  const inPortfolio = resolved === portfolioDir || resolved.startsWith(portfolioDir + path.sep);
  return inSession || inPortfolio;
}

function resolveScreenshotPath(p) {
  const sessionDir = getSessionShotDir();
  if (!p.includes('/') && !p.includes('\\')) {
    return path.join(sessionDir, p);
  }
  const resolved = path.resolve(p);
  if (!withinAllowlist(resolved, sessionDir)) {
    throw new Error(
      `Refusing to write screenshot outside the allowed folders: resolved to "${resolved}". ` +
      `Use a bare filename (auto-resolved into "${sessionDir}") or a path under ".portfolio-data/".`
    );
  }
  return resolved;
}

// Same allowlist as resolveScreenshotPath, for a frame-matrix output directory (nested files
// under it pass the same startsWith check, so no separate rule is needed for subfolders).
function resolveScreenshotDir(p) {
  const sessionDir = getSessionShotDir();
  const dir = (!p.includes('/') && !p.includes('\\')) ? path.join(sessionDir, p) : path.resolve(p);
  if (!withinAllowlist(dir, sessionDir)) {
    throw new Error(
      `Refusing to write into a folder outside the allowed locations: resolved to "${dir}". ` +
      `Use a bare folder name (auto-resolved into "${sessionDir}") or a path under ".portfolio-data/".`
    );
  }
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function usage() {
  console.error('Usage: --url <url> --plan <plan.json>');
  console.error('   or: --url <url> --screenshot <out.png> [--click <selector>] [--wait <ms>]');
  console.error('   or: --frames <frames.json> --out-dir <dir> [--serve <dir> | --base-url <url>]');
  console.error('Plan step types: {"type":"click","selector":".."} {"type":"hover","selector":".."} {"type":"selectOption","selector":"..","value":".."} {"type":"wait","ms":N} {"type":"scroll","to":N} {"type":"screenshot","out":"path.png"} {"type":"waitForSelector","selector":"..","timeout":N} {"type":"refresh"} {"type":"evaluate","js":".."}');
  console.error('evaluate.js is executed via page.evaluate(step.js) as a string - it must be an IIFE, e.g. "(function(){...})()", not a bare arrow function.');
  console.error('Frame spec: {"name":"..","url":"..","query":"..","width":N,"height":N,"wait":N,"deviceScaleFactor":N}. Give an absolute/file:// url, or a query/path combined with --base-url or --serve.');
}

function resolveFrameUrl(frame, baseUrl) {
  if (frame.url && /^(https?:|file:)/i.test(frame.url)) return frame.url;
  const suffix = frame.url || frame.query || '';
  if (!baseUrl) {
    throw new Error(`Frame "${frame.name}" needs an absolute url, or a --base-url/--serve origin to combine with its url/query.`);
  }
  const base = baseUrl.replace(/\/$/, '');
  return suffix ? base + (suffix.startsWith('/') || suffix.startsWith('?') ? suffix : `/${suffix}`) : base;
}

// Minimal static file server so bundled output (ES modules, relative asset paths) can be shot -
// those do not load over file://. Scoped to the given dir; caller closes it when done.
function startStaticServer(dir) {
  const root = path.resolve(dir);
  const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff': 'font/woff', '.woff2': 'font/woff2', '.map': 'application/json' };
  const server = http.createServer((req, res) => {
    const reqPath = decodeURIComponent((req.url || '/').split('?')[0]);
    const filePath = path.join(root, reqPath === '/' ? 'index.html' : reqPath);
    if (!filePath.startsWith(root)) { res.writeHead(403); res.end(); return; }
    fs.readFile(filePath, (err, data) => {
      if (err) { res.writeHead(404); res.end('Not found'); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => resolve({ server, port: server.address().port }));
  });
}

function runFrames(framesPath) {
  const serveDir   = get('--serve');
  const baseUrlFlag = get('--base-url');
  const outDirFlag  = get('--out-dir');
  if (!outDirFlag) { console.error('--frames requires --out-dir.'); process.exit(1); }

  let frames;
  try {
    frames = JSON.parse(fs.readFileSync(framesPath, 'utf8'));
  } catch (e) {
    console.error('Failed to read/parse frames file:', e.message);
    process.exit(1);
  }
  if (!Array.isArray(frames) || !frames.length) {
    console.error('Frames file must be a non-empty JSON array.');
    process.exit(1);
  }
  for (const f of frames) {
    if (!f.name || !f.width || !f.height) {
      console.error('Every frame needs name, width, height:', JSON.stringify(f));
      process.exit(1);
    }
  }

  let outDir;
  try {
    outDir = resolveScreenshotDir(outDirFlag);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }

  (async () => {
    let server = null;
    let baseUrl = baseUrlFlag;
    try {
      if (serveDir) {
        const started = await startStaticServer(serveDir);
        server = started.server;
        baseUrl = baseUrl || `http://127.0.0.1:${started.port}`;
      }

      const chromium = getChromium();
      const browser = await chromium.launch();
      const captured = [];
      const failed = [];

      for (const frame of frames) {
        const target = resolveFrameUrl(frame, baseUrl);
        // Mobile-width frames default to 2x for retina crispness; wider frames default to 1x.
        const scale = frame.deviceScaleFactor ?? (frame.width <= 500 ? 2 : 1);
        const context = await browser.newContext({
          viewport: { width: frame.width, height: frame.height },
          deviceScaleFactor: scale,
        });
        const page = await context.newPage();
        let pageError = null;
        page.on('pageerror', err => { pageError = err.message; });
        await page.goto(target, { waitUntil: 'networkidle' });
        if (frame.wait) await page.waitForTimeout(frame.wait);
        const outPath = path.join(outDir, `${frame.name}.png`);
        await page.screenshot({ path: outPath });
        await context.close();
        if (pageError) failed.push({ name: frame.name, error: pageError });
        else captured.push({ name: frame.name, path: outPath });
      }

      await browser.close();
      if (failed.length) {
        console.error('Frame(s) failed with a page error - a blank render does not count as captured.');
        process.exitCode = 1;
      }
      console.log(JSON.stringify({ captured, failed }));
    } catch (e) {
      console.error(e.message);
      process.exitCode = 1;
    } finally {
      if (server) server.close();
    }
  })();
}

function runPlanOrScreenshot() {
  const url          = get('--url');
  const planPath      = get('--plan');
  const screenshotOut = get('--screenshot');
  const clickSelector = get('--click');
  const waitMsRaw      = get('--wait');
  const [vw, vh]       = (get('--viewport', '1280x800')).split('x').map(Number);

  if (!url) { usage(); process.exit(1); }

  if (screenshotOut && planPath) {
    console.error('Pass either --plan or --screenshot, not both.');
    process.exit(1);
  }

  if (planPath && (clickSelector !== null || waitMsRaw !== null)) {
    console.error('--click/--wait only apply in --screenshot mode. In --plan mode, add {"type":"click","selector":...} or {"type":"wait","ms":...} steps instead.');
    process.exit(1);
  }

  if (screenshotOut) {
    if (clickSelector !== null && !/^[A-Za-z0-9_.:#\[\]=,\- ]+$/.test(clickSelector)) {
      console.error('Selector contains characters unsafe for shell argv - use --plan mode instead of --click for this selector.');
      process.exit(1);
    }
  } else if (!planPath) {
    usage();
    process.exit(1);
  }

  const waitMs = waitMsRaw !== null ? Number(waitMsRaw) : null;
  if (waitMs !== null && !Number.isFinite(waitMs)) {
    console.error('--wait must be a number (ms).');
    process.exit(1);
  }

  let steps = null;
  if (planPath) {
    try {
      steps = JSON.parse(fs.readFileSync(planPath, 'utf8'));
    } catch (e) {
      console.error('Failed to read/parse plan file:', e.message);
      process.exit(1);
    }
  }

  // Resolve/guard every screenshot output path up front, before launching the browser.
  let resolvedScreenshotOut = null;
  try {
    if (screenshotOut) resolvedScreenshotOut = resolveScreenshotPath(screenshotOut);
    if (steps) {
      for (const step of steps) {
        if (step.type === 'screenshot') step.out = resolveScreenshotPath(step.out);
      }
    }
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }

  (async () => {
    const chromium = getChromium();
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: vw, height: vh } });
    await page.goto(url, { waitUntil: 'networkidle' });

    if (resolvedScreenshotOut) {
      if (clickSelector) await page.click(clickSelector);
      if (waitMs !== null) await page.waitForTimeout(waitMs);
      await page.screenshot({ path: resolvedScreenshotOut });
      console.log('Saved:', resolvedScreenshotOut);
    } else {
      for (const step of steps) {
        switch (step.type) {
          case 'screenshot':
            await page.screenshot({ path: step.out });
            console.log('Saved:', step.out);
            break;
          case 'scroll':
            await page.evaluate(px => window.scrollTo(0, px), step.to);
            break;
          case 'click':
            await page.click(step.selector);
            break;
          case 'hover':
            await page.hover(step.selector);
            break;
          case 'selectOption':
            await page.selectOption(step.selector, step.value);
            break;
          case 'wait':
            await page.waitForTimeout(step.ms);
            break;
          case 'waitForSelector':
            await page.waitForSelector(step.selector, { timeout: step.timeout ?? 10000 });
            break;
          case 'refresh':
            await page.reload({ waitUntil: 'networkidle' });
            break;
          case 'evaluate': {
            const out = await page.evaluate(step.js);
            if (out !== undefined) {
              const prefix = step.label ? `evaluate[${step.label}]:` : 'evaluate:';
              console.log(prefix, typeof out === 'string' ? out : JSON.stringify(out));
            }
            break;
          }
          default:
            console.error('Unknown step type:', step.type);
            process.exit(1);
        }
      }
    }

    await browser.close();
  })();
}

const framesPath = get('--frames');
if (framesPath) {
  runFrames(framesPath);
} else {
  runPlanOrScreenshot();
}
