<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 0084, 0930, 0956 are different surfaces; this is a new regression from b232631's claim naming, not the stem-fallback duplication 0794 tracked -->
# claim-todo: a sibling's claim blocks claiming the other file of a duplicate id

**Type:** task
**Origin:** ai
**Summary:** When two todo files share one id, claiming one of them by slug wrongly reports it as already claimed (or deletes the sibling's stale claim).

## Goal

`claim-todo.ps1 -Id pc-NNNN -Slug <b>` claims `<b>` independently of a live claim on the other file that shares `pc-NNNN`, as the contract says ("sibling task's claim survives").

## Context

Found by the 2026-10-30 `/review-unpushed` pass over b232631 (device-prefixed todo ids), not reproduced again by the filing session.

- `skills/close/claim-todo.ps1:195` with `Find-TodoClaims` (`skills/close/_shared.ps1:199-214`): when no slugged claim exists, `Find-TodoClaims` falls back to the plain `<id>.claim`, and the older-name check then treats the sibling's claim as this file's own.
- Reviewer repro: `pc-0007-alpha.md` claimed as `pc-0007.claim`, add `pc-0007-beta.md`, run `claim-todo -Id pc-0007 -Slug beta`: prints "already claimed under the older name pc-0007.claim - not stale, skipping", exit 1. If the sibling's claim is stale it gets deleted instead.
- Before b232631 the claim was named `<id>-<slug>.claim` independently, so this is a regression.
- Live duplicate ids per the reviewer: pc-0096, pc-0097, pc-0307, pc-0335, pc-0338.

## Approach

Only fall back to the plain `<id>.claim` when the id resolves to exactly one backlog file; with a `-Slug` and 2+ files for the id, look only at `<id>-<slug>.claim`. Add the repro above as a test in `tools/test_close_claim_complete.py`.

## Acceptance

- The repro claims beta and leaves `pc-0007.claim` untouched.
- A single-file id still migrates its older-name claim as before.

## Notes

Same review, lower value, fold in if cheap:
- `skills/commit/todo-ref.sh:33`: the optional `label-` group added in b232631 flags comments like `// todo list-3 items remain` or `// TODO handle-1 case` as todo refs. Require the label to match a device label followed by a 4-digit number, or keep requiring digits right after `todo ` for the unlabelled form.
- `tools/migrate-todo-ids.py:303`: a repo whose `apply_repo` raises midway never reaches the undo log. Low value: the migration already ran.
