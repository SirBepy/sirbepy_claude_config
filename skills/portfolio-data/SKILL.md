---
name: portfolio-data
description: Use this skill when the user asks to generate portfolio data, create portfolio files, or says "generate portfolio data". Generates .portfolio-data/metadata.json and .portfolio-data/PORTFOLIO.md for a project repo.
---

# Portfolio Data Skill

Generates two files for any project repo, consumed by the portfolio site's GitHub Action at build time:

1. `.portfolio-data/metadata.json` — structured data
2. `.portfolio-data/PORTFOLIO.md` — short project write-up

---

## Workflow

### Step 1 — Explore the repo

Before writing anything, explore the repository. Look at:
- README, package.json / pubspec.yaml / Cargo.toml / go.mod / equivalent
- Folder structure, source files, config files
- Git history if available (for year)
- Any existing `.portfolio-data/` files (if updating, use them as a base)

Infer from this: languages, frameworks, type, status, year, impressiveness, and what the project actually does and why it was built.

### Step 2 — Ask only what you cannot infer

Do not ask questions upfront. Make your best guesses and flag them.

The only things you **may** ask before drafting:
- **Live URL** — if none is obvious from docs/config, ask with exactly these options: "Do you have a live URL? Options: **github pages** (I'll use `https://sirbepy.github.io/[repo-name]`), paste a URL, or say none." If they say "github pages", construct the URL from the repo name. Otherwise assume `null`
- **Images** — use the AskUserQuestion tool with these two options: "Take screenshots automatically (recommended)" and "I'll add them manually". If they choose manually, ask them to drop the files into `.portfolio-data/` and tell you the filenames. If they choose automatically, follow the **Auto-Screenshot Workflow** below.

If the project's purpose is genuinely ambiguous after reading the code, make a reasonable assumption and flag it.

---

### Auto-Screenshot Workflow

#### 1. Detect project type

Check the working directory for:
- `vite.config.js` or `vite.config.ts` → **Vite** project. Default port: `5173`. Start command: `npm run dev`
- `package.json` with a `dev` or `start` script and React/Next deps → **React** project. Default port: `3000`. Start command: `npm run dev` (prefer) or `npm start`
- `index.html` with no `package.json` → **Static HTML**. Port: `8080`. Start command: `python -m http.server 8080`

If `vite.config.*` specifies a port, use that instead of the default.

#### 2. Start the dev server

Run the start command using Bash with `run_in_background: true`. Do NOT chain commands — one Bash call only.

Then poll for readiness: run `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT` in a loop (up to 15 tries, 1 second apart). Stop as soon as you get a non-zero HTTP response.

#### 3. Take screenshots

Run this command once for the main view (not full-page):
```
npx --yes playwright screenshot --browser chromium --viewport-size "1280,800" http://localhost:PORT .portfolio-data/screenshot-1.png
```

Then read `screenshot-1.png` back using the Read tool to view it. Based on what you see:
- If the page has meaningful content below the fold, take a second full-page screenshot:
  ```
  npx --yes playwright screenshot --browser chromium --viewport-size "1280,800" --full-page http://localhost:PORT .portfolio-data/screenshot-2.png
  ```
- If the project has clearly distinct views or routes visible from the code (e.g. `/about`, a modal, a second tab), navigate to one and take a third screenshot. Only do this if it meaningfully showcases something the first two don't.
- Cap at 3 screenshots total.

Make sure `.portfolio-data/` exists before writing screenshots (create it with `mkdir -p .portfolio-data` if needed — one Bash call).

#### 4. Stop the dev server

Find the PID and kill it. For npm/vite processes on Windows, run:
```
npx kill-port PORT
```
(uses `npx --yes kill-port PORT` — no install needed)

For static Python server, kill by port the same way.

#### 5. Set image fields

Set `mainImage` to `"screenshot-1.png"` and `images` to all screenshot filenames taken (e.g. `["screenshot-1.png", "screenshot-2.png"]`).

---

### Step 3 — Draft and present both files

Present both files in separate code blocks. For any field where you made a significant assumption, add an inline note:

> ⚠️ *Assumed X — correct me if wrong*

Then wait for corrections.

### Step 4 — Apply corrections and output final files

Once the user confirms or corrects, output the final versions ready to copy into `.portfolio-data/`.

---

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
| `title` | string | Display name — not necessarily the repo name |
| `shortDescription` | string | One punchy sentence, under 100 chars |
| `type` | string | e.g. Game, Web App, CLI Tool, Library, Bot, Mobile App, Script |
| `status` | string | Exactly one of: `"finished"` · `"in-progress"` · `"abandoned"` · `"archived"` |
| `languages` | string[] | All languages used, e.g. `["TypeScript", "Lua"]` |
| `frameworks` | string[] | Frameworks, libraries, platforms, e.g. `["React", "Tailwind"]` |
| `liveUrl` | string \| null | URL if deployed/live, otherwise `null` |
| `mainImage` | string \| null | Filename e.g. `"screenshot.png"`, or `null` |
| `images` | string[] | All image filenames; `[]` if none |
| `year` | integer | Year started or primarily worked on |
| `impressiveness` | integer 1–5 | See scale below |

### Impressiveness scale

Rate honestly based on scope, complexity, and polish found in the repo. Always flag this as an assumption.

| Score | Meaning |
|---|---|
| 1 | Throwaway script or tiny utility |
| 2 | Simple but functional |
| 3 | Solid project with decent scope |
| 4 | Technically interesting or well-executed |
| 5 | Flagship — complex, polished, something to be proud of |

> `repoUrl` is intentionally absent. The portfolio ingestion script sets it automatically based on repo visibility.

---

## File 2: `PORTFOLIO.md`

Three short sections. Total target: **150–250 words**. Do not pad — write as much as the project genuinely warrants and no more.

### The What
What is the project and how is it used. Anything immediately interesting about it.

### The Why
Why it was built. What problem it solves. Why an existing tool didn't cover it.

### The How
Interesting technical challenges or decisions worth calling out. **Skip this section entirely** if there's nothing genuinely interesting to say. Do not mention the tech stack here — that's already in `metadata.json`.

---

## Notes

- Image files referenced in `metadata.json` should also live in `.portfolio-data/` (e.g. `.portfolio-data/screenshot.png`)
- If `.portfolio-data/` already exists, update the existing files rather than replacing blindly — preserve any fields you have no reason to change
- If updating, still re-read the repo before drafting in case things have changed
