const { chromium } = require('C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const args = process.argv.slice(2);
const get = (flag, def = null) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : def; };

function usage() {
  console.error('Usage: --url <url> --plan <plan.json>');
  console.error('   or: --url <url> --screenshot <out.png> [--click <selector>] [--wait <ms>]');
}

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

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: vw, height: vh } });
  await page.goto(url, { waitUntil: 'networkidle' });

  if (screenshotOut) {
    if (clickSelector) await page.click(clickSelector);
    if (waitMs !== null) await page.waitForTimeout(waitMs);
    await page.screenshot({ path: screenshotOut });
    console.log('Saved:', screenshotOut);
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
        case 'wait':
          await page.waitForTimeout(step.ms);
          break;
        case 'waitForSelector':
          await page.waitForSelector(step.selector, { timeout: step.timeout ?? 10000 });
          break;
        case 'refresh':
          await page.reload({ waitUntil: 'networkidle' });
          break;
        case 'evaluate':
          await page.evaluate(step.js);
          break;
        default:
          console.error('Unknown step type:', step.type);
          process.exit(1);
      }
    }
  }

  await browser.close();
})();
