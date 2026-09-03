<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# 865 - Nothing stops a session tearing down infra other live sessions are using

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-01

## Goal

Make tearing down a supervised server check whether other sessions are live first, the same way
committing already checks.

## Context

2026-09-01, five sessions live in one zng-app checkout. One session finished an e2e run, posted
"browser/fixture slot is FREE" to the peer channel, then a few minutes later stopped both
`zng-app:node-2` (the release-bundle server on :42047) and `zng-api:start-clean` (core on :3009)
as part of wrapping up. Another session then spent real time debugging "Error attempting to
signin" as a defect in its own in-flight change before a third session asked about it and the
cause surfaced.

Two things made it expensive:

1. **"Slot is free" and "the backend is still up" are different claims**, and announcing the first
   while doing the second is actively misleading. The announcement made it *less* likely anyone
   would suspect infra.
2. **The failure does not look like an outage from inside the app.** After the process dies,
   `Test-NetConnection -Port 3009` still reports the port **open** while `curl` returns **000**.
   The request never leaves Chrome and the UI shows a generic error, so a probe scores it as app
   code.

The asymmetry is the point: `list_peers` before `git commit` is a hard rule with a documented
incident behind it, because a commit can sweep up someone else's work. Stopping shared infra has
the same blast radius - it breaks every other session's runtime work - and has no rule at all.

Distinct from todo 797 (positional git refs in shared checkouts): same "concurrent sessions share
one resource" family, different resource and different fix. 797 guards the git index, this guards
running processes. Neither subsumes the other.

## Approach

Options, cheapest first:

1. A line in `supervised-run`'s SKILL.md: before `sv.ps1 stop` on any entry, call `list_peers`;
   if any peer is live in the same repo, post what is being stopped and why, rather than assuming
   the entry belongs to you. Cheap, no enforcement.
2. The same check in `/close`, since that is where "wrapping up" turns into stopping things.
   `/close` currently says nothing about supervised servers at all.
3. A `sv.ps1 stop` guard that refuses without `-Force` when peers are live. Real enforcement, but
   it needs `sv.ps1` to know about the Conductor peer list, which it currently does not.

Prefer 1 + 2. The default should probably invert too: when peers are live, **leave supervised
servers running** and say so. They are shared infrastructure, not this session's orphans, and
process hygiene does not require killing them.

## Verify

Not a code change with a test. Success is a later multi-session day where a session says "leaving
:3009 up, peers are live" instead of silently stopping it.

## Notes

- Worth folding the false-liveness detail into whatever doc gets the rule: port-open is not a
  liveness check, only an actual HTTP response is.
- Filed from the zng-app session that caused the incident, into this repo's backlog because the
  fix is to `supervised-run` and `/close`, both global.
- Completed in /mega-todos wave 1, commit 81f7815: /supervised-run checks list_peers before stopping a server and /close checks for supervised servers, both defaulting to leaving shared infra up when peers are live.
