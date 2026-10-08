---
name: review-unpushed
description: Reviews unpushed commits for correctness bugs via sliced sonnet fan-out; called by /commit and /loop-todos before push.
argument-hint: "[range, default @{u}..HEAD]"
---

# /review-unpushed

> Per-commit correctness review fan-out over unpushed commits. Called from /commit's Pre-push gate
> and from /loop-todos, not typed standalone in the normal case.

## Trigger

Called from another skill's procedure, not typed directly in the normal case: `/commit push
review` and `/loop-todos`'s final review phase both invoke this file's steps rather than restating
them. Takes one optional range argument, default `@{u}..HEAD`.

## Why this exists, not /code-check

`/code-check` reviews structure: file splits, DRY, dead code, written-convention breaches. This
skill reviews CORRECTNESS: does the commit's own change do what it claims, for every unpushed
commit, judged at the commit it actually produced. The two never substitute for each other - a
`/commit push` run uses both, in sequence, on different passes.

## Step 1 - Resolve the range

`git log --format='%H %s' <range>` (default `@{u}..HEAD`) enumerates the unpushed commits in
scope, oldest first. No commits: report `N=0 unpushed commits, nothing to review` and stop.

## Step 2 - Slice by area

Group the commit list by area (the directory/package most of its files sit under), roughly 10-13
commits per reviewer - the size that already worked across the hand-built rounds this skill
replaces (57 commits in 5 slices, then runs of 26, 5, 9, 13). A commit whose files span more than
one area goes with whichever slice already holds the most of its files; never split one commit's
own diff across two reviewer dispatches.

**A fresh reviewer for the session's own fixes.** If the invoking run itself authored any commits
inside the range (same session, or commits made since that run's own recorded start sha), those
commits get a SEPARATE reviewer dispatch from every other slice - never bundled with commits the
run did not just write, and never reviewed by continuing the dispatch that wrote them. This is
`/code-check`'s "the session that wrote the code never reviews it" rule, applied per-commit instead
of per-diff: the property only holds if the reviewer has no memory of writing the thing it is
judging.

## Step 3 - Dispatch

One `model: 'sonnet'` dispatch per slice, `subagent_type: general-purpose`. Fire every slice's
dispatch in the same message, since they are read-only and file-disjoint by construction (each
slice reviews different commits, not different working files) - `refs/delegation-doctrine.md`'s
Parallelism rule has nothing to serialize here.

Each dispatch prompt:

```
READ-ONLY DISPATCH

Stage your changes but do NOT commit. The main agent will run /commit after your report-back.
(For a repo sharing a git index with concurrent sessions, use instead: "Leave all changes
unstaged. The main agent will run /commit by pathspec after your report-back.")

`run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
before ending your turn.

You are reviewing commits for CORRECTNESS BUGS only, not structure or style - a separate pass
already covers file splits, DRY and dead code, so do not repeat that.

Judge each commit AT ITS OWN COMMITTED STATE, never the working tree: `git show <sha>` for the
commit's own diff, `git show <sha>:<file>` for full-file context when the diff alone is not enough.
The working tree may hold unrelated, unreviewed changes from later commits or another session -
never let those influence your verdict on this commit.

For each commit below, try one adjacent case each fix's own tests skip (an edge its diff's test
coverage does not reach, when the commit touches tested code), then report:

- The commit's sha and subject.
- Verdict: OK or NEEDS-IMPROVEMENT.
- Every finding cited as `file:line`, stating what is wrong and why - not a style opinion.
- Zero findings is a valid, complete answer for a commit. Do not manufacture one to look thorough.

Commits to review (oldest first):
<sha> <subject>
<sha> <subject>
...
```

## Step 4 - Triage

Once every slice reports, split its findings into:

- **Fix-now** - a real bug in a commit still unpushed, cheap to fix before it ships. This is what
  the hand-built rounds this skill replaces actually caught, including 2 regressions in safety
  hooks. Fix it, recommit through `/commit`'s fold rules (the target commit is still unpushed, so
  folding is available), then rerun the fast-check floor.
- **Backlog** - a real finding not worth blocking this push for (low severity, a large rewrite, or
  a commit already superseded by a later one in range). File it per `close/ai-todos-format.md`,
  `**Origin:** ai`.

Zero findings across every slice is success, not a sign the review did not run - say so explicitly
in the report rather than treating silence as suspect.

## Step 5 - Report

One summary: commits reviewed (count and range), slices dispatched, OK vs NEEDS-IMPROVEMENT per
commit, fix-now findings with the resulting sha, backlogged findings with their todo id, and the
session's-own-fixes slice named separately so a caller can confirm that rule was actually followed.

## Notes

- Never commits and never claims a todo on its own. The fix-now fold happens through the caller's
  own `/commit` invocation, triggered by this skill's Step 4 - not by this skill acting alone.
- Dispatches only the per-slice reviewers above; it does not re-run itself for a second pass. A
  caller wanting another round invokes this skill again over the (now smaller) remaining range.
