<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Document the advanced-but-not-finished outcome in the backlog contract, not just in /pickup

**Type:** skill-improvement
**Origin:** ai

## Goal

Move the Completed versus Advanced-but-not-finished distinction into
`skills/close/ai-todos-format.md`, so every executor honours it rather than only the one skill that
happens to describe it.

## Context

Todo 374 (archived 2026-08-19, commit `8b2e904`) split `/pickup` Step 7 into two endings: a
completed todo runs `complete-todo.ps1` and archives, while one that advanced but did not finish
gets its file and PLAN.md line updated, its claim released, and its remaining work named, without
moving to `done/`.

That distinction now lives only in `skills/pickup/SKILL.md`. But `/batch-todos`, `/autopilot`,
`/auto-do-todos` and `/mega-todos` all execute todos through the same contract, and none of them
has any ending except "archive it". So the same epic-scale todo picked up through a different
entrypoint still gets wrongly archived.

374's own text raised this, and its builder reported it as out of scope because
`ai-todos-format.md` was owned by a different lane during that run.

## Approach

1. Add the two outcomes to `ai-todos-format.md`, next to the existing Claims and Release rules,
   with the same decidable tell 374 settled on (the Goal names an epic, or Acceptance carries items
   this session could not address).
2. Have `skills/pickup/SKILL.md` POINT at the contract rather than restating it, so the two cannot
   drift. That is the pattern todo 369 just applied to `/auto-do-todos`.
3. Check whether `complete-todo.ps1` should grow a flag for the not-finished path, or whether that
   path should deliberately not touch the script at all. Decide and write down which.

## Acceptance

- `ai-todos-format.md` describes both outcomes and the tell that picks between them.
- `skills/pickup/SKILL.md` no longer carries its own copy of the rule.
- The other executors either follow the contract or explicitly say why they do not.

## Notes

- Fixed 2026-08-25, all three approach steps. ai-todos-format.md gained a 'Two endings, and the tell that picks between them' section stating it binds EVERY executor, not just /pickup. pickup/SKILL.md Step 7 no longer carries its own copy, it points at the contract. Step 3 decided and written down: complete-todo.ps1 gets NO flag for the not-finished path, because its three jobs are archive/prune/release and that path wants only release - a flag skipping two of three would blur what the script guarantees, and deleting your own claim is not a race since the mutex governs acquisition. Also closed the third acceptance item, which the todo's own approach did not spell out: auto-do-todos Step 6.3 and mega-todos Step E.1 both said 'archive it' unconditionally and now defer to the contract, so no executor contradicts it.
