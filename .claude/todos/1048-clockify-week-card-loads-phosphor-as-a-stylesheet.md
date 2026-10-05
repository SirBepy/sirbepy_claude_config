<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=75fdfb2c -->
<!-- duplicate-checked: 997 and 830 share only clockify/week/script vocabulary, neither mentions icons or Phosphor -->
# clockify-week card loads the Phosphor icon script as a stylesheet

**Type:** task
**Origin:** ai

## Goal

The hero chips in the clockify-week preview card show their Phosphor icons.

## Context

`skills/clockify-reconciliator/scripts/render_week.cjs:202` loads Phosphor with
`<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web"></link>`. Global CLAUDE.md's UI
section gives the CDN form as a `<script src="https://unpkg.com/@phosphor-icons/web"></script>` tag,
because that URL serves JavaScript that injects the icon CSS.

UNVERIFIED: the chip icons (`ph-square`, `ph-pencil-simple`, `ph-plus-circle`, `ph-users-three`)
render blank today. The script-vs-stylesheet mismatch predicts it. To check, render a card and look
at a chip, or open the unpkg URL and check its content type.

Found 2026-09-29 while writing `skills/iterate-it/scripts/render_report.cjs`, which copied the
template's head, hit the same line, and switched to the `<script>` form.

## Approach

1. Render a sample week with `render_week.cjs` and push it via `show_preview`, then look at whether
   the chip icons appear.
2. If they are blank, replace line 202 with the `<script>` tag and re-render to confirm.

## Acceptance

- A rendered clockify-week card shows an icon in each hero chip.
