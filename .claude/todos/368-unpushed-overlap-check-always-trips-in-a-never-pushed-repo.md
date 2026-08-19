<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/commit`'s unpushed-overlap check is permanently tripped in a repo with no push cadence

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the unpushed-overlap check discriminate between "you are accidentally splitting one unit of
work across two commits" and "you touched this file six weeks ago", instead of firing on every
commit in a repo that never pushes.

## Context

Observed 2026-08-17 in `~/.claude`. `/commit` step 8's fourth precondition says:

> **Unpushed-overlap check:** `git log @{u}..HEAD --format='%h'` (skip silently, no upstream). For
> each sha, `git show --name-only --format= <sha>` and intersect with this commit's pathspec. Any
> overlap: STOP, name the overlapping commit, ask [...]

In this repo `git log @{u}..HEAD` returned **50 shas**. Intersecting six paths against fifty commits
found overlap on two of them: `.gitignore` (in `2573d5e` and `2f2be17`) and
`skills/auto-do-todos/SKILL.md` (in `7bb8751` and `7a13c14`). Both were obviously unrelated - a
different todo, a different section of the file, committed days apart. The run proceeded on the
rule's own "genuinely separate -> proceed" branch.

The check is not wrong, it is miscalibrated for this repo. `~/.claude` accumulates unpushed commits
indefinitely, so the unpushed window is not "work in progress since my last sync", it is "months of
history". Under that condition every frequently-edited file - `CLAUDE.md`, any SKILL.md, `.gitignore` -
overlaps something, and a guard that fires on nearly every commit is a guard that gets waved through
on nearly every commit. That is worse than not having it, because the waving-through becomes routine.

Cost is also real, not just theoretical: intersecting a six-path commit against fifty shas is fifty
`git show` invocations, or one wide `git log` sweep, per commit, six times in that run.

## Approach

Options, roughly in order of preference. Do not simply delete the check - todo 281 added it for a
real reason and that reason still holds inside a single session.

1. **Bound the window by recency, not by push state.** The failure mode 281 targeted is stacking a
   second commit on work you *just* did. `git log @{u}..HEAD --since=<N hours>` or "commits made in
   this session" captures that and ignores archaeology. Session-own shas are already tracked for
   `/close` Phase 2's `shas:` scope, so the plumbing exists.
2. **Narrow what counts as overlap.** File-level intersection is too coarse for a 500-line SKILL.md
   that a dozen unrelated todos each touch one section of. Overlapping HUNKS, or an overlap on a
   file that is small or single-purpose, is the real signal.
3. **Cap the scan.** If `@{u}..HEAD` exceeds some count, say so once and check only the most recent
   N, rather than silently doing fifty `git show` calls.

Whichever is chosen, `/commit` should state what it did rather than leaving the reader to infer it,
and the "STOP and ask" instruction needs a stated answer for unattended runs - `/auto-do-todos`'s
precedence says Steps 6-7 never ask, so today the two contracts disagree about what happens on a hit.

## Acceptance

- A commit in `~/.claude` touching a long-lived file does not trip the check on unrelated history.
- Stacking a second commit on the same unit of work within one session still trips it (verify
  deliberately, so this is not confused with disabling the guard).
- The unattended-run behaviour on a hit is written down in one place, not implied by two skills.

## Notes

- Filed 2026-08-17 by `/close` Phase 1, from six commits in one `/auto-do-todos` run.
- **Second data point 2026-08-18**, and it sharpens option 2 above. The unpushed window was only
  TWO commits, both from the same session, so the recency bound in option 1 would NOT have helped -
  it still tripped. What it tripped on was `CLAUDE.md` and `.claude/todos/PLAN.md`, two long-lived
  shared files where the earlier commit touched a completely different section (the testing floor
  and a lane line) from the later one (the outbound rule and a different lane line). **File-level
  intersection is the whole defect here, not window size.** That makes option 2, hunk-level or
  small-file-only overlap, the load-bearing fix rather than a refinement.
- The session proceeded past the hit without asking, on the reasoning that `/test` and `/ticket` are
  plainly separate units, and surfaced the overlap in its summary instead. That is the
  waving-through this todo predicts, done knowingly. Recording it as evidence, not as a defence.
- Related: [[281-commit-no-guard-against-stacking-same-area-unpushed]] in `done/`, which introduced
  this check. This todo is a follow-on to that fix, not a request to revert it.
- The repo's large unpushed backlog is not itself a problem to fix here; it is the condition that
  exposes this one.
