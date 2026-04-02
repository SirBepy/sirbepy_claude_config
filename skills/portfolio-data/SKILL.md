---
name: portfolio-data
description: Triggers on /portfolio-data only.
---

# /portfolio-data

> Generate or update portfolio metadata and write-up for a project repo.

## Before anything else - detect OS

Run `uname` to detect the OS. If it fails, assume Windows. Keep this in mind for any shell commands throughout.

## Workflow

### Step 0 - Check existing data

If the user passed `skipVerification`, skip this step entirely and proceed to Step 1.

If `.portfolio-data/metadata.json` exists: read it, identify null/empty/0 fields, fill only those. Tell user if already complete and stop. Skip Step 1 unless core fields (title, description, type) look wrong.

If `.portfolio-data/` does not exist, proceed to Step 1.

### Step 1 - Explore the repo

Read: README, package.json/equivalent, folder structure, source/config files, git history (for year). Infer: languages, frameworks, type, status, year, impressiveness, purpose.

### Step 2 - Infer everything, ask only if genuinely unsure

Make best guesses for all fields. Do not ask routine questions.

- **Live URL** - default to `https://sirbepy.github.io/[repo-name]/`. If deploy type is `none`, set to `null`.
- **Images** - always take screenshots automatically using the Auto-Screenshot Workflow below.
- **All other fields** - infer from the codebase. Flag significant assumptions in the summary but do not wait for confirmation.

Only ask a question if something is genuinely confusing and you cannot make a reasonable guess (e.g. the project's purpose is truly ambiguous, or the type could reasonably be two very different things). Normal inference is fine - do not ask just to confirm.

### Auto-Screenshot Workflow

**Detect type and start command:**

| Check | Type | Port | Command |
|---|---|---|---|
| `vite.config.*` | Vite | 5173 | `npm run dev` |
| `package.json` with React/Next deps | React | 3000 | `npm run dev` |
| `index.html`, no `package.json` | Static | 8080 | `python -m http.server 8080` |

Use port from `vite.config.*` if specified. Run start command with `run_in_background: true` (one Bash call, no chaining).

Poll for readiness: `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT` - up to 15 tries, 1s apart.

**Plan screenshots before taking them.** Before capturing anything, read the source code to understand what the app looks like and what would be worth showing. Look for:

- **Routes/pages**: Check the router config (react-router, vue-router, file-based routing) for distinct pages worth capturing. Prioritize pages that show real functionality over empty shells.
- **Hidden UI**: Look for modals, drawers, dropdowns, settings panels, or UI that only appears after interaction (button clicks, hover states, toggling a feature on). If important UI is hidden behind a click, use Playwright scripting to trigger it before screenshotting.
- **States**: If the app has distinct visual states (empty vs populated, light vs dark, logged in vs out), pick the most visually interesting one.

Based on this analysis, plan 1-3 screenshots that best represent the project. Prefer variety: don't take 3 shots of the same page at different scroll positions.

**Take screenshots:** Make sure `.portfolio-data/` exists first (`mkdir -p .portfolio-data`).

For simple captures:
```
npx --yes playwright screenshot --browser chromium --viewport-size "1280,800" http://localhost:PORT .portfolio-data/screenshot-1.png
```

For captures that require interaction (clicking buttons, navigating, waiting for elements), write a short Playwright script inline and run it with `node -e`. Example:
```
node -e "
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:PORT');
  await page.click('button.open-settings');
  await page.waitForSelector('.settings-panel');
  await page.screenshot({ path: '.portfolio-data/screenshot-2.png' });
  await browser.close();
})();
"
```

Read each screenshot back to verify it captured something useful. Cap at 3 total.

**Stop server:** `npx --yes kill-port PORT`

Set `mainImage` to `"screenshot-1.png"` and `images` to all filenames taken.

### Step 3 - Write final files

Write both files directly to `.portfolio-data/`. Do not present drafts or wait for confirmation. Print a short summary of what was written and flag any significant assumptions inline. The user will correct if needed.

## File 1: `metadata.json`

All fields are required.

```json
{
  "title": "",
  "shortDescription": "",
  "type": "",
  "status": "",
  "languages": [],
  "frameworks": [],
  "tools": [],
  "liveUrl": null,
  "mainImage": null,
  "images": [],
  "year": 0,
  "impressiveness": 0
}
```

### Field reference

| Field | Type | Notes |
|---|---|---|
| `title` | string | Display name, not necessarily the repo name |
| `shortDescription` | string | One punchy sentence, under 100 chars |
| `type` | string | Game, Web App, Desktop App, Tray Tool, CLI Tool, Library, Bot, Mobile App, Script |
| `status` | string | `"finished"`, `"in-progress"`, `"abandoned"`, or `"archived"` |
| `languages` | string[] | All languages used |
| `frameworks` | string[] | Actual frameworks and platforms (e.g. Electron, React, Next.js, Express) |
| `tools` | string[] | Build tools, bundlers, utility libraries (e.g. electron-builder, Vite, sql.js, electron-updater) |
| `liveUrl` | string or null | URL if deployed, else `null` |
| `mainImage` | string or null | Filename e.g. `"screenshot.png"`, or `null` |
| `images` | string[] | All image filenames, `[]` if none |
| `year` | integer | Year started or primarily worked on |
| `impressiveness` | integer 1-5 | See scale below |

> `repoUrl` is intentionally absent. The portfolio ingestion script sets it automatically based on repo visibility.

### Impressiveness scale

| Score | Meaning |
|---|---|
| 1 | Throwaway script or tiny utility |
| 2 | Simple but functional |
| 3 | Solid project with decent scope |
| 4 | Technically interesting or well-executed |
| 5 | Flagship - complex, polished, something to be proud of |

Rate honestly based on scope, complexity, and polish. Always flag as an assumption.

## File 2: `PORTFOLIO.md`

Three sections. Each can be one or more paragraphs as needed - don't force everything into a single paragraph if the content benefits from separation. Total target: 150-300 words. Do not pad.

### The What

What is the project and how is it used. Anything immediately interesting about it.

### The Why

Why it was built. What problem it solves. Why an existing tool didn't cover it.

### The How

Interesting technical challenges or decisions. Skip entirely if nothing genuinely interesting. Do not mention the tech stack here.

## Notes

- **Never use em dashes anywhere in generated text.** Use commas, colons, or hyphens instead.
- Image files referenced in `metadata.json` should also live in `.portfolio-data/`
- If updating, preserve fields you have no reason to change
- To force a full refresh, delete `.portfolio-data/` and run again
