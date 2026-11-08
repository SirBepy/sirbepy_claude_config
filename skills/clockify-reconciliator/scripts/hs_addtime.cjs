// Bulk-adds HubStaff time entries via the web UI Add-time dialog (v2 API is read-only for time).
// Usage: node hs_addtime.cjs --org <id> --user <id> --profile <dir> --entries <path-to-json>
//   --project-label <label> --reason-label <label>
// entries.json: [{date:"YYYY-MM-DD", from:"H:MM am/pm", to:"H:MM am/pm", note:"..."}]
//
// Each result is {...entry, ok}. A failure before the Save click is retried (HubStaff pages are
// slow to settle: 8 of 21 entries timed out on goto or dialog-open on 2026-11-06 and all passed on
// a rerun). A failure after Save was clicked is never retried, because the entry may already exist:
// it reports ok:false with maybeSaved:true so the caller verifies through the activities API.
const fs = require('fs');
const { getArg, launchProfileContext, gotoWithRetry, defaultSleep } = require('./hs_common.cjs');

const MAX_RETRIES = 2;

// attempt(entry, markSaveClicked) performs one full try and calls markSaveClicked() right before
// it clicks Save. recover() resets the page between tries (closes a half-open dialog).
async function addEntryWithRetry(entry, attempt, { retries = MAX_RETRIES, recover = async () => {}, sleep = defaultSleep } = {}) {
  const result = { ...entry, ok: false };
  for (let n = 0; n <= retries; n++) {
    let saveClicked = false;
    try {
      await attempt(entry, () => { saveClicked = true; });
      result.ok = true;
      delete result.error;
      return result;
    } catch (e) {
      result.error = e.message;
      await recover();
      if (saveClicked) {
        result.maybeSaved = true;
        return result;
      }
      if (n < retries) await sleep(1000);
    }
  }
  return result;
}

function makeAttempt(page, { org, user, projectLabel, reasonLabel }) {
  const dailyUrl = (date) =>
    `https://app.hubstaff.com/organizations/${org}/time_entries/daily?date=${date}&date_end=${date}&filters%5Buser%5D=${user}`;

  return async (entry, markSaveClicked) => {
    await gotoWithRetry(page, dailyUrl(entry.date), { retries: 0 });
    await page.waitForTimeout(1500);

    await page.getByText('Add time', { exact: true }).first().click();
    const dlg = page.locator('.app-dialog.opened');
    await dlg.waitFor({ state: 'visible', timeout: 10000 });

    const selects = dlg.locator('select.select2-hidden-accessible');
    await selects.nth(0).selectOption({ label: projectLabel });
    await selects.nth(2).selectOption({ label: reasonLabel });

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
    const save = dlg.locator('button.save-button:has-text("Save")');
    markSaveClicked();
    await save.click();
    await page.waitForFunction(() => document.querySelectorAll('.app-dialog.opened').length === 0, { timeout: 10000 });
  };
}

async function main() {
  const args = process.argv.slice(2);
  const org = getArg(args, '--org');
  const user = getArg(args, '--user');
  const profile = getArg(args, '--profile');
  const entriesPath = getArg(args, '--entries');
  const projectLabel = getArg(args, '--project-label');
  const reasonLabel = getArg(args, '--reason-label', 'Forgot to start/stop timer');

  if (!org || !user || !profile || !entriesPath || !projectLabel) {
    console.error('Usage: --org <id> --user <id> --profile <dir> --entries <path-to-json> --project-label <label> [--reason-label <label>]');
    process.exit(1);
  }

  const entries = JSON.parse(fs.readFileSync(entriesPath, 'utf8'));
  const firstUrl = entries.length
    ? `https://app.hubstaff.com/organizations/${org}/time_entries/daily?date=${entries[0].date}&date_end=${entries[0].date}&filters%5Buser%5D=${user}`
    : null;
  const context = await launchProfileContext(profile, firstUrl);
  const results = [];
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.setViewportSize({ width: 2000, height: 1000 });
    const attempt = makeAttempt(page, { org, user, projectLabel, reasonLabel });
    const recover = async () => {
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(500).catch(() => {});
    };
    for (const entry of entries) results.push(await addEntryWithRetry(entry, attempt, { recover }));
  } finally {
    await context.close();
  }
  console.log(JSON.stringify(results));
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}

module.exports = { addEntryWithRetry, makeAttempt };
