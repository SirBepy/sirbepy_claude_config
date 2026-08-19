// Screenshots the HubStaff weekly grid for one or more Mon-Sun weeks via local Playwright.
// No Playwright MCP dependency, no allowed-write-roots dance - writes straight to --out-dir.
// Usage: node hs_weekshot.cjs --org <id> --user <id> --profile <dir> --weeks <mon:sun,mon:sun,...> [--out-dir <dir>]
const fs = require('fs');
const path = require('path');
const { getArg, launchProfileContext } = require('./hs_common.cjs');

const args = process.argv.slice(2);
const org = getArg(args, '--org');
const user = getArg(args, '--user');
const profile = getArg(args, '--profile');
const weeksArg = getArg(args, '--weeks');
const outDir = getArg(args, '--out-dir', 'C:/Users/tecno/Desktop');

if (!org || !user || !profile || !weeksArg) {
  console.error('Usage: --org <id> --user <id> --profile <dir> --weeks <mon:sun,mon:sun,...> [--out-dir <dir>]');
  process.exit(1);
}

const weeks = weeksArg.split(',').map(pair => {
  const [mon, sun] = pair.split(':');
  return { mon, sun };
});

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const context = await launchProfileContext(profile);
  const results = [];
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.setViewportSize({ width: 2300, height: 1000 });

    for (const { mon, sun } of weeks) {
      const url = `https://app.hubstaff.com/organizations/${org}/time_entries/weekly?date=${mon}&date_end=${sun}&filters%5Buser%5D=${user}&filters%5BshowWeeklycopy%5D=`;
      await page.goto(url, { waitUntil: 'domcontentloaded' });

      const collapseToggle = page.getByText('left_panel_close', { exact: true });
      if (await collapseToggle.count() > 0) {
        await collapseToggle.click({ timeout: 3000 }).catch(() => {});
      }

      try {
        await page.waitForSelector('table tr, [data-testid*="row"]', { timeout: 10000 });
      } catch {
        results.push({ mon, sun, warning: `weekly table did not load for ${mon} - skipped` });
        continue;
      }
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(1500);

      const outPath = path.join(outDir, `hubstaff-weekly-${mon}_to_${sun}.png`);
      await page.screenshot({ path: outPath });
      const sizeBytes = fs.statSync(outPath).size;
      const warning = sizeBytes < 50 * 1024
        ? `screenshot for ${mon} may be a login page or empty table - check manually before sharing`
        : null;
      results.push({ mon, sun, path: outPath, sizeBytes, warning });
    }
  } finally {
    await context.close();
  }
  console.log(JSON.stringify(results));
})().catch(e => {
  console.error(e.message);
  process.exit(1);
});
