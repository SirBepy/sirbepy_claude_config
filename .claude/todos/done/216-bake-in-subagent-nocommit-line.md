<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Subagent dispatch templates should bake in the mandatory no-commit line, not rely on the orchestrator remembering it

**Type:** skill-improvement

## Goal

Prevent the mandatory "Stage your changes but do NOT commit. The main agent will run `/commit`
after your report-back." line (global CLAUDE.md, Git Commits section) from being silently dropped
when a skill's own literal subagent-dispatch prompt template doesn't itself include it.

## Context

During the 2026-07-18 `/cleanup-todos` build session, all 7 `/iterate-it` round dispatches
(3 Explore + 3 Polish + 1 extra manual round) omitted this mandatory line.
`~/.claude/skills/iterate-it/SKILL.md`'s own "Subagent prompt template" section doesn't include
it, and the orchestrating agent didn't add it manually either, 7 times in a row across the same
session. No actual harm resulted this time (all 7 subagents were read-only rating tasks with no
file writes), but the rule is meant to be unconditional per dispatch, and relying on the
orchestrator to recall a rule that lives only in CLAUDE.md - not in the skill's own template -
clearly failed under repetition within a single session.

## Approach

Add the line directly into `iterate-it`'s "Subagent prompt template" section so it ships with
every round automatically. While there, check other skills that define their own literal
Agent-dispatch templates for the same gap: `~/.claude/skills/batch-todos/SKILL.md` step 5's
premise-check subagent dispatch, and `~/.claude/skills/rate-it/SKILL.md`'s panel-mode dispatch
template. Baking the line into each template removes the dependency on the orchestrator recalling
a global rule mid-loop, especially across many sequential rounds.

## Acceptance

- Every skill file that defines its own literal subagent dispatch prompt template includes this
  line verbatim in the template text itself, not just as a reminder living elsewhere.
- Must not regress: subagent prompts stay otherwise unchanged (angle briefs, hard constraints,
  output format) - this is a pure addition, not a rewrite of the templates.

## Notes

- Dropped via /cleanup-todos 2026-08-11: prevents zero live harm - all three templates dispatch read-only or opinion-only subagents. Confirmed by dev 2026-08-11.
