<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; no live or done todo mentions HARD_STOP_AT against the loop's 35% respawn line -->
# /loop-todos keeps a cycle in-chat at 35%+ remaining, but /auto-do-todos stops taking todos at 40% used

**Type:** skill-improvement
**Origin:** ai

## Goal
The two thresholds agree, so a loop never starts a cycle that its own inner skill refuses to work.

## Context
`skills/loop-todos/SKILL.md` Phase 4: "At or above 35% remaining, start the next cycle in this chat."
`skills/auto-do-todos/SKILL.md` Step 6: ">= 40% used (HARD_STOP_AT): stop taking new todos
immediately". Between 40% and 65% used, Phase 4 says continue in-chat while Step 6 says take nothing,
so the next cycle completes zero todos and Phase 3's "zero todos" stop fires, ending the loop early.
Hit 2026-10-08, loop-todos cycle 1 in `~/.claude` on a 1M window: cycle 1 ended at 48% used (52%
remaining). The run respawned anyway rather than start a guaranteed-empty cycle, which deviated from
Phase 4's literal text.

## Approach
Make Phase 4's respawn line match Step 6: respawn whenever ctx used is at or above HARD_STOP_AT
(40%), i.e. below 60% remaining, and name Step 6 as the source so the two cannot drift again.

## Acceptance
- loop-todos Phase 4 and auto-do-todos Step 6 name the same boundary, one pointing at the other.

## Notes

- loop-todos Phase 4 now respawns at /auto-do-todos Step 6's HARD_STOP_AT (40% used) and points at Step 6 instead of copying the number.
