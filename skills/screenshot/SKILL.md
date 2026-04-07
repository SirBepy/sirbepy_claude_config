---
name: screenshot
description: Triggers on /screenshot only. Takes portfolio-quality screenshots of the current project using a persistent Playwright helper script.
---

# /screenshot

> Capture screenshots of the dev project, one per distinct view or state.

## Step 1 - Verify helper script

The script must exist at `C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs`.
If it is missing, stop and tell the user to restore it.

## Step 2 - Detect and start the server

| Condition | Port | Command |
|---|---|---|
| `vite.config.*` exists | 5173 (or as configured) | `npm run dev` |
| React/Next in `package.json` | 3000 | `npm run dev` |
| `index.html`, no `package.json` | 8080 | `python -m http.server 8080` |

Start with `run_in_background: true`. Poll: `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT` up to 15 tries, 1s apart.

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

Supported step types:

| Type | Fields | Purpose |
|---|---|---|
| `screenshot` | `out` (path) | Capture current view |
| `scroll` | `to` (px) | Scroll to position |
| `click` | `selector` | Click an element |
| `wait` | `ms` | Pause |
| `waitForSelector` | `selector`, `timeout` (optional ms) | Wait for element |
| `refresh` | - | Reload the page |
| `evaluate` | `js` (string) | Run arbitrary JS in the page context |

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
