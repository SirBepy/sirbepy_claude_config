<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Fix rate-it panel.md's hardcoded SKILL.md path (points at ~/.claude, skill lives in ~/.claude-personal)

**Type:** skill-improvement

## Goal

The dispatch prompt template in the rate-it panel doc points subagents at the skill's real
location.

## Context

`~/.claude-personal/skills/rate-it/panel.md` (Dispatch section) tells panel subagents to
"Read the skill file at `C:\Users\tecno\.claude\skills\rate-it\SKILL.md`" - but the skill
actually lives at `C:\Users\tecno\.claude-personal\skills\rate-it\SKILL.md`. Noticed
2026-07-22 in a Fibo session: the orchestrator had to silently correct the path when
dispatching a 3-rater panel; a less attentive run would send raters to a nonexistent file and
they'd rate without the rubric.

## Approach

In `~/.claude-personal/skills/rate-it/panel.md`, replace the hardcoded path with the
`.claude-personal` one - or better, instruct the main agent to substitute the skill's actual
base directory (it's given as "Base directory for this skill" at invocation), so the template
survives future moves. Grep the rest of `~/.claude-personal/skills/` for other stale
`\.claude\skills\` self-references while in there.

## Acceptance

- panel.md's dispatch template resolves to a real file on this machine.
- No other skill under ~/.claude-personal/skills/ references itself via the old ~/.claude path.

## Notes

- Dropped via /cleanup-todos 2026-08-11: premise false - .claude-personal\skills is a junction to .claude\skills, so the path always resolved. Confirmed by dev 2026-08-11.
