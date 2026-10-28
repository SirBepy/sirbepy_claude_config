<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=7, reconfirm-count=2, content-hash=33a49b33 -->
<!-- duplicate-checked: no live or done todo covers the preview skill's image branch; the render_markdown.py script covers markdown only -->
# /preview image branch needs a real gallery script instead of a hand-typed builder per push

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/preview/SKILL.md`'s image branch becomes one command, the way its markdown branch already is with `render_markdown.py`: given N image paths (or a directory), it builds the gallery HTML with the 1.5 MB raw-byte budget split, POSTs it to `http://127.0.0.1:27182/hooks/preview` with the slug/title, and prints included/dropped files plus the HTTP status.

## Context

Observed 2026-09-12 in `wedding_invitation` (session `98ea81a3`): seven separate image pushes to the Conductor preview panel, and every one was the same ritual, hand-typed: Write a `C:\tmp\preview-build.mjs` that base64-inlines a hardcoded file list, run it, `curl.exe --data-binary @body.json`, delete both files. The skill documents exactly this ritual (SKILL.md "Image branch", the commented-out `node -e` block) because a `node -e` one-liner cannot carry the embedded quotes in PowerShell 5.1, but it stops at "write the builder to a file" and leaves the file to be re-authored every time. Two pushes silently dropped mobile screenshots to the budget cap and needed a second gallery each; one attempt to push a mockup board with embedded base64 fonts hit the ~2 MB cap outright (HTTP 413-class refusal) and was replaced by a PNG of the page instead.

Repeated manual step by the /close retrospective's definition (same action 2+ times by hand). `render_markdown.py` next to the skill is the pattern to copy.

Seen again 2026-10-05 in `mc_plugins_tag` (spawn-market session `4dd74c84`): five hand-written gallery builders in one session, and Joe asked "let me click the images on the /preview window". The fix was a small inline lightbox (click an image to open it full-size, arrow keys step, Esc or click closes), verified with the screenshot helper (overlay `display:flex`, image 960x540). The gallery script should ship that lightbox by default.

## Approach

- Add `skills/preview/build_gallery.py` (or `.mjs`, either is fine; Python matches the sibling script) taking `<image...|dir> [--slug] [--title] [--budget-mb 1.5] [--post]`. It expands directories, sorts, applies the raw-byte budget (drop that file and everything after, report every dropped name), writes the gallery HTML, and with `--post` sends the JSON body itself (title, slug, html, source "terminal", session_id from `CLAUDE_CODE_SESSION_ID`) and prints the response id and status.
- When files are dropped for budget, print a ready-to-run second command for the remainder, so a two-gallery push is copy-paste, not re-authoring.
- Update SKILL.md's image branch to call the script, keeping the current inline builder text only as the fallback when Python is unavailable.
- Rejected: raising the budget (the endpoint's ~2 MB cap is the host app's, not this skill's).

## Acceptance

- `python skills/preview/build_gallery.py a.png b.png --slug x --title y --post` pushes one gallery and prints `included: 2 dropped: [] HTTP 200`.
- Over-budget input prints the dropped names and the follow-up command; nothing is truncated.
- Clicking a gallery image opens it full-size in an overlay (arrows step, Esc/click closes).
- `ci/run_all.py` green; the skill description stays within its word budget.

## Notes

- 2026-10-03, folded in from a claude_usage_in_taskbar /close: the plain **HTML file** push has the
  same problem. A Code mode mockup was re-pushed to one slug about fifteen times, each a retyped
  `node -e` body builder + `curl.exe` + temp cleanup. Make the script's push path take a plain
  `.html` file too (`<file> --slug --title --post`), so all three branches share it. Add a
  `--check` that POSTs the html to `/hooks/preview-render`, loads `/hooks/preview-render/<id>`
  headless (`screenshot/screenshot-helper.cjs`), and fails on a page error: a doc that rendered
  fine from `file://` threw an inline-script parse error in the panel that same session.
- Done in loop-todos cycle 2 (2026-10-06): gallery pages get an inline lightbox (click to open, arrows/keys to step, Esc or backdrop to close), verified headless in chromium; --check POSTs to /hooks/preview-render and loads /hooks/preview-render/<id> headless, failing on a page error before --post (endpoint and {id} shape confirmed in claude_usage_in_taskbar hooks_server/preview_render.rs:30-36). 29/29 tests pass.
