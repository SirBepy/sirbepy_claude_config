<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=5, reconfirm-count=1, content-hash=b185bd0b -->
<!-- duplicate-checked -->
# `Agent` tool dispatches with no explicit `model` aren't caught by anything

**Type:** skill-improvement
**Origin:** ai

## Goal

CLAUDE.md's "Subagent model (cost control - MANDATORY)" section requires every subagent dispatch
to pass `model: 'sonnet'` explicitly, "never default-inherit the session model". Nothing currently
enforces this mechanically, so a violation is silent until someone notices the cost.

## Context

Filed 2026-08-26 from a `claude_usage_in_taskbar` session's `/close` retrospective. That session
dispatched an `Explore` subagent (via the `Agent` tool) for codebase investigation and did not
pass a `model` parameter at all, letting it default-inherit the session's own model - a direct,
if minor, violation of the MANDATORY rule. Caught only by this retrospective sweep, not at
dispatch time.

By contrast, `hooks/dispatch-preamble-guard.py` already enforces a DIFFERENT per-dispatch
requirement (the builder preamble's staging line / orphan-check text / screenshot-id line) via a
`PreToolUse` hook on the `Agent`/`Task` tool - so there's direct precedent for catching this kind
of thing mechanically rather than relying on the dispatching session to remember.

## Approach

1. Check whether a hook is the right shape here at all, per this repo's own hook doctrine (three
   guess-based hooks were killed in one day per `PLAN.md`'s "Hook doctrine" - `dispatch-preamble-
   guard.py`'s string-match approach is the precedent to follow, not a semantic one).
2. If pursued: extend `dispatch-preamble-guard.py` (or a sibling hook) to also check the `Agent`
   tool call's own `model` input parameter is present and non-empty, blocking with a clear message
   pointing at CLAUDE.md's subagent-model section - mirroring the existing preamble-marker checks'
   style (pure parameter presence check, not judging the value).
3. Decide the boundary case explicitly: a `fork` subagent_type always inherits the parent model by
   design (per the Agent tool's own description) - confirm the hook (if built) exempts `fork`
   dispatches rather than false-flagging them.

## Acceptance

- A subagent dispatch omitting `model` is blocked (or at minimum loudly flagged) before it runs,
  the same way a missing preamble marker already is.
- A `fork`-type dispatch (which legitimately has no `model` param need) is not blocked.

## Notes

Low urgency / low blast-radius (worst case is one subagent call costing more than it should), but
cheap to fix given the existing hook already does the mechanically-similar check on the same tool.
