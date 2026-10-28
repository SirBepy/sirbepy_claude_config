<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Bulk ticket state moves bypass /ticket entirely, so nothing lands in its log

**Type:** skill-improvement
**Origin:** ai

## Goal

Make a multi-ticket state move ("move all these to Testing") route through `/ticket`'s Update
verb instead of hand-rolled REST, so the run gets the skill's target resolution, its ground
check, and its `log.md` entry.

## Context

2026-09-01, zng-app session. Joe asked to move 8 tickets to Testing after a push. The session
never invoked `/ticket` - it extracted `SHORTCUT_API_TOKEN` from `~/.claude/.env` and drove
`PUT /api/v3/stories/{id}` directly through inline Python, four separate times (the bulk move,
then three more calls diagnosing a failure and searching for a sibling ticket).

The skill already covers this shape. `skills/ticket/SKILL.md` has `## Update` with
`### 1. Resolve the targets` (plural) and `### 4. Write, one ticket at a time`, and
`skills/ticket/log.md` states its job is a "chronological log of every ticket created or updated
via `/ticket`". Seven state moves happened and none were logged.

Cost of the bypass, concretely: `sc-54902` 422'd with
`{"message":"Workflow state and Team are not compatible."}` because it lives in the **UI Design**
workflow (`500000012`), not ENG - Core Workflow (`500018252`). The session had to diagnose that
from scratch. `skills/ticket/shortcut.md` pins workflow defaults and would have been the natural
home for "check `workflow_id` before picking a `workflow_state_id`", but nothing wrote it there.

Enforcement asymmetry worth noting: ticket CREATION is guarded at the tool layer by
`hooks/shortcut-create-guard.py`. Ticket UPDATES have no equivalent, which is why a bulk move
can complete without the skill ever loading.

## Approach

1. Read `skills/ticket/SKILL.md` `## Update` and confirm whether a bulk/multi-target invocation
   is actually spelled out or only implied by "Resolve the targets". If implied, make it explicit:
   one worked example of "move sc-A, sc-B, sc-C to <state>".
2. Add a cross-workflow guard to that section: GET each story first, read `workflow_id`, and only
   then pick the state id. Name the 422 message verbatim so it is greppable.
3. Pin the UI Design workflow table in `skills/ticket/shortcut.md` alongside the existing ENG
   defaults (ids confirmed 2026-09-01: 500000016 To Do (Backlog), 500000013 Doing, 500000033
   Ready for Review, 500000017 Done, 500000034 Done - Ready for Dev, 500004887 Wont Do). Note it
   has no Testing equivalent.
4. Decide whether an update-side guard hook is worth it, mirroring
   `hooks/shortcut-create-guard.py`. Lean NO unless the bypass recurs - a guard that fires on
   every `PUT /stories/` would also catch legitimate diagnostic calls, and the create guard exists
   because a bad create is public and permanent while a bad state move is one more PUT to undo.
   Prefer step 1's explicit example first and re-check next time.

Rejected: filing this in zng-app's backlog. It is a global `~/.claude` skill gap, so it belongs
here per CLAUDE.md's "A todo belongs in the backlog of the repo it changes".

## Acceptance

- `skills/ticket/SKILL.md` `## Update` shows a bulk-move example and the read-`workflow_id`-first
  step.
- `skills/ticket/shortcut.md` carries the UI Design workflow ids.
- A future "move these N tickets to X" run produces a `log.md` entry.
- Must not regress: the create path and `hooks/shortcut-create-guard.py` are untouched.

## Notes

The Shortcut-side facts from this incident are already captured in zng-app's project memory
(`reference_shortcut_workflow_states.md`, updated 2026-09-01) so a future zng-app session is not
blocked on this todo landing. What is missing is only the skill-level routing and the pinned
defaults in `shortcut.md`.

Writing this file hit todo 851 / 859 again: `reserve-todo-id.ps1` created `861-.reserved`, then
`hooks/todo-duplicate-guard.py` rejected the write because that marker existed. Worked around by
deleting the marker first, contradicting ai-todos-format.md's "delete immediately after the write
succeeds". Third recurrence, so the guard and the reserve script still disagree.
- Completed in /mega-todos wave 1, commit 085c6da: /ticket Update now carries a bulk-move worked example and a workflow_id pre-check, and shortcut.md pins the UI Design workflow ids. No update-guard hook, per the todo's own lean.
