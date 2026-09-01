<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The POSIX rename-session.sh has no per-session id cache, so the 459 fix is Windows-only

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `skills/close/rename-session.sh --get-id` the same per-`sessionId` cache that
`skills/close/rename-session.ps1 -GetId` gained in commit `231b555`, so a mid-session respawn
cannot hand two callers two different ids on Mac or Linux.

## Context

Filed 2026-09-01 by the `/mega-todos` builder that closed todo 843, as an out-of-scope finding it
was not allowed to fix (`rename-session.sh` was outside that dispatch's owned paths, and this
machine is Windows so the POSIX path could not be exercised at all).

Todo 459 fixed the instability by caching the resolved `<pid>-<procStart-ticks>` id in
`sessions/.getid-cache/<sessionId>.txt` on first successful resolution, keyed on
`CLAUDE_CODE_SESSION_ID`. Todo 843 then relied on that cache to make the two screenshot-directory
resolvers agree by construction rather than by coincidence.

`skills/screenshot/session-shot-dir.cjs` shells out to `rename-session.ps1 -GetId` on Windows but
to `rename-session.sh --get-id` on everything else. Only the `.ps1` half was changed, so the same
class of disagreement (two calls to the same script at different times, straddling a respawn,
landing on different session records) still reproduces on the POSIX path.

**UNVERIFIED on this machine:** the reproduction has not been observed on Mac or Linux, only
reasoned from the shape of the two scripts. Confirm against a real POSIX session before assuming
the failure mode is identical rather than merely analogous.

## Approach

1. Read `skills/close/rename-session.ps1` at `231b555` and find the cache read/write it added.
2. Mirror it in `skills/close/rename-session.sh`: same cache directory, same filename convention,
   same key (`CLAUDE_CODE_SESSION_ID`), so a session that somehow crosses platforms still resolves
   one id. Decide deliberately whether the two implementations should share a file format or stay
   independent, and say which in the commit message.
3. Prove it the way 459 did: two separate shell processes with the same fabricated
   `CLAUDE_CODE_SESSION_ID` but different underlying session records must print the same id.
4. Check whether `session-shot-dir.cjs` needs any change, or whether delegating to the fixed script
   is already enough as it was on Windows.

## Acceptance

- Two consecutive `rename-session.sh --get-id` calls in separate processes, same session id,
  different underlying records, print the identical id.
- `session-shot-dir.cjs` and `rename-session.sh --get-id` agree on POSIX, proven by running both.
- `python ci/run_all.py` exits 0.
