# Clockify skill step 7 cites a meal-gap memory that is now archived

<!-- duplicate-checked: 1017 (done) folded the meal-gap rule into step 7, this is the stale pointer it left behind; 1008/1016/1092/101 are unrelated clockify steps -->

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/clockify-reconciliator/SKILL.md` step 7's meal-gap bullet stops pointing a run at a memory file that step 4a can no longer find.

## Context

Step 7's "Meal-gap check" bullet says the rule comes "from the `feedback_clockify_meal_breaks_and_unattended_work_next_day` memory file, read per step 4a". That file now sits only in `memory/archive/` for the zng-app project (both `~/.claude-personal/projects/c--Users-tecno-Desktop-Projects-zng-app/memory/archive/` and the `~/.claude/projects/...` mirror). Step 4a globs `feedback_clockify_*.md` in the memory dir root, so the archived file never loads. On the 2026-10-15 Zirtue run, Claude spent extra calls searching for the missing file before confirming the rule already lives inline in step 7. Done todo 1017 folded the meal-gap rule into step 7, which probably explains why the memory was archived afterward (UNVERIFIED: who archived it and why, check `/cleanup-memory` history).

The live memory `feedback_clockify_round_every_entry_to_5_minutes.md` still links `[[feedback_clockify_meal_breaks_and_unattended_work_next_day]]`. That is a harmless dangling wiki-link, and it is out of scope here.

## Approach

- Change step 7's bullet so it states the rule as owned by `SKILL.md` itself, for example "Meal-gap check (rule folded in from an archived memory by todo 1017)". Keep the 11:30-12:00 / 18:30-19:30 rule text exactly as written.
- Change nothing in step 4a's glob. Archived memories are meant to stay out of runs.

## Acceptance

- `grep -n "read per step 4a" skills/clockify-reconciliator/SKILL.md` no longer matches the meal-gap bullet.
- The meal-gap rule text in step 7 is unchanged.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1) in the clockify-reconciliator batch commit.
