<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# rename-session.ps1 -Close kills a dead pid, so /close never closes the terminal

**Type:** task
**Origin:** ai

## Goal

Make `-Close` target the process actually hosting the session, and make `-GetId` stop returning a
pid that has already exited.

## Context

Observed in a zng-app session on 2026-08-25, twice in a row. `/respawn` and then `/close` both ran
their kill step and reported success, and the chat stayed alive both times, so Joe asked "should we
/close now?" after the close had already completed.

Measured from inside the still-live session:

```
pid 12728 alive       : False
my own pid            : 36972
CLAUDE_CODE_SESSION_ID: ea6bfebf-49ba-4161-9c4e-5db773291854
session id per script : 12728-134321233204549677
```

`rename-session.ps1 -Close` printed `Scheduled kill of claude pid 12728 in 800ms` and exited 0. Pid
12728 was already gone, most likely killed by the earlier `/respawn`. The live chat was running
under 36972, and four `claude` processes existed at the time.

So `-GetId` resolved the session to a **stale** pid rather than the current one. Two consequences:

1. `-Close` is a no-op that reports success. Every `/close` and `/respawn` leaves the terminal open
   while telling the dev it closed.
2. The screenshot directory id is derived from the same value, so `.for_bepy/screenshots/<id>/`
   keeps using `12728-...` for a session whose process is 36972. That defeats the per-session
   bucketing `/disk-doctor` relies on, and it is why the mapping needs fixing at the source rather
   than only in the `-Close` path.

Note the session id in the environment (`ea6bfebf-...`) is stable and correct throughout. It is the
session-id-to-pid resolution that goes stale, not the session id itself.

## Approach

1. Reproduce: start a session, note `$PID`, run `/respawn` or anything that triggers the kill, then
   in the surviving chat compare `-GetId`'s pid against the live `$PID`.
2. Find where the resolution is cached. If it is a file or a one-time lookup, re-resolve on every
   invocation instead, or verify the pid is alive and re-resolve when it is not.
3. Make `-Close` fail loudly rather than silently when the resolved pid does not exist, so a no-op
   never again reports success.
4. Check whether `/respawn`'s own teardown is what orphans the chat, since the successor session it
   spawned (`b580704c-8feb-42f5-9689-bf4f9e244790`) also never ran.

## Acceptance

- `-GetId` returns a pid that is alive, in a session that has survived a prior kill attempt.
- `-Close` either closes the terminal or reports a clear failure; it never prints a scheduled kill
  for a pid that does not exist.
