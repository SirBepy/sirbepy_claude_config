const { chromium } = require('C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const args = process.argv.slice(2);
const get = (flag, def = null) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : def; };

const url      = get('--url');
const planPath = get('--plan');
const [vw, vh] = (get('--viewport', '1280x800')).split('x').map(Number);

if (!url || !planPath) { console.error('Usage: --url <url> --plan <plan.json>'); process.exit(1); }

const steps = JSON.parse(fs.readFileSync(planPath, 'utf8'));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: vw, height: vh } });
  await page.goto(url, { waitUntil: 'networkidle' });

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
    }
  }

  await browser.close();
})();
