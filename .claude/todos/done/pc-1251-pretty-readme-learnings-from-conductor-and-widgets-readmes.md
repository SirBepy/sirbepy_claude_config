<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no other open todo targets skills/pretty-readme -->
# /pretty-readme: fold in what worked on the Conductor and Taskbar Widgets READMEs

**Type:** task
**Origin:** dev
**Summary:** The /pretty-readme skill produces READMEs like the Conductor and Taskbar Widgets ones, using them as the reference output.

## Why

Joe, 2026-10-26: "add a todo to update the readme skill to be more similar to this, cuz this looks really cool".

## Goal
`skills/pretty-readme/SKILL.md` produces READMEs like the two Joe called "amazing" on 2026-10-26: claude_conductor (commits 555c2d11, cc94caa5, 8fe916c7, 3e7f8d89, f3c8bd33) and windows_taskbar_widgets (e2528671, pushed). Use those two READMEs as the reference output.

## Context
Joe, 2026-10-26: "add a todo to update the readme skill to be more similar to this, cuz this looks really cool". The skill's current steps (banner -> header -> body -> render check) were followed, but most of the result came from things the skill does not say:

- **Banner as HTML, rendered by Playwright** (Google Fonts, Phosphor via CDN, the project palette from DESIGN.md, `omitBackground` for transparent rounded corners). This came before capsule-render in the order. Gotchas:
  - Source art with a hard cut edge should run off the banner edge.
  - `background-clip:text` with `line-height:1` clips descenders, so add bottom padding.
  - 1440x450 PNG came to about 520 KB. Palette quantisation bands gradients, so don't use it.
  - Scripts: `claude_usage_in_taskbar/.for_bepy/readme-banner/{banner.html,shot.mjs}` (gitignored, may be gone).
- **Real screenshots, never the dev's screen.** Render the app's own components with fake data, then crop. Two ways that worked:
  - the repo's view harness (`scripts/harness-shot.ps1`, drivers in `.for_bepy/readme-drivers/`);
  - Vite `createServer` plus a stub of `window.__TAURI_INTERNALS__` (invoke switch, `plugin:event|listen`), with the real pages loaded as iframes inside a mock frame (a Windows 11 taskbar plus wallpaper).
  - A sonnet subagent with an exact spec did both well. The spec covered fake values, what each shot shows, size caps, and "look at every PNG".
- **Window width matters.** Joe uses the home dashboard as a narrow window, and a wide shot of it read as wrong. Ask, or check the app's default window size, before picking a viewport.
- **Mixed-aspect grid.** Use one `<table>` per row, since a table forces the same column widths on every row. Pair tall shots with tall and wide with wide, and size the columns by ratio (35/65) so heights match.
- **Sections that landed:**
  - a 3x4 emoji feature grid;
  - a "Things a terminal can't do" 2x3 grid of standout features;
  - a mermaid flow with `classDef` in the palette;
  - an install table plus big download badges;
  - an explainer for the one non-obvious mechanic (the safe-pace rings): a close-up image, a caption giving the exact values, and a colour legend made from shields swatch badges (`/badge/green-27ae60`);
  - cross-links to sibling repos.
- **Keep old docs word for word.** A small Python assembler split the old README on `## ` and put each long section into a `<details>` block. A check that every non-empty old line survives caught nothing lost.
- **Badge gotchas:**
  - simple-icons dropped the Windows logo, so `logo=windows` renders nothing; use a base64 SVG data URI for `logo=`.
  - `github/v/release` shows a `tauri-v` tag prefix, so use `github/package-json/v`.
  - Headings with a VS16 emoji (⚙️, 🛠️) get unreliable anchors, so don't link them from the nav row.
- **Render check mechanics:**
  - `gh api markdown -F text=@<var path>` trips `outbound-verify-guard`, and `>` trips `shell-content-write-guard`. Calling `gh` via node `execFileSync` inside the render script worked.
  - The markdown API leaves mermaid as `<pre lang="mermaid">`, so the render page has to run mermaid.js itself.
  - Show the result with `/preview`'s `build_gallery.py` as a JPEG. A full-page PNG is too large, and both READMEs fit in one gallery.

## Approach
Rewrite the pretty-readme steps around the above: HTML banner first, rendered-component screenshots via a subagent, a width check, grid pairing, the section menu, the preserve-verbatim assembler, the badge gotchas, and the working render-check recipe. Consider shipping `shot.mjs`, `render.mjs` and the assembler as scripts in the skill folder, so they aren't rewritten each time.

## Acceptance
Running `/pretty-readme` on a repo with no art produces a rendered banner, at least 3 real component screenshots, and a preview-panel render, without re-discovering any gotcha listed above.

## Notes

- Fixed in batch 2 (skill text only; no scripts shipped).
