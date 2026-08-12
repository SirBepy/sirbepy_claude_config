// Checks HubStaff auth via local Playwright before a reconciliation run.
// No Playwright MCP dependency - drives the npx-cached playwright package directly.
// Usage: node hs_preflight.cjs --org <id> --user <id> --profile <dir> --mon <YYYY-MM-DD> --sun <YYYY-MM-DD>
const { chromium } = require('C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');
const fs = require('fs');

const args = process.argv.slice(2);
const get = (flag, def = null) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : def; };

const org = get('--org');
const user = get('--user');
const profile = get('--profile');
const mon = get('--mon');
const sun = get('--sun');

if (!org || !user || !profile || !mon || !sun) {
  console.error('Usage: --org <id> --user <id> --profile <dir> --mon <YYYY-MM-DD> --sun <YYYY-MM-DD>');
  process.exit(1);
}

const weeklyUrl = `https://app.hubstaff.com/organizations/${org}/time_entries/weekly?date=${mon}&date_end=${sun}&filters%5Buser%5D=${user}`;

function report(result) {
  console.log(JSON.stringify(result));
}

(async () => {
  fs.mkdirSync(profile, { recursive: true });
  const context = await chromium.launchPersistentContext(profile, { headless: false });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(weeklyUrl, { waitUntil: 'domcontentloaded' });

    if (!page.url().includes('account.hubstaff.com/login')) {
      return report({ authOk: true });
    }

    const email = process.env.HUBSTAFF_EMAIL;
    const password = process.env.HUBSTAFF_PASSWORD;

    if (email && password) {
      await page.fill('input[type="email"], input[name="email"]', email);
      await page.fill('input[type="password"], input[name="password"]', password);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(4000);
      if (page.url().includes('account.hubstaff.com/login')) {
        return report({ authOk: false, reason: 'auto-login failed (bad creds / 2FA / CAPTCHA)' });
      }
      return report({ authOk: true });
    }

    // No stored creds: wait for the dev to log in by hand in the visible window.
    for (let i = 0; i < 60; i++) {
      await page.waitForTimeout(2000);
      if (!page.url().includes('account.hubstaff.com/login')) {
        return report({ authOk: true });
      }
    }
    return report({ authOk: false, reason: 'manual login timeout (120s), no HUBSTAFF_EMAIL/PASSWORD set' });
  } finally {
    await context.close();
  }
})();
