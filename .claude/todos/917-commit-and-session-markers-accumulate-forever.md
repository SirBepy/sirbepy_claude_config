<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hit, done/365, is about marker writes landing on MALFORMED PATHS and leaving a handful of strays; that was fixed. This one is about correctly-formed markers accumulating by VOLUME (266 of them) because nothing prunes them. Different cause, different fix. -->
# hooks/ accumulates commit markers and session markers forever

**Type:** task
**Origin:** ai

## Goal

`hooks/.commit-marker-*` and `hooks/.session-markers/` stop growing without bound, so the guard's
own scratch state does not outlive the sessions that wrote it by weeks.

## Context

Measured 2026-09-04 during a `/mega-todos` run, in `C:\Users\tecno\.claude`:

- `ls hooks/.commit-marker-* | wc -l` returns **266**
- `ls hooks/.session-markers/ | wc -l` returns **254**
- the oldest entries are dated **2026-08-16** and **2026-08-17**, roughly three weeks back

The commit-guard's documented behaviour is that it consumes only the oldest marker, which is what
lets concurrent agents avoid stealing each other's. That consumption is evidently not keeping pace
with the write rate: a wide parallel run writes one marker per builder commit, and this run alone
added a dozen. Nothing else prunes either directory.

Both paths are deliberately excluded from every skill's cleanup rules (`refs/builder-preamble.md`
names them as never-touch, because a live session's commit depends on `.session-markers/`), so no
agent will ever remove them as a side effect. That exclusion is correct and is not what should
change.

A `/mega-todos` builder surfaced the `.commit-marker-*` half on 2026-09-04 and judged it not worth
filing, on the reasoning that the guard cleans up after itself. The counts above are the evidence
that it does not.

## Approach

1. Read `hooks/commit-guard.py` and `hooks/write-session-marker.ps1` and establish, with receipts,
   which marker each one consumes and under exactly what condition. Do not assume the docstring is
   accurate; the counts say something is not firing.
2. Decide where pruning belongs. The obvious candidates, in rough order of preference:
   - the guard prunes any marker older than its own validity window (2 minutes) whenever it runs,
     which makes the cleanup self-maintaining and needs no new trigger;
   - a `SessionEnd` hook removes that session's own marker;
   - `/disk-doctor` or `/close` sweeps them, which is worse, since it makes cleanup depend on a
     skill nobody runs on a schedule.
3. Whatever is chosen must never delete a marker a live session still depends on. A session marker
   is keyed to a session id, so liveness is checkable; prove the check rather than reasoning about
   it.

## Acceptance

- Both directories have a bounded steady-state size, and the bound is stated in the code that
  enforces it.
- A concurrent-agent scenario is covered by a test: two markers written close together, the guard
  consuming one, and the other still present and valid for its own session.
- No live session's marker can be removed by the pruning path. State how this was checked.
