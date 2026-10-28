<!-- Claim before executing: .claude/todos/.claims/988-pid-recycling-makes-reservation-self-healing-never-fire.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=4d7c863b -->
<!-- duplicate-checked -->
<!-- checked against 336 (id allocation races, the reason reserve-todo-id.ps1 exists) and 60 (the
     screenshot-folder id, which is where the pid-plus-start-time form was adopted). 336 is about
     two sessions grabbing the same id, which the reserve step fixes and which is not this. 60 fixed
     the same PID-recycling hazard in a DIFFERENT artifact and its fix is the model for this one,
     but it never touched reservation markers. Neither covers this. -->
# A recycled PID keeps an abandoned reservation alive forever

**Type:** task
**Origin:** ai

## Goal

Make `reserve-todo-id.ps1`'s documented self-healing actually fire, so an abandoned reservation
cannot survive indefinitely.

## Context

Found 2026-09-12 during a `/close` sweep, and reproduced rather than inferred.

`skills/close/reserve-todo-id.ps1`'s own header promises: "An abandoned reservation (crash between
reserve and write) self-heals: the next call to this script prunes it once its mtime exceeds 4
hours, no separate cleanup skill required."

It does not. `Remove-StaleReservations` requires BOTH conditions:

```
if ($ageHours -gt 4 -and -not $pidAlive) { Remove-Item ... }
```

and `$pidAlive` comes from `Get-Process -Id <pid>` against a bare PID read out of the marker file.
Windows recycles PIDs. Once an unrelated process inherits that number, `$pidAlive` is true forever
and the marker is immortal no matter how old it gets.

**The live reproduction, still on disk at the time of writing, deliberately left there as evidence:**

- `.claude/todos/937-.reserved`, mtime 2026-09-05, seven days old.
- Its content records `pid: 2184` and `session: 68ef55bb-c2fc-4f12-bdfc-573586293dbb`.
- No `937-*.md` was ever written, in the backlog or in `done/`, so the reservation was abandoned.
- It survived five separate `reserve-todo-id.ps1` calls in one session on 2026-09-12.
- `Get-Process -Id 2184` today returns a live **`svchost`**. That is the whole bug: an unrelated
  Windows service now holds the number, so the dead session's marker reads as alive.

This repo already solved this exact hazard once, elsewhere. `/close` Phase 0 uses
`<pid>-<procStart-ticks>` for the screenshot subfolder and states why in its own words: "Windows
recycles PIDs, so a bare PID can collide with a dead session that left files behind; PID plus start
time cannot." The reservation marker predates or missed that lesson.

The same two-signal rule is written into `close/ai-todos-format.md` for CLAIMS, where it is far less
dangerous: a claim is held by a live session that releases it, so the PID is usually genuinely
current. A reservation marker is written once and then abandoned by definition in the failure case,
which is precisely when the PID is most likely to have been recycled.

Impact is small but unbounded: abandoned markers accumulate forever, each one burning an id the
contract says may never be reused, and the promise of no-separate-cleanup-needed is false.

## Approach

1. Reproduce first, from the artifact above if it is still present, or by writing a marker whose
   recorded PID belongs to some other live process and confirming it survives a prune pass.
2. The marker content already carries what is needed to disambiguate: `session:` (a session id) and
   `reserved:` (an ISO timestamp). Decide which to key on and say why:
   - Match `session:` against `~/.claude/sessions/*.json`, the same lookup `rename-session.ps1
     -GetId` already performs. Most precise, and consistent with how this repo resolves identity
     elsewhere.
   - Or record the process start time alongside the PID and compare both, the `<pid>-<start-ticks>`
     shape `/close` Phase 0 already settled on.
   Prefer reusing an existing mechanism over inventing a third identity scheme.
3. Handle the markers already on disk, which carry only a bare PID and cannot be repaired
   retroactively. An age-only fallback above some larger threshold is the obvious answer; pick the
   threshold deliberately and state it, rather than leaving old markers permanently unreachable.
4. Check whether the same bare-PID liveness test appears anywhere else that is written-once and
   abandoned. `close/ai-todos-format.md`'s claims rule uses the same two signals; claims are
   released on completion so they are much less exposed, but confirm rather than assume.

## Acceptance

- An abandoned reservation whose recorded PID has been recycled IS pruned, proven against a marker
  built for that case, not against a marker whose PID is simply absent.
- A genuinely live session's reservation is still NEVER pruned out from under it. This is the
  regression that matters: pruning a live reservation reintroduces the id race the script exists to
  prevent (todo 336, three collisions in a row).
- Markers already on disk with only a bare PID eventually clear.
- `python ci/run_all.py` passes.

## Notes

- `.claude/todos/937-.reserved` is left in place on purpose as the reproduction. Delete it as part of
  the fix, not before: removing it first destroys the only live evidence.
- Do not fix this by dropping the PID check and going age-only. The PID half is what stops a live
  session losing its reservation mid-write; weakening it trades a cosmetic leak for a real race.
- Completed by /loop-todos cycle 1 (2026-10-05), lane C, test-first via tools/test_close_*.py (RED against HEAD copies, then GREEN).
