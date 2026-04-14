---
name: test-flow
description: Triggers on /test-flow only. Drives a Flutter web app via Playwright MCP against a test plan markdown file, executing each step, watching the browser console for errors, and marking each step pass/fail/skip inline.
---

# /test-flow

> Walk a Flutter web app through a human-written test plan. For each step, drive Playwright, watch the browser console, and mark the result directly in the plan file.

## Why this skill exists

- Joe develops Flutter web apps and wants AI-assisted manual QA without giving up his VS Code F5 + launch.json + breakpoints flow.
- He runs the app himself. This skill never starts or stops the dev server.
- Flutter web renders to canvas, so normal Playwright selectors don't work. Semantics are enabled in debug builds via `WidgetsBinding.ensureSemantics()` inside an `assert`. This emits a DOM tree Playwright can query by label/role.
- Browser DevTools console catches ~90% of runtime errors, network failures, and app logs. Joe's Debug Console catches the Dart-specific rest; he watches that himself.

## Invocation

```
/test-flow <path-to-test-plan.md> [--url http://localhost:PORT]
```

- `<path-to-test-plan.md>`: required. Markdown file containing the plan. The skill edits this file inline as it runs.
- `--url`: optional. Dev server URL. If omitted, ask Joe for it using AskUserQuestion with sensible guesses (3000/5000/8080/random Flutter port from recent chromium tabs).

## Required tools

- Playwright MCP tools (all under `mcp__playwright__*`): `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_press_key`, `browser_wait_for`, `browser_console_messages`, `browser_take_screenshot`, `browser_evaluate`, `browser_close`.
- `Read` and `Edit` for the test plan file.

If the Playwright MCP isn't connected, stop immediately and tell Joe to restart Claude Code.

## Preconditions checklist (run once at start)

1. **Test plan file exists** — if the path doesn't resolve, stop and ask.
2. **Dev server URL is known** — either from `--url` or by asking Joe.
3. **App is running** — `browser_navigate` to the URL; if it fails, tell Joe to F5 and retry.
4. **App is authenticated** — snapshot the landing page. If it looks like a login screen, stop and ask Joe to log in first (we do NOT log in for him; staff creds shouldn't be in prompts).
5. **Semantics are live** — `browser_snapshot` should return a non-trivial accessibility tree. If it's empty, Flutter semantics didn't initialize; tell Joe to verify `binding.ensureSemantics()` is in `main.dart` and that he's running a debug build (not `--release`).
6. **Console is clean** — call `browser_console_messages` once to drain any startup noise; warn Joe about any errors already present before we start touching things.

## Test plan file format

Each step is a markdown checklist item. Accepted prefixes:

- `- [ ]` — pending
- `- [x]` — passed (set by this skill)
- `- [!]` — failed (set by this skill)
- `- [~]` — skipped (set by this skill, with reason)

Steps can be grouped under `##` headings. Everything else (intro paragraphs, notes) is left alone.

Optional per-step metadata uses indented sub-bullets the skill recognizes:

```
- [ ] Click the Filters button
  - expect: popup opens with two checkboxes
  - console: no new errors
```

If a step needs setup/cleanup that the AI can't do (a specific biller in a specific state, a backend-seeded row, etc.), Joe writes it as plain text above the step and the skill reads it for context but doesn't try to execute it.

## Execution loop (for each pending step)

1. **Read the step** from the plan file. Parse its intent.
2. **Drive Playwright.** Use semantic labels from the snapshot to locate elements. Never click by coordinates. If you can't find the element, mark the step `[!]` with a note "could not locate element: <label>" and continue.
3. **Wait for settle.** After interactions, call `browser_wait_for` with a short timeout or look for a specific expected element/text.
4. **Verify expectations.**
   - Visual: `browser_take_screenshot` and compare against the step's `expect:` description. Save screenshots to `.claude/test-runs/<timestamp>/<step-number>.png` (relative to the test plan file's directory).
   - Console: `browser_console_messages` — diff against the last seen message count. Any new `error` or `warning` level messages get logged under the step.
   - DOM/state: use `browser_evaluate` for JS probes when semantics can't express it.
5. **Mark the step.**
   - `[x]` if expectations met and no new console errors.
   - `[!]` if any expectation failed or new console errors appeared. Append a sub-bullet with the failure reason and the screenshot path.
   - `[~]` if the step is unreachable (e.g. previous step failed and this depends on it). Append a sub-bullet with "skipped: <reason>".
6. **Update the plan file** via Edit tool. Do not batch updates; write after each step so Joe sees progress live.
7. **Stop conditions.**
   - Hard stop: Playwright connection dies, browser crashes, the dev server returns non-200 on navigation.
   - Soft stop: 3 consecutive `[!]` on dependent steps — ask Joe whether to continue.

## Final report

After the loop ends, append a `## Run summary` section to the plan file:

```
## Run summary (YYYY-MM-DD HH:MM)

- Total: N steps
- Passed: X
- Failed: Y
- Skipped: Z
- New console errors: list with file:line if available
- Screenshots: .claude/test-runs/<timestamp>/

### Failures
1. Step "..." — <one-line reason>
...
```

Keep the summary terse. Joe reads the file, reruns `/test-flow` after fixes — the skill should be idempotent: on rerun, reset all `[x]`/`[!]`/`[~]` back to `[ ]` if the user confirms, or only re-run failed steps if they pass `--only-failed`.

## Things to NOT do

- Do not edit application code during a test run. Report failures only.
- Do not commit anything.
- Do not create new tickets when things fail; Joe decides.
- Do not log in, type passwords, or submit forms with credentials.
- Do not close the browser after the run unless Joe passes `--close`. He often wants to keep poking manually after.
- Do not add, remove, or reorder steps in the plan file. Steps are Joe's spec; the skill only flips their state.

## Fallbacks

- If `browser_snapshot` returns canvas-only content with no semantic tree, warn Joe that semantics aren't on and offer to proceed in "screenshot-only mode" where every step is marked `[~]` and pasted with a screenshot for him to eyeball.
- If a step is ambiguous ("check the Filters button"), use AskUserQuestion with 2-3 interpretations before guessing.
