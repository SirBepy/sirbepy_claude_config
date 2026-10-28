<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=7, reconfirm-count=3, content-hash=aab517ab -->
<!-- duplicate-checked -->
# clockify-reconciliator Audit mode's gap-detection should be scripted, not manual, once entry/commit counts get large

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/clockify-reconciliator/modes.md`'s Audit mode checklist (hard overlap, mechanical-split,
chopped-session, duration-sanity) is described as something to reason through directly. On a
week-scale audit this produced a real false positive that had to be walked back before Joe saw
it land. Add explicit guidance to run the overlap/coverage checks as a small script once the
entry or commit count crosses a size where manual timestamp arithmetic gets error-prone.

## Context

2026-08-27 zng-app session. Dev asked "did we sure there's nothing we didn't already log" for a
Mon-Thu week (23 Clockify entries, 93 commits across 2 repos). First pass was done by manually
reading each day's block list and eyeballing which commits fell in which gap - this produced a
false-positive finding ("Wed ~22:16 gap, 55186 commit unlogged") that was actually already
covered by an existing entry; the block's end time was misread against the commit's timestamp.
The error was caught by Claude itself, before writing anything, only because a second look was
taken - it was already presented to the dev as a confirmed finding once, in the same message
that also contained a *correct* finding, so a less careful pass would have shipped both.

A second, later pass - built as an actual script (commits and entries converted to epoch seconds,
one bash loop checking every commit against every interval, plus a pairwise interval-overlap
check) - ran once, cleanly, and gave a result the dev could be told was verified rather than
reasoned-through. That script also caught a real gotcha worth folding into the guidance: a naive
nested-loop version (spawning a `date -d` subshell per commit-times-interval pair) timed out at
93 x 23 = 2139 subshell spawns; precomputing all interval epochs once up front before the
per-commit loop fixed it (93 + 23 date calls instead of 2139).

## Approach

Add to `modes.md`'s Audit mode section:

- Once the day/entry count for an audit is large enough that a mistake would be non-obvious on
  re-read (rough heuristic: more than ~10 entries or ~30 commits, i.e. anything past a single
  day), do the hard-overlap and gap-detection checks as a short script rather than narrated
  reasoning: convert every entry's `[start,end)` and every commit's timestamp to epoch seconds
  once, then check coverage/overlap in a loop.
- Note the subshell-per-comparison trap: precompute interval epochs into arrays first, then loop
  commits against the precomputed arrays - don't call `date -d` inside a nested loop.
- A finding that will be shown to the dev as confirmed should come from the script's output, not
  from an earlier manual read that the script wasn't yet run to confirm.

## Acceptance

- modes.md's Audit mode section names a size threshold past which gap/overlap checks are
  scripted rather than manually reasoned.
- The subshell-batching gotcha is documented so a future session doesn't rediscover the timeout
  the hard way.

## Notes

The false-positive itself was caught and corrected within the same session before any bad write
happened - no bad data landed in Clockify. This todo is about tightening the process so the
catch doesn't depend on a second look happening to occur.

**Reconfirmed 2026-08-31, zng-app, plain Reconciliation mode (not Audit).** Same failure shape
outside Audit mode too: step 6a's gap detection was done by eyeballing each day's min/max entry
bound against commit local times, which produced a proposal (Wed 08/26, 22:35-23:55) that both (a)
overlapped an existing same-project entry (23:35-00:00) and (b) duplicated work that entry's
description already covered - the two commits it was "filling" were already logged. Caught only
because the dev asked to add an explicit same-project overlap check; not caught proactively. A
follow-up full per-commit-vs-per-entry coverage script (every commit's epoch ms checked against
every entry's `[start,end]` in true UTC, not just day-boundary min/max) then ran cleanly and
confirmed the ONLY real gaps were elsewhere (Fri + Sat, both zero-entry days). Suggests the
threshold in Approach should read "any step 6a gap detection with existing same-day entries
nearby", not just Audit mode or a size cutoff - a single day with a handful of entries was enough
to produce this false positive.
- Completed in /mega-todos wave 1, commit dd58170: Audit mode now carries explicit script-not-manual guidance plus the subshell-batching gotcha.
