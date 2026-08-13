---
name: screenshot
description: Triggers on /screenshot, and on requests to shoot a matrix of frames/states of a local page (design comps, responsive sweeps). Takes portfolio-quality screenshots of the current project using a persistent Playwright helper script.
---

# /screenshot

> Capture screenshots of the dev project, one per distinct view or state.

## Native windows - the Playwright flow does not apply

Desktop shells (Tauri/Electron windows, tray icons, taskbar strips, OS dialogs) are unreachable
from the browser helper below. Capture them with an ad-hoc PowerShell `System.Drawing` grab
instead, but resolve the output folder via the shared helper - never a hand-built id/path:

```powershell
$dir = & node "C:/Users/tecno/.claude/skills/screenshot/session-shot-dir.cjs"
Add-Type -AssemblyName System.Drawing
$b = New-Object Drawing.Bitmap 1920, 1080
[Drawing.Graphics]::FromImage($b).CopyFromScreen(0, 0, 0, 0, $b.Size)
$b.Save("$dir/strip.png", [Drawing.Imaging.ImageFormat]::Png)
```

`session-shot-dir.cjs` creates the folder if missing and prints its path - it is the single place
the `<pid>-<start-ticks>` id gets resolved (wraps `close/rename-session.ps1 -GetId`), so no caller
hand-builds `.for_bepy/screenshots/...` itself and no capture lands at the root, where `/close`
treats it as unowned legacy and never deletes it (past incident, 2026-08-01: 25 loose captures
from one Tauri icon session had to be cleared by hand).

## Step 1 - Verify helper script

The script must exist at `C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs`,
alongside `session-shot-dir.cjs` (resolves the per-session output folder, see Step 4).
If either is missing, stop and tell the user to restore it.

## Step 2 - Detect and start the server

| Condition | Port | Command |
|---|---|---|
| `vite.config.*` exists | 5173 (or as configured) | `npm run dev` |
| React/Next in `package.json` | 3000 | `npm run dev` |
| `index.html`, no `package.json` | 8080 | `python -m http.server 8080` |

Start with `run_in_background: true`. Poll: `(Invoke-WebRequest -Uri "http://localhost:PORT" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue).StatusCode` up to 15 tries, 1s apart.

## Step 3 - Read the project and plan

Read the root component and routing config. Look for:
- Pages or routes (react-router, file-based, etc.)
- Sections in SPAs (check root component composition)
- Intro animations that block content until triggered
- Hidden UI worth capturing (modals, drawers, toggled panels)

Plan 1-5 screenshots showing distinct views. Do not plan multiple shots of the same layout at different scroll depths.

**Scrolling to sections:** If sections are full-viewport-height, use multiples of 800px (the default viewport height). Read the CSS if unsure.

**Animations:** If the app starts with an intro animation, plan one screenshot before triggering it and one after. Calculate `wait` ms from the animation timing constants in source code.

## Step 4 - Write the plan file

Write a JSON plan to `.portfolio-data/screenshot-plan.json`. The plan is an ordered list of steps executed in one browser session.

