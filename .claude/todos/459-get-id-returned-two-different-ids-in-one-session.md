<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=3, content-hash=a49b179b -->
<!-- duplicate-checked -->
# rename-session.ps1 -GetId returned two different ids inside one session

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `-GetId` return the same value for the whole life of a session, or make `/close` stop relying
on it as a proof of screenshot-folder ownership. Right now it silently does neither.

## Context

zng-app session `86af7f10-2a0d-41b6-bb41-af1f812047a1`, 2026-08-20. `-GetId` was called twice in
the same session, hours apart, with no restart in between:

- Early, per CLAUDE.md's UI rule, to pick the screenshot folder: **`46636-134317129989413272`**.
  Five PNGs were written to `.for_bepy/screenshots/46636-134317129989413272/` and are still there.
- At `/close` Phase 0: **`42292-134317285759421211`**. That folder does not exist.

Both the PID and the start-ticks differ, so this is not a PID recycle - it resolved to a different
process entirely. Phase 3 step 3 counts files under "this session's own subfolder (the Phase 0 id)",
which would have reported 0 screenshots for a session that captured 5.

This matters more than a wrong count. `close/ai-todos-format.md`'s sibling comment in
`e2e/lib/config.js` and `close/SKILL.md` Phase 0 both state the guarantee explicitly:

> `/close` proves ownership of a screenshot folder by subfolder name, never by mtime, because a
> concurrent session's files can be newer OR older. Windows recycles pids, so the key is pid plus
> process start ticks.

If the id is not stable within a session, the ownership proof does not hold, and `/disk-doctor`
ages out folders keyed on it.

Note todo 60 already replaced a process-tree walk with a `$env:CLAUDE_CODE_SESSION_ID` match against
`~/.claude/sessions/*.json` **because the walk resolved to two different PIDs in one session**. That
is the same symptom recurring after the documented fix, so the fix is either incomplete or the
matching path is falling back to the walk under some condition.

Relevant context: this machine runs several concurrent Conductor sessions in the same repo, and this
session had two live peers, so `sessions/*.json` held multiple entries with the same `cwd`.

## Recurrence 2026-08-27, with a identifiable cause this time

zng-app session `56dd6326-c91a-49fd-8857-74917d59ccaf`. Same signature, and here the mechanism is
not ambiguous: the session was started in the CLI on 2026-08-26, then **resumed the next day by the
Conductor app** (`entrypoint` flips from `cli` to `sdk-cli` in the transcript, ~13 hours later).
The host respawns the process, so the pid and start-ticks change by construction.

- Screenshots were written on 08-26 to `.for_bepy/screenshots/48360-639233675804062390/` (2 PNGs,
  still there).
- `/close` Phase 0 on 08-27 resolved **`14432-134322965285327444`**. That folder does not exist.

So the id is not merely racy under concurrency - it is **guaranteed** to change for any session the
host respawns, which is the normal lifecycle in Conductor, not an edge case. A per-session cached
id (Approach step 3) keyed on `sessionId` rather than pid would survive this; a pid-derived one
cannot. Note the two ticks values also use different epochs/widths (`134322965285327444` vs
`639233675804062390`), worth checking as a second, separate inconsistency in how the suffix is
produced.

## Recurrence 2026-08-31 - single uninterrupted session, no resume, no peers

pomalo session `93dc9a67-8180-48e2-bda0-a84afa66afa2`. Tightens the 08-27 finding: this session
was never resumed and `list_peers` returned empty, so neither concurrency nor a cross-day resume
explains it.

- Early call, to pick the screenshot folder: **`14776-134326453636888116`**. 29 PNGs plus two
  `.mp4` screen recordings were written there and are still there.
- `/close` Phase 0, same conversation: **`17048-134326571109686356`**. That folder does not exist.

So Approach step 1's hypothesis (a newest-`startedAt` fallback picking a peer) is NOT the cause,
at least not the only one - there was no peer to pick. Plain per-turn respawn by the Conductor
host is sufficient on its own, which makes this reproduce in ordinary single-session use rather
than only under concurrency or resume. That strengthens the case for Approach step 3 (cache the
id on first call, keyed on `sessionId`) over any refinement of the pid lookup.

## Approach

1. Read `~/.claude/skills/close/rename-session.ps1` and find every path that can produce an id.
   Confirm whether a fallback (newest-`startedAt`-for-this-cwd, or the old process-tree walk) can
   fire when the `CLAUDE_CODE_SESSION_ID` lookup misses. With three sessions sharing a `cwd`, a
   newest-`startedAt` fallback would return whichever peer started last - which fits the observed
   result exactly.
2. If `$env:CLAUDE_CODE_SESSION_ID` was unset or unmatched at close time, make that a hard error
   rather than a silent fallback - a wrong id is worse than no id here, because it reads as a real
   answer.
3. Consider caching the resolved id per session on first call (a file under `~/.claude/sessions/`)
   so every later call in the same session returns the same value by construction.
4. Whatever the fix, `/close` Phase 3 step 3 should notice the mismatch instead of reporting 0:
   if the Phase 0 id's folder is missing but this session is known to have captured screenshots,
   say so rather than printing a confident zero.

## Acceptance

- Two `-GetId` calls hours apart in one session return the same string, with two other Conductor
  sessions live in the same repo.
- A session that cannot resolve its own id fails loudly instead of returning another session's.
- `/close` Phase 4's screenshot count matches what the session actually wrote.
- Regression case: the exact shape above - three sessions sharing one `cwd`, `-GetId` early and at
  close.

## Progress 2026-09-01 - advanced, NOT finished

`/mega-todos` batch 1, commit `231b555`. `-GetId` now caches its resolved `<pid>-<procStart-ticks>`
id in `sessions/.getid-cache/<sessionId>.txt` on first successful resolution, keyed on
`CLAUDE_CODE_SESSION_ID`, and every later call in the same session returns that value verbatim
instead of re-resolving. Verified with two separate PowerShell processes sharing one fabricated
session id but different underlying records (the respawn shape): both printed the identical id.

Still open, which is why this stays in the backlog:

- Acceptance item 3 (`/close` Phase 4's screenshot count noticing a Phase-0-id mismatch instead of
  reporting a confident zero). That logic lives in `skills/close/SKILL.md`, outside the builder's
  owned paths, so it was not touched.
- The literal three-sessions-sharing-one-cwd regression shape was never reproduced with three live
  peer records. The fix is keyed purely on `sessionId` and so is peer-count-agnostic, but that is
  reasoning, not a test.
- The secondary finding from 2026-08-31 (the two observed ticks values use different epochs and
  widths, `134322965285327444` against `639233675804062390`) is still uninvestigated.

Only the `.ps1` half was fixed. The POSIX `rename-session.sh` has no equivalent cache; filed as
todo 867.
