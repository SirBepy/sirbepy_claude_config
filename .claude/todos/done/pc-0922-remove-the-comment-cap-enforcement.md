<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/839 was the narrower "make the cap report better" fix, declined. 403 is the parked philosophy question about what the rule should be. This is the concrete removal of the enforcement mechanism, which neither of those covers. -->
# Remove the comment-cap enforcement

**Type:** task
**Origin:** dev

## Goal

The 2-line/4-line comment cap stops being mechanically enforced, so writing a genuinely useful
comment no longer trips a gate.

## Context

Joe, 2026-09-04, answering the question card for todo 839 (which asked how to make the cap's
commit-time rejection friendlier):

> "honestly, this can be removed now, i no longer care about it, at this point we are back to
> wanting comments in our code again
> but its important that the comments never explain what, but why, right? thats the best way to
> leave comments?"

So the CAP goes, but the intent behind it does not: comments should still say *why*, not *what*.
The distinction that matters is enforcement versus guidance. A hard numeric cap enforced at commit
time is what he no longer wants; a stated preference for why-over-what is what he still does.

Todo 839 was archived as declined on the same day. Todo 403 ("rethink the comment rule from what
comments are worth") stays PARKED for a dedicated `/brainstorm` session at his explicit request, and
todo 399 stays gated behind 403. This todo does not preempt 403: 403 decides what the guidance
should say, this one removes the machinery. Doing the removal first is deliberate, so the brainstorm
starts from a blank slate rather than from a defence of the existing numbers.

Not done during the `/mega-todos` run that recorded this, on purpose: twelve builder agents were
mid-flight with prompts instructing them to obey the cap, and pulling the mechanism out from under
them would have broken running dispatches.

## Approach

Trace every place the cap is enforced or restated before changing any of them. Known surfaces, all
to be re-verified rather than trusted from this list:

- `skills/commit/comment-noise.sh` and `skills/commit/comment-noise.md` - the mechanism itself
- `skills/commit/prefilter-gate.sh` - runs it as one of the gated prefilters
- `skills/commit/test_comment_noise.sh` - its self-tests, run by `ci/run_all.py`
- `skills/commit/SKILL.md` step 5a, and step 8's precondition list
- `skills/create-pr/SKILL.md`'s comment-noise check
- `refs/builder-preamble.md`'s prefilter paragraph, which every dispatch pastes
- `CLAUDE.md`'s Code Style section, which states the cap numerically

Decide one thing before starting, and say which was chosen: does `comment-noise.sh` get DELETED, or
kept and demoted to informational (prints, never fails)? Deleting is cleaner and matches "removed".
Demoting keeps the measurement available for the 403 brainstorm to look at. Deleting is the default
reading of what Joe asked for.

Replace the numeric cap in `CLAUDE.md` with the guidance he actually stated: a comment says why, not
what. Note the carve-out that came up in the same conversation - genuinely opaque code (a dense
regex, bit-twiddling, a non-obvious algorithm) can earn a one-line *what*, because reconstructing it
from source is real work. The test is whether a competent reader would be surprised or waste time
without the line.

`CLAUDE.md` now has headroom (ceiling raised to 7000, todo 921), but this change should still be
net-negative on tokens: the replacement guidance is shorter than the cap rules it removes.

## Acceptance

- `bash skills/commit/prefilter-gate.sh <any file>` no longer fails on comment length.
- No surface in the list above still states a numeric per-block comment cap. Grep for the numbers to
  prove it rather than reasoning about coverage.
- `CLAUDE.md`'s Code Style section states the why-not-what guidance, and its token count went DOWN.
- `python ci/run_all.py` passes, with `test_comment_noise.sh` either removed from the suite or
  passing against the demoted behaviour.

## Notes

Do not also relax the em-dash or secret-scan prefilters. They share `prefilter-gate.sh` with the
comment check and are unaffected by this decision; the em-dash ban in particular is one Joe has
reinforced repeatedly.
- Done in b5eb872 plus e943559. DECISION: comment-noise.sh was DEMOTED to informational, not deleted - prefilter-gate.sh still runs it and prints it labeled non-blocking, but it never sets the gate's exit status. Deleting outright was the todo's stated default, but hooks/commit-guard.py, hooks/test_commit_guard.py and skills/commit/test_prefilters.sh all call it, so deletion would have broken unowned callers. CLAUDE.md now states why-not-what with the opaque-code carve-out, and went 6698 to 6633 tokens (net negative, as required). test_comment_noise.sh deleted. The four surfaces the builder could not reach - mega-todos, delegation-doctrine, bepy-skill-creator, create-pr/drafting-rules - were cleared by the orchestrator in e943559; a repo-wide grep for the cap numbers now returns nothing outside the todo archive. Follow-on: hooks/test_commit_guard.py's backstop fixture was repointed at an em-dash violation in 3eb5722, since its old fixture only ever tripped the now-demoted cap.
