<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# clockify-reconciliator/SKILL.md carries two gated optional modes inline instead of read-on-demand

**Type:** skill-improvement
**Origin:** ai

## Goal

Move `Reconstruction mode` and `Audit mode` out of `skills/clockify-reconciliator/SKILL.md`'s
always-loaded body and into a read-on-demand sub-file, the way the same skill already treats
`hubstaff.md`.

## Context

Surfaced by the `/code-check` verification pass of the 2026-08-12 `/auto-do-todos` run, which added
both modes (todos 34 and 82, commit `8d83c75`). The file went from 139 to 259 lines, +86%. Roughly
47 of those lines are the two new mode sections, and Step 3a explicitly gates both: a normal
Reconciliation run never enters either, and both require the dev's explicit confirmation first.

The same file already demonstrates the right pattern one section later: HubStaff procedure lives in
`hubstaff.md` and is pulled in only when that path is taken. The two new modes were added inline
instead, so every ordinary run loads procedure it will not use.

## Approach

Extract both sections to `skills/clockify-reconciliator/modes.md` (or one file per mode if they read
better apart), leaving a one-line pointer in SKILL.md's Step 3a next to the mode-resolution rule.
Keep the gating logic itself in SKILL.md, since that is what decides whether to read further; only
the per-mode procedure moves. Check the Rules section afterwards, some of its new billable/overlap
rules were written for the modes and may belong with them.

## Acceptance

- `skills/clockify-reconciliator/SKILL.md` is back near its pre-change size, with Step 3a pointing
  at the sub-file rather than inlining both procedures.
- A Reconciliation run never needs to read the mode procedures.
- Nothing from either mode is lost in the move; a diff of the extracted text against `8d83c75`
  accounts for every line.

## Notes

- Filed by the wrap-up verification of the 2026-08-12 `/auto-do-todos` run, not by the dev.
