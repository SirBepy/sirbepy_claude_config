<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 995 is the preview image-branch gallery script, 330 is /mockup's stage width; neither covers render_markdown.py's layout on a phone -->
# /preview markdown branch needs a phone layout

**Type:** skill-improvement
**Origin:** ai (dashboard-a Hosting chat, 2026-10-22)

## Goal

`/preview`'s markdown renderer (`skills/preview/render_markdown.py`) produces a page Joe can read on his phone. Joe
reviews docs in the Conductor preview panel from his phone, and asked: "Redo the preview so i can properly and easily
see it on my phone".

## Context

- The current output has a sidebar and plain wide tables. On a 390 px screen the tables overflow and the sidebar takes
  room.
- In the dashboard-a Hosting chat, Claude hand-wrote a one-off renderer (in a scratch folder, since deleted) and re-ran
  it three times for one doc. That renderer used the Python `markdown` package with `tables`, `toc` and `sane_lists`,
  and had:
  - `<meta name="viewport">`
  - a collapsible `<details>` table of contents at the top instead of a sidebar
  - 17 px body text and wrapping for code and long words
  - `prefers-color-scheme` dark mode
  - a floating "Top" link
  - **every table turned into labelled cards under 700 px**: each `<td>` gets `data-label` from its `<th>`, shown with
    `td::before { content: attr(data-label) }`; a leading `#` rank column is folded into the first cell ("1. OVHcloud")
- Testing gotcha: headless Edge has a minimum window width of about 492 px, so `--window-size=390,...` screenshots crop
  a 492 px layout and look broken. Test inside a 390 px wide `<iframe>` in a 492 px window instead.

## Approach

Add a responsive mode to `render_markdown.py`: the viewport meta, the card tables under a breakpoint, and the TOC at
the top on narrow screens with the sidebar kept on wide ones. Make it the default. Check with the iframe method above.

## Acceptance

A markdown doc with a 6-column table renders at 390 px wide with no horizontal scroll, the tables shown as cards, and
it looks unchanged on desktop.

## Notes

- render_markdown.py is responsive by default: viewport meta, nav in a details block collapsed at the top under 700px, tables as labelled cards with the # rank column folded into the card title, 17px text with wrapping, prefers-color-scheme dark palette, floating Top link. Verified in headless Edge with the 390px page in an iframe: scrollWidth 375 (no horizontal scroll), cards render; light desktop at 1280px pixel-identical to HEAD. Tests: skills/preview/test_render_markdown.py, 24 failures against HEAD's renderer, all pass now.
