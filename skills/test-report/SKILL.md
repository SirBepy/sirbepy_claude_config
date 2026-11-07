---
name: test-report
description: Records a browser feature test into a narrated report deck. /test-report, or a feature test in a listed repo.
argument-hint: "[feature or ticket to test]"
---

# /test-report

> Record a feature test, then build a watchable, narrated report the dev can open in the panel.

## When it runs

| Situation | Report? |
|---|---|
| A chat tests a feature or ticket end to end in a browser, in a repo that is on | Always, without being asked |
| Same test, in a repo that is off | Only when the dev asks |
| The push gate's e2e suite (`/e2e`) | Never |
| A probe of one or two clicks | Never |

`node ~/.claude/skills/test-report/scripts/enabled.cjs` in the repo prints `on` or `off`. The list is `~/.claude/refs/test-report-repos.txt`. To switch a repo on or off, edit that line.

Decide this BEFORE the test starts: a recording cannot be added afterwards.

## Cost

Claude writes only the words: slide 1, one short explanation per surface, the captions. Scripts make the rest. Do not write custom deck code, and do not hand-read recordings beyond the frame check in Step 5.

Measured 2026-11-04: a 2-step report with 3 lines cost a Sonnet subagent about $0.29 and 83 seconds, with no retakes. Hand the takes and the deck to one `model: 'sonnet'` subagent with a narrow brief, because a long main chat pays its whole context on every call. Keep the dev told how long a run will take: recording runs at real time, plus about 2 minutes to encode.

## Step 1 - Install the voice, once

```powershell
& "$HOME\.claude\skills\test-report\scripts\setup.ps1"
```

Installs a pinned Kokoro voice into `%LOCALAPPDATA%\claude-test-report` (350MB, outside every repo). Skip when `...\claude-test-report\venv\Scripts\python.exe` exists. Raising a pinned version needs the packages safety check first.

## Step 2 - Set up the run

- Work folder: `.for_bepy/screenshots/<id>/report` (any folder name), where `<id>` comes from `~/.claude/skills/close/rename-session.ps1 -GetId`. Use the same folder for `REPORT_WORK`, the build and the check. Deck: `.for_bepy/presentation/<name>.html`. Scripts: `.for_bepy/presentation/<name>-src/`.
- Local backend only, never a deployed one. Backend and bundles must be up before a take. Serve bundles through `/supervised-run` with `-Kind ephemeral`.
- Coordinate the e2e slot with peers (`list_peers`, `read_messages`).

## Step 3 - Write one take per surface or signed-in person

Copy the shape from `examples/biller-groups/`: `lib.cjs` (calls `R.setup` once, holds project URLs and sign-in, re-exports the helpers), `rec-app.cjs` (a take), `report.cjs` (the words). Flutter helpers are in `scripts/flutter.cjs`: `find` returns `{x, y, w, h, disabled}` or null and never throws, `click` throws on a miss.

```js
const R = require(`${process.env.USERPROFILE}/.claude/skills/test-report/scripts/recorder.cjs`);
const F = require(`${process.env.USERPROFILE}/.claude/skills/test-report/scripts/flutter.cjs`); // Flutter web only
R.setup({ chromium, workDir: process.env.REPORT_WORK, refuseUrls: /dev\.example/ });

const s = await R.open({ take: 'app' });
const step = R.stepper(s.page);
await F.goto(s.page, url);
R.begin(s.page);                       // everything before this is cut from the video
await step('Group link shows the landing page', async () => {
  await R.say(s.page, 'The group link');   // returns only after the speech has finished
  // ... drive the page, and throw when a check fails
});
await R.skip(s.page, () => F.goto(s.page, other)); // a boot in the middle: cut it
await R.finish(s);
```

| Rule | Why |
|---|---|
| Every check throws on failure inside `step` | A failed step shows as failed in the report, never hidden |
| One short sentence per `say`, in plain words | It is read aloud, and it decides the video's length |
| `say(page, text, { speak })` for a URL or `.csv` | The caption keeps the exact text, the voice gets words it can read |
| Never speed narrated video up in the encode | It breaks the sync. The player has a speed button |
| Pass `{ min }` only to keep a screen up longer | `say` already holds for the length of the speech |

Run a take with `$env:REPORT_WORK='<work folder>'; node rec-app.cjs`. A request matching `refuseUrls` is aborted before it is sent and `R.finish` then throws, so a take that touches a deployed backend fails. Only exact CDN hosts (`allowHosts`, a regex on the host) get through; any other non-local host gets a stub reply and shows in the take's `outside` list. `R.finish(s, extra)` stores an optional object in the take's JSON. Generating speech is cut from the video, and clips are cached by text, so a retake is free. Flutter driving rules: `~/.claude/refs/flutter-web-playwright.md`.

## Step 4 - Write `report.cjs` and build

```powershell
node "$HOME\.claude\skills\test-report\scripts\build-report.cjs" <report.cjs> <work folder> <out.html>
```

Each slide is `{ title, html }`, and a recording slide adds `{ clip, takes: [...] }`. Names in `takes` are the `take` passed to `R.open`, played in that order, and `clip` is any short name. `tickets: [{ label, url }]` puts ticket links in their own card, so keep them out of the heading. `{{HEADLINE}}` gives the pass or fail line, `{{FAILED}}` a box listing failures. Available classes: `box`, `box warn`, `note`, plain `table`. The order is fixed:

1. **What you need to know.** What the dev must do or decide, first. If nothing, say that plainly.
2. **How the surfaces connect.** Skip it with only one surface, and move the rest of this item to slide 1. Then what it was recorded on (and that it is not a deployed environment), what the script added or cut, and what was not shown.
3. **One slide per surface,** with its recording. A few sentences at most: the step list comes from the take.
4. **Do it yourself.** Short steps.

Say each thing once. FE over BE: mention BE and teammates only where it changes what the dev must do.

The build lowers quality until the page fits the panel's 8MiB cap, and exits non-zero on overlap (3) or on still being too big (4). For 4, cut narration or split into two reports.

## Step 5 - Verify, then show it

```powershell
$env:PLAYWRIGHT='<project>/node_modules/playwright'; node "$HOME\.claude\skills\test-report\scripts\check-report.cjs" <out.html> <work folder>/check
```

It loads the deck in a frame sandboxed like the panel's, and checks click to pause, sound, the auto-scrolling list, full screen and the Next button. Read one `check/slide-N.png` per recording to confirm the caption is on the matching screen. Claude cannot hear the voice: ask the dev about pronunciation.

Push it, then stop the servers you started and restore any local state you changed:

```powershell
node "$HOME\.claude\skills\test-report\scripts\push-preview.cjs" <out.html> <slug> "<title>"
```

Pushing the same slug replaces the old report in place.

## What this skill does not do

The deck stays local. Never send it anywhere, and never commit it.
