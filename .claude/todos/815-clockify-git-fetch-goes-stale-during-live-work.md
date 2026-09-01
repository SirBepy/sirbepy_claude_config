<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=77e3e7c7 -->
<!-- duplicate-checked -->
# clockify-reconciliator's step 6 git fetch goes stale when the dev is actively committing mid-run

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a re-fetch-before-finalize step (and a "cap at a clean boundary, defer the rest" rule) so a
Reconstruction run whose window extends to "now" doesn't finalize hours off a stale commit
snapshot while the dev is still working.

## Context

2026-08-27 zng-app run (Mon-Wed reconstruction): step 6 fetched commits once, early in the run, and
built the whole plan from that snapshot. By the time step 9's approval question was answered, real
time had moved well past the original fetch - the dev was actively coding a late-night session that
kept producing new commits. The dev caught this ("myb we should increase wednesday cuz im still
working") and asked to re-check with the peer session doing the work.

Re-fetching after that prompt turned up 5 commits the original fetch had missed entirely: 2 more on
Wednesday night (23:56) and 3 more on Thursday morning (00:22), all on a linked worktree branch
(`54968-lender-flow`) that IS reachable via `git log --all` from the main checkout - the miss wasn't
a `--all` scoping gap (that failure mode is already covered by todo done/485), it was pure timing:
the commits didn't exist yet when step 6 ran.

A follow-up peer-session check (`list_peers` + a targeted message) confirmed the session was still
mid-run with more commits expected imminently. The dev's resolution: cap the reconstructed entry at
the nearest clean boundary (midnight) rather than projecting forward or waiting indefinitely, and
explicitly defer asking about the excluded tail to a future run. This worked well live but was
improvised in the moment - the skill doesn't currently prompt for either the re-fetch or the
cap-and-defer move.

## Approach

In `SKILL.md` step 6 (or a new step right before step 9's approval gate):

- If the window's end is within the last few hours of "now" (i.e. the reconstruction covers today or
  very recent activity), re-run the git-log fetch immediately before presenting the final step 9
  approval question, not just once at the start of the run. Note in the plan if the re-fetch changed
  anything from what was already shown to the dev.
- If a re-fetch (or a peer-session check) reveals the dev - or a peer session driving work under the
  same git identity - is still actively committing, don't project the reconstructed entry forward
  into guessed additional time. Cap the entry at the last confirmed commit + the stated pad, or at
  the next clean boundary (midnight) if that's closer, and explicitly flag the excluded tail as "ask
  again once that session wraps" rather than silently dropping it or silently including a guess.
- Consider whether `list_peers`/`post_message` (Claude Conductor sessions) should be a documented
  step for exactly this check - confirming with an actively-running peer session before finalizing
  hours attributed to "right now" - rather than something only reached for ad hoc.

## Acceptance

- A Reconstruction run whose window includes "now" re-fetches commits at least once between the
  initial draft and the final apply-approval question.
- When live/in-flight work is detected, the finalized entry stops at a clean, defensible boundary
  and the excluded remainder is named to the dev as deferred, never silently included or silently
  dropped.

## Notes

Related but distinct from `814-clockify-reconstruction-3h-bridge-overcounts-sparse-days.md` (that
one is about the clustering math overcounting; this one is about the input snapshot going stale
mid-run). Both surfaced in the same 2026-08-27 session.
