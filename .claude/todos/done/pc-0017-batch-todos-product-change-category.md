<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=28080b2a -->
# batch-todos: add a product-change category that's never auto-executed

**Type:** skill-improvement

## Goal

/batch-todos should recognise todos that are **product/behavior changes** and keep them
out of the auto-executable set, distinct from EASY (auto-run) and HARD (dev-picks-then-run).

## Context

During a 2026-07-12 run, the classifier ranked `#04` (wire-or-hide the Approve Orders
button) as an "important todo that needs doing." Joe corrected that it's a product change
and shouldn't be executed in a batch/audit pass at all — only when deliberately doing
product work. The current EASY/HARD split doesn't capture this: a product change can look
"HARD but important" and get surfaced as actionable, which is the wrong frame. See memory
`feedback-product-change-vs-code-health-todos`.

## Approach

In `C:\Users\tecno\.claude-fibo\skills\batch-todos\SKILL.md`:
- In the classification step, add a third label PRODUCT (alongside EASY/HARD): any todo
  that adds, removes, or alters user-facing functionality, or whose own file carries a
  `Type: product-change` header.
- PRODUCT todos are listed separately in the dry-run and are NEVER auto-executed and NEVER
  surfaced under "important todos that need doing" — they're only offered when Joe explicitly
  says he's doing product work.
- Respect an existing `Type: product-change` header in a todo file as an authoritative
  PRODUCT signal (don't re-litigate).

## Acceptance

- SKILL.md documents the PRODUCT label, its detection rule, and that it's excluded from
  both auto-execution and the "important" ranking.
- A todo file tagged `Type: product-change` is always classified PRODUCT.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 88; renumbered to 17 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Implemented 2026-08-08: added PRODUCT label to `skills/batch-todos/SKILL.md`'s Step 3 classify table (checked before EASY/HARD, `Type: product-change` header authoritative), a separate PRODUCT section in Step 4's dry-run report, and an explicit exclusion from Step 7's HARD/urgency ranking.
