<!-- Claim before executing: .claude/todos/.claims/987-the-marker-gate-refuses-so-often-it-became-a-rubber-stamp.md -->
<!-- duplicate-checked -->
<!-- checked against 924 and 978, both in done/. 924 ADDED the session-marker gate and is correct as
     far as it goes; this todo is about what happened when that gate met a repo where its refuse
     condition is permanently true, which 924 could not have observed because it was measured on
     scratch repos. 978 added --own-since, which is part of the answer here but was shipped for a
     different reason (spanning already-committed commits) and its interaction with the gate was
     never exercised on a real multi-commit run. Neither covers this. -->
# The session-marker gate refuses on nearly every commit here, so it gets forced by reflex

**Type:** task
**Origin:** ai

## Goal

Make `commit-pathspec.sh`'s foreign-hunk gate produce a decision a caller actually reads, in a repo
where two or more sessions are live essentially all the time.

## Context

Found 2026-09-12 by the `/close` retrospective of the same run that shipped the gate, reviewing its
own behaviour rather than its own code.

Todo 924 made the gate honest: with 2+ live session markers, an auto-derived own-range cannot prove
the absence of a foreign hunk, so it prints UNVERIFIED and refuses instead of printing `clean`. That
is right, and the reasoning holds.

What it did not account for is that in THIS repo the refuse condition is close to permanent. There
were four live markers for the entire run. Over roughly twenty commits, the orchestrator passed
`--force overlap,foreign-hunk,coverage` on nearly every one, because there was no practical
alternative: declaring `--own-range` by hand for twenty-odd files is exactly the arithmetic todos 924
and 933 existed to abolish.

So the gate moved from one failure mode to its mirror image. Before: a check that could never fail,
printing `clean`. After: a check that nearly always fails, answered by a blanket override typed from
muscle memory. Neither state gives the caller information. The 440 dispatch in that same run warned
in its own prompt that "a noisy guard gets bypassed wholesale"; this is that, observed from inside.

Worth knowing, from the repo's peer channel (2026-09-10 09:54, session `6a0b`): the original
can-never-fail behaviour was NOT unnoticed. That session flagged it explicitly as todo 964's "own
accepted design" and left 924 and 933 open because of it. The 2026-09-12 run overturned that
decision rather than discovering the problem. Whoever picks this up is arbitrating between two
prior deliberate calls, not fixing an oversight.

**The lever probably already exists.** `--own-since <sha>` (todo 978) is trusted unconditionally
regardless of marker count, because a range traced to a git-verifiable commit list does not rest on
the assumption the gate polices. An orchestrator that knows its own start sha could pass
`--own-since` on every commit and get a real verdict instead of a forced one. That run shipped
`--own-since` and then never used it, which is itself the evidence that discoverability, not
capability, is what is missing.

## Approach

1. Measure before changing anything. Over the last run's commits, count how many refused on the
   marker gate and how many were resolved by `--force` rather than by a declared range. A fix aimed
   at the wrong ratio is wasted.
2. Decide where the default should move. Candidates, to be argued rather than assumed:
   - Have `commit-pathspec.sh` REFUSE with a message that names `--own-since <sha>` as the first
     remedy rather than listing `--force` as a peer option. Cheapest change, and it may be enough.
   - Have the caller-side wrapper (`skills/close/archive-and-commit-todo.ps1`) pass `--own-since`
     automatically from a session start sha it already has, so the common path stops needing a force.
   - Reconsider whether marker COUNT is the right signal at all. It answers "is anyone else here",
     not "has anyone else touched these files". A per-file question might be answerable from
     `git diff` timestamps or from the peer channel instead.
3. Whatever lands, keep 924's actual guarantee: the word `clean` must never appear on a path that
   was not verified. Loosening back to a comfortable lie is the one outcome worse than the noise.
4. Update `skills/commit/SKILL.md` step 8 in the same change, so the documented procedure names the
   new default path. The gate and the prose drifting apart is how this class of thing recurs.

## Acceptance

- A normal multi-commit run in this repo, with several sessions live, completes without a blanket
  `--force foreign-hunk` on every commit.
- A genuine foreign hunk is still refused, proven by a test, not by reading the code.
- `clean` still never prints on an unverified path.
- The documented procedure in `skills/commit/SKILL.md` matches what the script now does.
- `python ci/run_all.py` passes.

## Notes

- Do not solve this by widening what counts as a live marker or by raising the threshold above two.
  That reintroduces the original defect with extra steps.
- The measurement in step 1 is the part most likely to be skipped and the part most likely to change
  the answer.
