<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 385 is the /preview push helper (posting HTML to the panel); this is building and sandbox-verifying a bundled interactive board before that push. 44/264/889/04 share only generic words. -->
# /mockup: ship a reusable "bundle the real app code" build + sandbox-verify template

**Type:** skill-improvement
**Origin:** ai

## Goal
Make an interactive /mockup that runs a web project's real modules a one-command job instead of a
hand-copied build script per board.

## Context
In claude_usage_in_taskbar (2026-10-15/16, Drafts redesign) Claude built four interactive boards
(`.for_bepy/mockups/mockup-drafts-{quiet,live,older}.*`, `mockup-draft-editor.*`), each by copying
the previous `*-build.mjs` (vite `build()` with `configFile:false`, inline JS/CSS into one HTML) and
`*-verify.cjs` (Playwright, board inside `<iframe sandbox="allow-scripts">`, real mouse clicks,
screenshot) and renaming strings. The sandboxed-iframe + real-click verify caught a real shipped bug
a plain tab could not (a focus refresh swallowing the first click). `skills/mockup/SKILL.md` only
covers the iframe-sandbox concern for boards that frame live pages, not bundled ones, and has no
template for the bundle path. Project memory in that repo:
`project_interactive_mockup_bundles_real_code.md`. Pushing the result is todo 385's concern.

## Approach
Add to `skills/mockup/` a `bundle-board.mjs <src.html> <out.html>` script (the vite build + inline
step) and a `verify-board.cjs <out.html> <shotdir> [plan.json]` script (sandboxed iframe, real
clicks from a plan, screenshot, pageerror capture). Reference both from SKILL.md's Spliced-CSS /
real-component branches, plus the two gotchas: stub `navigator.clipboard` (sandbox denies it) and
prefix board CSS overrides with the component's root class (the bundled real CSS loads after the
board's own `<style>`).

**Verify through the panel's real route, not a hand-made iframe (added 2026-10-20).** A theme-picker
board passed a sandboxed `data:` iframe verify with every interaction green, then rendered dead in the
panel; Joe: "we should make sure the /mockup actually works when you hand it over to me". The panel
runs pushed HTML through `buildPreviewDocumentHtml` (claude_usage_in_taskbar
`src/views/sessions/preview-panel-document.ts`), which splices a diagnostics `<script>` before the
FIRST literal `</body>` in the raw text; the board's inline script held the string `"</body>"`, so
the splice closed that script early. `verify-board` should therefore transpile that TS (vite
`transformWithEsbuild`), `POST http://127.0.0.1:27182/hooks/preview-render` with its output, and
drive `GET /hooks/preview-render/<id>` inside the sandboxed iframe. Working example:
`.for_bepy/mockups/mockup-theme-picker-verify.mjs` in that repo. SKILL.md gotcha line: never put a
literal `</body>`, `<head` or `<html` inside an inline script or comment of a pushed page.

## Acceptance
- A new interactive board needs only a `.src.html` + `.ts`; build and verify are single commands.
- The verify command loads the board through `/hooks/preview-render`, and a board holding `"</body>"` in an inline script fails it.
- SKILL.md tells the next session to verify with real clicks inside the sandbox.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): bundle-board.mjs (vite from --project/BOARD_PROJECT, inlines JS/CSS, escapes </body> etc.) and verify-board.cjs (sandboxed iframe, real clicks from a plan, pageerror capture), documented in mockup SKILL.md; 8/8 offline checks pass. NOT run live: the default --route panel POST/GET against 127.0.0.1:27182 was not exercised in an unattended loop.
