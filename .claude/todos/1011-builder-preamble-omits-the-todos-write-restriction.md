<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=0a678d1a -->
<!-- duplicate-checked: 1006 is about pasting the preamble block at all, a compliance gap. This is about the block's CONTENT being silent on a restriction that exists, so a fully compliant dispatch still fails. Different failure, different fix. -->
# 1011 - builder-preamble.md never says a dispatched agent cannot write to .claude/todos/

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

Record in `refs/builder-preamble.md` that `hooks/agent-todo-write-guard.py` rejects any
Edit/Write from a dispatched agent targeting `.claude/todos/`, so an orchestrator does not spend a
whole dispatch discovering it.

## Context

2026-09-24, zng-app. A sonnet subagent was dispatched to append a dated note to ten backlog todos.
The dispatch was fully preamble-compliant. Every one of its ten Edit calls was rejected pre-write
by `agent-todo-write-guard.py`, which permits `.claude/todos/` writes only from the orchestrator.

Cost was ~91k subagent tokens for zero writes. It ended well only because the agent returned the
drafted text in its report instead of failing silently, so the orchestrator could apply the ten
appends itself. A less careful agent would have reported ten errors and nothing usable.

The restriction is correct and should stay. The problem is purely that nothing an orchestrator
reads before dispatching mentions it. `refs/builder-preamble.md` is the natural home: it is already
the place that documents what a dispatch may and may not do, and it already enumerates the three
literal strings `dispatch-preamble-guard.py` checks for.

## Approach

1. Read `hooks/agent-todo-write-guard.py` first and describe what it actually blocks, rather than
   generalising from the one observed case. Confirm the exact path scope (is it `.claude/todos/`
   only, or does it cover `.claims/` and `done/` too) and whether Write is blocked as well as Edit.
2. Add a short paragraph to `refs/builder-preamble.md` stating the restriction and the correct
   pattern: a dispatch that needs backlog changes returns the intended content in its report, and
   the orchestrator applies it.
3. Check whether `skills/create-todo/SKILL.md` and `skills/close/ai-todos-format.md` should carry
   the same one-liner, since both are read by orchestrators planning todo writes.
4. Do not add it as a fourth literal check in `dispatch-preamble-guard.py`. That file's own
   comments argue against growing the check list, and this is a restriction on the agent's actions
   rather than on the prompt's text.

## Acceptance

- `refs/builder-preamble.md` states the restriction, scoped to what the hook actually enforces as
  read from its source, not inferred.
- The return-it-in-the-report pattern is named explicitly as the workaround.
- `grep -rn "agent-todo-write-guard" refs/ skills/` returns the new mention.
