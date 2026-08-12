<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=5, reconfirm-count=2, content-hash=9e017250 -->
# /iterate-it: harden "report must be the turn's final message" beyond a written instruction

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it structurally harder for a session running `/iterate-it` to bundle follow-up tool calls into the same turn as the final convergence report, even when the dev already gave standing authorization to continue past it.

## Context

sc-54844 (2026-08-11, zng-app session): after a 7-round `/iterate-it` design pass converged, the report was printed correctly, but the same turn then continued straight into `Read`/`Edit` tool calls to begin implementation - a direct violation of `~/.claude/skills/iterate-it/SKILL.md`'s own instruction: "Do NOT call `AskUserQuestion` in the same turn as this report... The report is the deliverable; it must always render as the turn's final message." No `AskUserQuestion` was called (the specific harness bug the rule guards against), but the broader "must always render as the turn's final message" clause was still broken.

No visible harm resulted (the report rendered fully before the tool calls), but this is a written-instruction-only enforcement, and it was skipped under real-world pressure (a multi-step task with prior dev go-ahead). See that session's zng-app memory `feedback_report_must_be_final_message` for the behavioral-side record of this same incident.

## Approach

In `~/.claude/skills/iterate-it/SKILL.md`, strengthen the final-report section beyond prose. Options to consider (pick one, don't over-build):
- Add an explicit callout that the "final message" rule applies even when the dev has already pre-authorized next steps - name that exact failure mode so it's not just inferred from context.
- Consider whether the report template itself could end with an explicit "STOP - do not call any tool this turn, including implementation, even if authorized" line, making the instruction impossible to skim past.

## Acceptance

- Skill text makes clear the final-message rule holds regardless of standing authorization to continue.
- A future session following the skill literally has no ambiguity about whether it's safe to chain tool calls after the report in the same turn.

## Notes

Low severity, no user-visible harm this time - filed because the rule is easy to skip under real task pressure, and the skill is the right place to close that gap, not a one-off "be more careful" fix. Originally mis-filed in zng-app's own `.claude/todos/` and moved here per CLAUDE.md's global-tree rule.
- completed, commit 2d57b70
