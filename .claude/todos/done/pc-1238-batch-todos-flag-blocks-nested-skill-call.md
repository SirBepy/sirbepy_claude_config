<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no backlog file covers batch-todos' disable-model-invocation flag -->
# batch-todos' disable-model-invocation flag contradicts its callers and the skill-creator rule

**Type:** skill-improvement
**Origin:** ai

## Goal

`/batch-todos` is either callable as a nested step by `/auto-do-todos` and `/mega-todos`, or those
callers say plainly that they read its SKILL.md instead of invoking it, with no rule in between
contradicting either.

## Context

Found by the 2026-10-23 loop-todos per-commit review (slice A) of commit e0cc2a9 ("mark
batch-todos as an internal-only step"). It added `disable-model-invocation: true` to
`skills/batch-todos/SKILL.md:4`, but `skills/auto-do-todos/SKILL.md:100` ("3. `/batch-todos`,
unattended") and `skills/mega-todos/SKILL.md:60` run it as a step. `skills/bepy-skill-creator/SKILL.md:101`
says "if any other skill invokes this one via the Skill tool, do NOT add the field ... it would
break the chain", and `ci/check_skill_frontmatter.py:55-58` repeats that. The same commit's
`skills/batch-todos/SKILL.md:10` says "Trigger: `/batch-todos` only" while the description says
"not a standalone command", and `CLAUDE.md:102` still lists `/batch-todos` as an executor.

In practice this loop's runs read flagged SKILL.md files directly (the harness injects the text when
the slash name appears), so the chain has not visibly broken; UNVERIFIED whether a Skill-tool call
from inside `/auto-do-todos` is refused.

## Approach

Pick one: drop the flag (and fix line 10's trigger wording), or keep it and change both callers to
"read `skills/batch-todos/SKILL.md` and follow it", matching how they already handle other flagged
skills. Check which way commit e0cc2a9's author intended from its message and the cleanup-todos
edit in the same commit.

## Acceptance

- `batch-todos`' frontmatter, its trigger line, both callers and `CLAUDE.md:102` agree.
- `python ci/check_skill_frontmatter.py` reports nothing for batch-todos.

## Notes

- Kept the flag (e0cc2a9's stated intent: internal-only, same as auto-do-todos and mega-todos). batch-todos' trigger line now says callers read the file instead of a Skill-tool call, auto-do-todos Step 3 says the same, and CLAUDE.md's executor list names /auto-do-todos instead of /batch-todos (token-neutral, budget check PASS). check_skill_frontmatter.py reports nothing for batch-todos; its one FAIL is the uncommitted impeccable re-vendor.
