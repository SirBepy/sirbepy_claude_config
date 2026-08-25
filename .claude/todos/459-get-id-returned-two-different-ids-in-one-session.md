<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
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
