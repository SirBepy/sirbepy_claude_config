<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=6, reconfirm-count=1, content-hash=1aa897d9 -->
<!-- duplicate-checked: 1014 is reorder safety, 788 is reachability tooling; neither covers Step 4's dispatch size gate -->
# /cleanup-memory: add a small-corpus inline branch to Step 4

**Type:** skill-improvement
**Origin:** ai

## Goal
Give `skills/cleanup-memory/SKILL.md` Step 4 the same small-set inline branch `/cleanup-todos` Step 4 already has (`INLINE_MAX`), so a tiny memory corpus is deep-passed by the orchestrator instead of a mandatory single subagent dispatch.

## Context
`skills/cleanup-memory/SKILL.md` Step 4 says "dispatch exactly ONE subagent" for the deep pass with no size exemption. On 2026-10-08 an unattended wedding_dj run had 6 memory files, all already read in full in Step 1; dispatching a subagent would have re-read the same ~12KB for zero context saving (CLAUDE.md's context-weight axis). The run deep-passed inline instead, which is a deviation from the skill as written. `/cleanup-todos` solved the identical problem with `INLINE_MAX = 4` (todo 942), see `skills/cleanup-todos/SKILL.md` "Small-backlog branch".

## Approach
Add a "Small-corpus branch" paragraph to Step 4 of `skills/cleanup-memory/SKILL.md`, modelled on `/cleanup-todos`'s: at or under a constant (suggest `INLINE_MAX = 10` files, since memory files are short) the orchestrator does the same verification inline. Add the constant to a Notes section. Keep the "never one dispatch per memory" rule.

## Acceptance
- Step 4 names the inline threshold and states the inline pass checks the same things (paths/commands exist, `[[links]]` resolve, `suggested_drop`).
- A run over a <= threshold corpus following the skill literally dispatches no subagent.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved to build as written.