**Output path.** Portfolio-quality keepers (this skill's normal output, never purged by `/close`) go under `.portfolio-data/` - use that path in `out` directly. A throwaway verification shot instead: set `out` to a bare filename (e.g. `"check-1.png"`, no directory) and `screenshot-helper.cjs` auto-resolves it into this session's `.for_bepy/screenshots/<pid>-<start-ticks>/` via `session-shot-dir.cjs`, matching `/close`'s Phase 0/3 purge scheme - no id to hand-build. The script refuses any `out` that names `.for_bepy/screenshots/` directly at the root.

Supported step types:

| Type | Fields | Purpose |
|---|---|---|
| `screenshot` | `out` (path) | Capture current view |
| `scroll` | `to` (px) | Scroll to position |
| `click` | `selector` | Click an element |
| `hover` | `selector` | Hover an element (triggers real `:hover` CSS, unlike a dispatched `mouseover` event) |
| `selectOption` | `selector`, `value` | Pick a `<select>` option, firing its `change`/`input` listeners |
| `wait` | `ms` | Pause |
| `waitForSelector` | `selector`, `timeout` (optional ms) | Wait for element |
| `refresh` | - | Reload the page |
| `evaluate` | `js` (string) | Run arbitrary JS in the page context - `js` must be an IIFE (`(function(){...})()`), not a bare arrow function; it runs via `page.evaluate(step.js)` as a string |

Example plan:
```json
[
  { "type": "wait", "ms": 500 },
  { "type": "screenshot", "out": ".portfolio-data/screenshot-1.png" },
  { "type": "click", "selector": ".envelope" },
  { "type": "wait", "ms": 6500 },
  { "type": "screenshot", "out": ".portfolio-data/screenshot-2.png" },
  { "type": "scroll", "to": 800 },
  { "type": "wait", "ms": 600 },
  { "type": "screenshot", "out": ".portfolio-data/screenshot-3.png" }
]
```

## Step 5 - Run the script

One command, one browser session:
```
node "C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs" --url "http://localhost:PORT" --plan ".portfolio-data/screenshot-plan.json"
```

After it completes, read each screenshot back to verify: not blank, not mid-animation, not on a loader. If a screenshot is bad, adjust the plan (longer `wait`, different selector) and re-run.

## Step 6 - Stop the server

```
npx --yes kill-port PORT
```

## Step 7 - Return results

List the screenshots taken and their paths. Do not modify `metadata.json`. Delete the plan file.

## Batch mode - a folder of static HTML files

Trigger: "screenshot every mockup/HTML file in folder X and show them", e.g. a `/mockup` round
that produced several standalone variant files (v1.html, v2.html, ...). This replaces N manually
typed single-file invocations with one documented loop.

1. `Glob` the folder for `*.html`. Confirm the set with the dev if the match looks wrong (wrong
   folder, unexpected count).
2. Prefer this Playwright helper over a chrome-devtools MCP attempt for local files - an MCP
   Chrome instance can fail on a locked profile (wasted a subagent round-trip, 2026-07-31 mockup
   session); this helper launches its own isolated browser every time.
3. For each file, one command, one invocation:
   ```
   node "C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs" --url "file:///<abs-path-to-file.html>" --screenshot "<basename>.png" --viewport 1920x1080
   ```
   The bare filename (no directory) auto-resolves into this session's subfolder, same as Step 4.
   If a file needs interaction before it's ready to shoot (a click, a wait for animation), use
   `--plan` for that file instead of `--click`/`--wait`, same rule as Step 4 - still one command
   per file.
4. Output path: throwaway verification shots auto-resolve into
   `.for_bepy/screenshots/<pid>-<start-ticks>/` via the bare-filename convention above; writing
   directly to the folder root is refused (see the top-of-file rule). A batch that's a portfolio
   keeper instead uses an explicit `.portfolio-data/` path, matching Step 4.
5. After the loop, `Read` every PNG back inline (same verification bar as Step 5: not blank, not
   mid-animation). Report the full list of files captured with their paths.

## Frame matrix mode - many parameterised frames in one command

Trigger: "shoot every state/variant/breakpoint of this component", a design comp round with
several near-identical HTML/bundle variants, or any case that would otherwise mean hand-rolling a
Playwright loop. Replaces the pattern of re-deriving launch/loop/screenshot boilerplate per round.

1. Write a frames JSON array, each entry `{ "name": "..", "url": "..", "query": "..", "width": N,
   "height": N, "wait": N, "deviceScaleFactor": N }`. Give either an absolute/`file://` `url`, or a
   `query`/relative `url` combined with `--base-url`/`--serve` below. `wait` and
   `deviceScaleFactor` are optional; `deviceScaleFactor` defaults to 2 for `width <= 500` (mobile),
   1 otherwise.
2. Pick a source for the pages:
   - Static files: `--serve <dir>` starts a throwaway local server over the directory (needed for
     any bundled/ES-module output, which does not load over `file://`) and tears it down after.
   - Already-running dev server: `--base-url <url>` instead of `--serve`.
3. One command:
   ```
   node "C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs" --frames "frames.json" --out-dir "comp-shots" --serve "path/to/static/dir"
   ```
   `--out-dir` follows the same rule as every other output path: a bare name auto-resolves into
   this session's subfolder, an explicit path must be under `.portfolio-data/`.
4. The command exits non-zero if any frame throws a page error - a blank/broken render never
   reports as captured. Its stdout is `{"captured":[...],"failed":[...]}`.
5. `Read` each captured PNG back, same verification bar as every other mode.
