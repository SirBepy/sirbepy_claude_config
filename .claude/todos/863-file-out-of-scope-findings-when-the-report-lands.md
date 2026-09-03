<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=1, content-hash=7c1e4b93 -->
# 863 - Out-of-scope findings piled up unfiled across a whole fan-out

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-08-27

## Goal

Close the gap between a subagent reporting an out-of-scope finding and that finding becoming a todo.

## Context

The delegation doctrine (`~/.claude/refs/delegation-doctrine.md`, "Out-of-scope findings") is deliberate about this: a subagent must NEVER write into `.claude/todos/` itself, because only the orchestrator can allocate an id without racing a concurrent session. Every dispatch instead asks for an "Out-of-scope findings" section, and **the orchestrator files each one as a proper todo after the fan-out returns.**

On 2026-08-27, roughly fifteen dispatches ran across one session. Several returned real out-of-scope findings. **None were filed as todos until `/close`.** They survived only because they were carried in the orchestrator's own summaries and eventually swept into a handoff todo's Notes - which is luck, not a mechanism. In a session that ended abruptly, or one where context compacted, they would have been lost silently.

The global rule this breaks is stricter still: "Deferring work mid-task means writing it to `.claude/todos/` at the moment of deferring, not at the end." Its own honest caveat is that nothing enforces it, and `/close` and `/code-check` only sweep after the fact. This session is a clean demonstration of that caveat being real.

The findings that eventually got filed are todos 03, 04, 05 and 06 in the zng-app backlog.

Aggravating factor specific to that session: **seven-plus subagents died without ever reporting.** Findings held only in an unreported agent's context are gone entirely. That raises the cost of batching filings to the end of a run, because the run may not have an end.

## Approach

Options, roughly in increasing cost:

1. Add an explicit step to the doctrine's fan-out reconciliation: after each dispatch returns, file its out-of-scope findings **before** dispatching the next round, not at the end of the session.
2. Make it part of the orchestrator's per-report hygiene, alongside "keep only the durable outcome in main context" - the discard step is exactly where a finding gets dropped today.
3. A `Stop`-hook style check, on the model of the existing dispatch-preamble guard: if the session's transcript contains an "Out-of-scope findings" section with content and no todo was written since, warn. Mechanical, but only catches it at the end - which is the same failure this todo is about.

Prefer 1 or 2. A rule that fires at the end of the run has the same weakness as the one it replaces.

## Verify

Not a code change - no test. Success is a later multi-dispatch session where findings appear in the backlog with ids allocated during the run rather than after it.

## Notes

- Relocated from `07` in `c:\Users\tecno\Desktop\Projects\zng-app` via /cleanup-todos 2026-09-01: the todo's own Notes said it belongs to the global `~/.claude` tree because its subject is `refs/delegation-doctrine.md`, and it was only filed in zng-app because that is where the incident happened.
- Related: global todo 817 (a progress-status skill) covers the adjacent problem of silent agent deaths being invisible.
- Distinct from todo 404, which covers the opposite side of the same doctrine section - a subagent writing INTO the backlog, rather than the orchestrator failing to file after the fan-out returns.
