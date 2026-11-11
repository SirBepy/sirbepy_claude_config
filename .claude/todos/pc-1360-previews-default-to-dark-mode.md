<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Every HTML preview Claude writes defaults to dark mode

**Type:** skill-improvement
**Origin:** dev
**Summary:** Make every preview card Claude generates (show_preview, mockups, reports, rendered markdown) dark by default, as a standing rule.

## Why

Joe, 2026-11-11: "i always want previews to be darkmode whenever they can be". He asked for it as a rule, unsure whether it belongs in claude_conductor or `~/.claude`. He saw a light-themed `show_preview` card (a Spotify DIY guide) and had it re-pushed dark.

## Goal

Any HTML Claude pushes into the Conductor preview panel is dark unless Joe asks for light or the content is meant to be shown on a light surface (for example a mockup of a light-themed product).

## Context

- The `show_preview` tool wraps pages in a padded template; a page's own CSS wins (tool description). So Claude's page CSS decides the theme today. UNVERIFIED: whether the panel's own wrapper background is dark or light, and whether it already passes `prefers-color-scheme: dark` into the sandboxed frame. One check settles it: push a page with no CSS and look.
- `skills/preview/render_markdown.py` already follows `prefers-color-scheme` (`skills/preview/SKILL.md` line 45), so the markdown branch may already be dark in a dark panel.
- Working dark recipe used 2026-11-11 for slugs `spotify-family-diy-guide` and `spotify-family-move-checklist`: `<meta name="color-scheme" content="dark">`, `:root{color-scheme:dark}`, `html,body{background:#14161a}`, text `#e4e6eb`, headings `#fff`, muted `#9aa0aa`, dividers `#2e333b`, links `#7db3ff`, code bg `#242830`. Status boxes: green `#16301f` on border `#2f6b44`, red `#3a1b1d` on border `#7a3a3d`, amber `#3a2e14` on border `#7a6230`. Chip colours: blue `#1f3a66`/`#cfe0ff`, pink `#5a2644`/`#ffd6ea`.
- Related but different: pc-1325 (mockup skill: dropdown for choices) covers controls, not theme. No earlier todo or done item mentions dark mode for previews (searched `dark mode`, `color-scheme` across the backlog, `done/`, `CLAUDE.md`, `refs/`, the preview skill).

## Approach

1. Add one line to the "UI & visual changes" section of `~/.claude/CLAUDE.md`: HTML previews (show_preview, mockups, reports) are dark by default; light only on request or when the content is a mock of a light product.
2. Put the dark recipe above in `skills/preview/SKILL.md` as the default page skeleton, and reference it from the mockup, report and clockify week-card skills that emit their own HTML (grep `show_preview` and `render_` under `skills/`).
3. Check `render_markdown.py` renders dark in the panel; if it only follows `prefers-color-scheme`, decide whether to force dark.
4. Optional second todo for the claude-conductor repo (`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar`), only if the first Context check shows the panel wrapper is light: make the `show_preview` wrapper dark by default so Claude's CSS no longer has to. That is the stronger fix, since it works even when a page forgets the recipe. Rejected as the only fix: a CLAUDE.md line alone, because it relies on Claude remembering on every page.

## Acceptance

- A freshly pushed `show_preview` page written by following the skill shows a dark background with readable text, links and code.
- The rule line exists in `~/.claude/CLAUDE.md` and the recipe in `skills/preview/SKILL.md`.
- Rendered markdown previews and existing mockup/report skills are not made unreadable (contrast checked in a screenshot).
- Light mocks of light products can still be shown light on request.

## Notes

- Joe was unsure of the repo; this todo is filed in `~/.claude` because the rule and skills live here. The Conductor-side default is Approach step 4.
