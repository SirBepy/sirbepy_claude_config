<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hits (1193 close_session, 105 commit-skill step1, 208 chained-shell, 213/269 em-dash) are each a different rule with no mechanical enforcement, sharing only generic vocabulary ("rule"/"mechanical"/"enforcement"/"gets skipped"). This one is specifically about the .claude/todos/ claim-before-executing rule, not covered by any of them. -->
# The non-negotiable todo-claim rule has no mechanical enforcement and gets skipped routinely

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether the `.claude/todos/` claim rule (CLAUDE.md: "before EXECUTING any todo, claim it
via `.claude/todos/.claims/<id>.claim`... non-negotiable") needs a mechanical gate, given it was
skipped 3 times in a row in one solo session with no enforcement catching it.

## Context

Observed 2026-10-19 in a `windows_taskbar_widgets` session: todos 81, 82, and 83 were each executed
and completed (via `complete-todo.ps1`) without ever being claimed first. `complete-todo.ps1`
printed the same warning each time: `"todo N is being completed with no claim on record - either it
was executed without claiming, or the claim was released early... Not blocking."` Three warnings in
one session on a rule CLAUDE.md calls non-negotiable is a real pattern, not a one-off slip - and
`close/ai-todos-format.md`'s claim contract is itself honest that nothing enforces it mid-task,
only `complete-todo.ps1`'s own after-the-fact warning catches a miss, and only at completion time.

No peer collision actually happened this session (`list_peers` was empty throughout), so the
practical cost here was zero - but the rule exists for the shared-checkout case, and a session that
skips it reflexively when solo is the same session that will skip it reflexively when it matters.

## Approach

Options, not a prescribed fix - this needs a judgment call on enforcement cost vs. benefit:

1. A `PreToolUse` hook on the Edit/Write tools that checks whether the file being edited is one
   named in an open `.claude/todos/<id>-*.md` currently being worked, and blocks if no matching
   `.claims/<id>.claim` exists - likely too strict/noisy for incidental edits unrelated to a todo.
   mirroring `hooks/agent-todo-write-guard.py`'s existing pattern.
2. A lighter touch: `complete-todo.ps1`'s existing warning is already the backstop: leave it as
   documentation-only, since the realistic cost (todo 890's worth-rubric incident aside) is low for
   a solo session and the claim mechanism exists specifically for concurrent sessions.
3. Somewhere between: a reminder surfaced earlier, e.g. when a todo file is first Read/Edited in a
   turn rather than only at completion time, so the gap is visible before three todos pass through
   it unclaimed rather than after.

## Acceptance

A decision recorded here (even "leave as-is, here's why") with the tradeoff actually weighed -
this todo's job is to force that one deliberate pass, not necessarily to ship a hook.

## Notes

- Archived by the cleanup-todos pass 2026-10-23: worth 4. Decision recorded: claim enforcement stays at complete-todo.ps1's existing warning (line 252); solo cost was zero and a hook would be noisy on incidental edits.
