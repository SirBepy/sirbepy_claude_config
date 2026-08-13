// Checks HubStaff auth via local Playwright before a reconciliation run.
// No Playwright MCP dependency - playwright resolution lives in hs_common.cjs (fallback chain,
// not a pinned npx cache path).
// Usage: node hs_preflight.cjs --org <id> --user <id> --profile <dir> --mon <YYYY-MM-DD> --sun <YYYY-MM-DD>
const { getArg, launchProfileContext } = require('./hs_common.cjs');

const args = process.argv.slice(2);
const org = getArg(args, '--org');
const user = getArg(args, '--user');
const profile = getArg(args, '--profile');
const mon = getArg(args, '--mon');
const sun = getArg(args, '--sun');

if (!org || !user || !profile || !mon || !sun) {
  console.error('Usage: --org <id> --user <id> --profile <dir> --mon <YYYY-MM-DD> --sun <YYYY-MM-DD>');
  process.exit(1);
}

const weeklyUrl = `https://app.hubstaff.com/organizations/${org}/time_entries/weekly?date=${mon}&date_end=${sun}&filters%5Buser%5D=${user}`;

function report(result) {
  console.log(JSON.stringify(result));
}

(async () => {
  const context = await launchProfileContext(profile);
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
})().catch(e => {
  console.error(e.message);
  process.exit(1);
});
