<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# rename-session.ps1 -GetId answers confidently with the wrong id when a subagent calls it

**Type:** task
**Origin:** ai

## Goal

Make `skills/close/rename-session.ps1 -GetId` refuse or flag a call it cannot answer correctly,
instead of silently returning a plausible-looking wrong id to a subagent.

## Context

Measured 2026-08-15 during an `/auto-do-todos` run in this repo.

- A builder subagent ran `pwsh -File skills/close/rename-session.ps1 -GetId` and got
  `36492-134312608129305037`.
- The orchestrating session ran the identical command later in the SAME session and got
  `35944-134313459928168875`. Both halves differ, pid and start-ticks.
- The orchestrator's value is stable: two consecutive calls returned it identically, with
  `$env:CLAUDE_CODE_SESSION_ID` set to `0067935c-6b8f-48a7-9de2-8b0f62d9f6a6`.

So this is process-scoped divergence, not nondeterminism.

UNVERIFIED as to mechanism: the likely cause is that a subagent process does not inherit
`CLAUDE_CODE_SESSION_ID`, so the script falls through to the process-tree walk its own comments at
lines 8-13 already call "Fallback only, best-effort/unstable (todo 60)". Confirm that before
fixing, by printing the env var from inside a dispatch.

Why it matters: a wrong id creates a screenshot subfolder `/close` can never prove ownership of.
That is the exact failure class todo 339 fixed at the documentation level (three orphaned
subfolders plus 49 loose files in zng-biller alone), and the fix there was to make `-GetId` the
single source of truth. This todo closes the remaining hole, which is that `-GetId` itself will
answer wrongly rather than refuse.

`refs/delegation-doctrine.md` already mandates that the orchestrator resolve the id ONCE and pass
it into every dispatch, never re-deriving per dispatch. That rule is correct and is what kept this
run safe. This is defence in depth for when someone does not follow it.

## Approach

Detect the unreliable path rather than papering over it.

1. Confirm the mechanism first: print `$env:CLAUDE_CODE_SESSION_ID` from inside a subagent
   dispatch. If it is empty there, the fallback path is the cause and the rest follows.
2. When the sessionId lookup fails and the script is about to use the process-tree fallback, do NOT
   return a bare id as if it were authoritative. Options: exit non-zero with a message naming the
   doctrine rule (the orchestrator resolves this and passes it in), or return the id prefixed with
   a clear unreliable marker that a caller cannot mistake for a folder name.
3. Keep `-Close` and the normal orchestrator path working exactly as they do now. Only the
   degraded `-GetId` path changes.

Do not delete the fallback outright without checking what else calls it. `skills/close/SKILL.md`
Phase 0, `skills/screenshot/session-shot-dir.cjs` and `e2e-helpers.js` all resolve through this
chain.

## Acceptance

- A subagent calling `-GetId` either fails loudly or returns something no caller can mistake for a
  valid folder name.
- The orchestrator path still returns the same stable id it does today, proven by two consecutive
  calls matching.
- `/close` Phase 0 and the screenshot helpers still resolve correctly.

## Notes

- Done 2026-08-16, commit f95bc94. The suspected mechanism was REFUTED by measurement: a foreground subagent does inherit CLAUDE_CODE_SESSION_ID (measured non-empty) and -GetId returned the orchestrator's exact id, because a foreground dispatch shares the orchestrator's OS process. The real trigger is a genuinely separate process, most plausibly a background dispatch. Fix shipped for the narrower hole the todo targeted: Resolve-SessionRecord now tags how it resolved, and -GetId exits 1 citing the doctrine's resolve-once rule rather than trusting the pid-walk fallback. Exit-nonzero was chosen over a marker string because no caller validates the id format, so a marker would just become a bogus folder name. session-shot-dir.cjs and e2e-helpers.js now fail loudly instead of crashing raw. -Close and -Name untouched.
