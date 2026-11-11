<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Every HTML preview Claude writes defaults to dark mode

**Type:** skill-improvement
**Origin:** dev
**Summary:** Make every preview card Claude generates dark by default as a standing rule, including hand-written show_preview pages and the generators that only follow the system theme.

## Why

Joe, 2026-11-11: "i always want previews to be darkmode whenever they can be". He asked for it as a rule, unsure whether it belongs in claude_conductor or `~/.claude`. He saw a light-themed hand-written `show_preview` card (a Spotify DIY guide) and had it re-pushed dark.

## Goal

Any HTML Claude pushes into the Conductor preview panel is dark unless Joe asks for light or the content is meant to be shown on a light surface (for example a mockup of a light-themed product).

## Context

Dark support already exists in part, so this todo closes the gaps rather than starting from zero:

- Already dark by default: a bare fragment is "wrapped in a dark page first" (`skills/preview/SKILL.md:34`); `skills/mockup/SKILL.md:160`, `skills/iterate-it/scripts/render_report.cjs:122` and `skills/clockify-reconciliator/scripts/render_week.cjs:228` emit `<meta name="color-scheme" content="dark">`.
- Follows the system theme only (dark only if the panel reports a dark scheme): `skills/preview/render_markdown.py:18-19` (`color-scheme:light dark`, dark palette under `@media (prefers-color-scheme:dark)`), `skills/report/build_report.py:179-180`, `skills/test-report/scripts/template.html:4-5`. UNVERIFIED whether the panel frame reports a dark scheme to the sandboxed page; the check that settles it is a pushed page with `color-scheme:light dark` and no other colour CSS.
- Forced light: `skills/preview/build_gallery.py:142-143` and `:302-303` set the page body to `background:#fbfcfd`, and `:159` uses `background:#fff`; there is no `color-scheme` meta or dark CSS. Every screenshot or keep/drop gallery built through the preview skill's image branch is therefore light, and its own body style wins over the panel default (`skills/preview/SKILL.md:35`).
- The gap that triggered this: a full hand-written `<html>` page pushed through `show_preview` has no default; its own CSS wins ("Your own CSS wins", `skills/preview/SKILL.md:35`). Claude wrote it light on 2026-11-11. UNVERIFIED reason: probably no rule said otherwise; the check is whether any loaded instruction on that date mentioned a theme (grep `CLAUDE.md` and the preview skill for "dark", which found only the lines cited above).
- Prior work, related but not the same: `done/pc-1242-preview-markdown-branch-needs-a-phone-layout.md:24` (markdown renderer got a `prefers-color-scheme` dark palette) and `done/pc-1209-report-skill-for-shareable-html-reports.md:40` (report template decided "light/dark", i.e. follows the scheme). Neither forces dark nor covers hand-written pages. `pc-1325` (mockup dropdowns) covers controls, not theme.
- Working dark recipe used 2026-11-11 for slugs `spotify-family-diy-guide` and `spotify-family-move-checklist`: `<meta name="color-scheme" content="dark">`, `:root{color-scheme:dark}`, `html,body{background:#14161a}`, text `#e4e6eb`, headings `#fff`, muted `#9aa0aa`, dividers `#2e333b`, links `#7db3ff`, code bg `#242830`. Status boxes: green `#16301f` on border `#2f6b44`, red `#3a1b1d` on border `#7a3a3d`, amber `#3a2e14` on border `#7a6230`. Chip colours: blue `#1f3a66`/`#cfe0ff`, pink `#5a2644`/`#ffd6ea`.

## Approach

1. Add one line to the "UI & visual changes" section of `~/.claude/CLAUDE.md`: HTML previews (show_preview, mockups, reports) are dark by default; light only on request or when the content mocks a light product.
2. Put the dark recipe above in `skills/preview/SKILL.md` as the default skeleton for a hand-written full page (next to line 34-35).
3. Decide per generator that only follows the system theme (`render_markdown.py`, `skills/report/build_report.py`, `skills/test-report/scripts/template.html`): force dark, or keep following the scheme if the UNVERIFIED check above shows the panel reports dark. Give `skills/preview/build_gallery.py` a dark palette (it is forced light today). Skip the ones already forced dark (see Context).
4. Optional second todo in the claude-conductor repo (`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar`), only if the UNVERIFIED check shows the panel does not report a dark scheme: make the `show_preview` wrapper dark by default so Claude's CSS no longer has to. That is the stronger fix, since it works even when a page forgets the recipe. Rejected as the only fix: a CLAUDE.md line alone, because it relies on Claude remembering on every page.

## Acceptance

- A freshly pushed hand-written `show_preview` page written by following the skill shows a dark background with readable text, links and code.
- The rule line exists in `~/.claude/CLAUDE.md` and the recipe in `skills/preview/SKILL.md`.
- Rendered markdown, report, test-report and `build_gallery.py` gallery outputs show dark in the panel (screenshot checked for contrast), or step 3 records why the first three stay scheme-following.
- Light mocks of light products can still be shown light on request.

## Notes

- Joe was unsure of the repo; this todo is filed in `~/.claude` because the rule and skills live here. The Conductor-side default is Approach step 4.
