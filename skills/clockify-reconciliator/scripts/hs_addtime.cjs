// Bulk-adds HubStaff time entries via the web UI Add-time dialog (v2 API is read-only for time).
// Usage: node hs_addtime.cjs --org <id> --user <id> --profile <dir> --entries <path-to-json>
//   --project-label <label> --reason-label <label>
// entries.json: [{date:"YYYY-MM-DD", from:"H:MM am/pm", to:"H:MM am/pm", note:"..."}]
const fs = require('fs');
const { getArg, launchProfileContext } = require('./hs_common.cjs');

const args = process.argv.slice(2);
const org = getArg(args, '--org');
const user = getArg(args, '--user');
const profile = getArg(args, '--profile');
const entriesPath = getArg(args, '--entries');
const PROJECT_LABEL = getArg(args, '--project-label');
const REASON_LABEL = getArg(args, '--reason-label', 'Forgot to start/stop timer');

if (!org || !user || !profile || !entriesPath || !PROJECT_LABEL) {
  console.error('Usage: --org <id> --user <id> --profile <dir> --entries <path-to-json> --project-label <label> [--reason-label <label>]');
  process.exit(1);
}

const entries = JSON.parse(fs.readFileSync(entriesPath, 'utf8'));

(async () => {
  const context = await launchProfileContext(profile);
  const results = [];
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.setViewportSize({ width: 2000, height: 1000 });

    for (const entry of entries) {
      const result = { ...entry, ok: false };
      try {
        const url = `https://app.hubstaff.com/organizations/${org}/time_entries/daily?date=${entry.date}&date_end=${entry.date}&filters%5Buser%5D=${user}`;
        await page.goto(url, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1500);

        await page.getByText('Add time', { exact: true }).first().click();
        const dlg = page.locator('.app-dialog.opened');
        await dlg.waitFor({ state: 'visible', timeout: 10000 });

        const selects = dlg.locator('select.select2-hidden-accessible');
        await selects.nth(0).selectOption({ label: PROJECT_LABEL });
        await selects.nth(2).selectOption({ label: REASON_LABEL });

        const timeInputs = dlg.locator('input.default-input');
        for (const [idx, value] of [[0, entry.from], [1, entry.to]]) {
          const input = timeInputs.nth(idx);
          await input.click();
          await page.keyboard.press('Control+A');
          await page.keyboard.press('Delete');
          await page.keyboard.type(value, { delay: 30 });
          await page.waitForTimeout(400);
        }

        const billableCheckbox = dlg.locator('[data-testid="time-entries-form-dialog-billable"] input[type="checkbox"]');
        if (await billableCheckbox.count() > 0 && await billableCheckbox.isChecked()) {
          await dlg.locator('[data-testid="time-entries-form-dialog-billable"]').click();
        }

        const addNote = dlg.locator('a:has-text("Add note")');
        if (await addNote.count() > 0) await addNote.click();
        await dlg.locator('textarea[name="work_note"]').fill(entry.note);

        await dlg.locator('[data-testid="app-dialog-header"]').click();
        await dlg.locator('button.save-button:has-text("Save")').click();
        await page.waitForFunction(() => document.querySelectorAll('.app-dialog.opened').length === 0, { timeout: 10000 });

        result.ok = true;
      } catch (e) {
        result.error = e.message;
        await page.keyboard.press('Escape').catch(() => {});
        await page.waitForTimeout(500);
      }
      results.push(result);
    }
  } finally {
    await context.close();
  }
  console.log(JSON.stringify(results));
})().catch(e => {
  console.error(e.message);
  process.exit(1);
});
