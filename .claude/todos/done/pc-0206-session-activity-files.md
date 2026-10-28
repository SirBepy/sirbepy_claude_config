# "Sessions" folder - concurrent AI sessions log what they're doing; needs design session with Joe

**Type:** skill-improvement

## Goal

NOT ready to implement - Joe explicitly wants this planned together with the AI in a dedicated
brainstorm before any design is fixed. This file only captures the raw idea (voiced 2026-07-15,
mid-session, "before I forget").

The idea: a folder where every running AI session writes a small file saying what it's currently
doing, so other concurrent sessions (and Joe) can see what's in flight.

## Context

Joe's raw sketch, near-verbatim:

- A folder inside "the .claude folder" - make sure it's ALWAYS gitignored.
  (Ambiguous which .claude: the project-local `.claude/` dir or the global `~/.claude` - Joe said
  "a folder inside of the .claude folder"; resolve in the design session. Note: this same session
  decided todo 03's plan/todos storage moves to project-local `.claude/todos/`, so a sibling like
  `.claude/sessions/` would rhyme with that.)
- Other AIs write what they're doing there (one file per session, presumably).
- `/close` deletes those files as part of its cleanup phases.
- Known hole: Joe sometimes closes a chat WITHOUT running `/close`, so stale session files will
  accumulate - "for those cases I guess we would have something that cleans it up regularly?"
  (his open question: some regular/stale-sweep cleanup mechanism, undecided).
- Explicitly not urgent ("i don't think it's anything that needs urgent care").

Related: [[05-multi-phase-plan-skill]] (in done/, implemented 2026-07-15 as the .claude/todos plan layer) - its claim-marker gap (two fresh agents double-picking the
same plan item) is the same underlying problem: concurrent sessions have no awareness of each
other. A sessions folder could be the shared substrate for both (claim = "session X is working on
todo NN" entry), so design them together or at least mutually aware.

Prior art worth checking in the design session: the server_supervisor already tracks long-lived
processes; `close/rename-session.ps1` already knows the session's own process; session transcripts
already persist titles. Don't reinvent what one of those could expose.

## Approach

None yet - deliberately. Open questions for the brainstorm with Joe:

1. Which `.claude` folder (project-local vs global), and how to guarantee gitignored everywhere.
2. File shape: one file per session? What's in it (task summary, cwd, PID, started-at, last-heartbeat)?
3. Write cadence: once at session start, or updated as the task changes?
4. Stale cleanup: who sweeps files from sessions that died without `/close` - a time-based sweep in
   `/close` itself (clean siblings older than N hours), a PID-liveness check, or a scheduled task?
5. Who reads it: just Joe, or should skills (autopilot, batch-todos claim markers) consume it?

## Acceptance

N/A - this is a design-discussion placeholder. Resolve by replacing this file with the real design
once Joe and the AI have brainstormed it, or deleting it if the idea is dropped.

## Notes

- Duplicate of 95 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
