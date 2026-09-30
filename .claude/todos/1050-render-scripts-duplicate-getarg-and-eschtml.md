<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: first finding about skill render-script helpers -->
# Two skill render scripts each define their own getArg and escHtml

**Type:** task
**Origin:** ai

## Goal

Decide whether the preview-card render scripts share their tiny helpers, and if yes, move them to
`skills/_shared/`.

## Context

From /code-check on commit 054b7df (2026-09-30):

- `getArg`: `skills/iterate-it/scripts/render_report.cjs:9-12` duplicates the export in
  `skills/clockify-reconciliator/scripts/hs_common.cjs:7-10`. The render_report copy adds an
  `i + 1 < args.length` bounds check that the hs_common copy lacks.
- `escHtml`: `skills/iterate-it/scripts/render_report.cjs:33-35` is byte-identical to
  `skills/clockify-reconciliator/scripts/render_week.cjs:46-48`.

`skills/_shared/` already exists as the cross-skill home (it holds `playwright-resolve.cjs`).
Classified as a judgment call, not a mechanical fix: sharing couples two otherwise independent
skills, and neither script has a test. Each helper is 3-4 lines, so leaving the duplicates is a
valid outcome.

## Approach

1. If a third render script appears, or one copy gets a fix the other misses, extract
   `skills/_shared/cli-html.cjs` exporting `getArg` (with the bounds check) and `escHtml`, and
   import it from all three scripts.
2. Otherwise archive this todo as declined.

## Acceptance

- Either one shared module that every render script imports, with each script re-run once to confirm
  it still renders, or this todo archived with the reason it was declined.
