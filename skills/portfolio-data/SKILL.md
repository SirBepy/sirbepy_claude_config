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

If `.portfolio-data/metadata.json` exists: read it, identify null/empty/0 fields, fill only those. Tell user if already complete and stop. Skip Step 1 unless core fields (title, description, type) look wrong.

If `.portfolio-data/` does not exist, proceed to Step 1.

### Step 1 - Explore the repo

Read: README, package.json/equivalent, folder structure, source/config files, git history (for year). Infer: languages, frameworks, type, status, year, impressiveness, purpose.

### Step 2 - Ask only what you cannot infer

Do not ask questions upfront. Make your best guesses and flag them.

The only things you may ask before drafting:

- **Live URL** - if none is obvious from docs/config, ask with exactly these options: "Do you have a live URL? Options: **github pages** (I'll use `https://sirbepy.github.io/[repo-name]`), paste a URL, or say none." If they say "github pages", construct the URL from the repo name. Otherwise assume `null`.
- **Images** - use the AskUserQuestion tool with these two options: "Take screenshots automatically (recommended)" and "I'll add them manually". If they choose manually, ask them to drop the files into `.portfolio-data/` and tell you the filenames. If they choose automatically, follow the Auto-Screenshot Workflow below.

If the project's purpose is genuinely ambiguous after reading the code, make a reasonable assumption and flag it.

### Auto-Screenshot Workflow

**Detect type and start command:**

| Check | Type | Port | Command |
|---|---|---|---|
| `vite.config.*` | Vite | 5173 | `npm run dev` |
| `package.json` with React/Next deps | React | 3000 | `npm run dev` |
| `index.html`, no `package.json` | Static | 8080 | `python -m http.server 8080` |

Use port from `vite.config.*` if specified. Run start command with `run_in_background: true` (one Bash call, no chaining).

Poll for readiness: `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT` - up to 15 tries, 1s apart.

**Take screenshots:** Make sure `.portfolio-data/` exists first (`mkdir -p .portfolio-data`).

```
npx --yes playwright screenshot --browser chromium --viewport-size "1280,800" http://localhost:PORT .portfolio-data/screenshot-1.png
```

Read `screenshot-1.png` back to view it. If content below the fold, take a full-page second shot (`--full-page`, `screenshot-2.png`). If distinct views exist in code, take a 3rd. Cap at 3 total.

**Stop server:** `npx --yes kill-port PORT`

Set `mainImage` to `"screenshot-1.png"` and `images` to all filenames taken.

### Step 3 - Draft and present both files

Present both files in separate code blocks. For any field where you made a significant assumption, add an inline note:

> Assumed X - correct me if wrong

Then wait for corrections.

### Step 4 - Apply corrections and write final files

Once confirmed, write the final files to `.portfolio-data/`.

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
| `type` | string | Game, Web App, CLI Tool, Library, Bot, Mobile App, Script |
| `status` | string | `"finished"`, `"in-progress"`, `"abandoned"`, or `"archived"` |
| `languages` | string[] | All languages used |
| `frameworks` | string[] | Frameworks, libraries, platforms |
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

Three short sections. Total target: 150-250 words. Do not pad.

### The What

What is the project and how is it used. Anything immediately interesting about it.

### The Why

Why it was built. What problem it solves. Why an existing tool didn't cover it.

### The How

Interesting technical challenges or decisions. Skip entirely if nothing genuinely interesting. Do not mention the tech stack here.

## Notes

- Image files referenced in `metadata.json` should also live in `.portfolio-data/`
- If updating, preserve fields you have no reason to change
- To force a full refresh, delete `.portfolio-data/` and run again
