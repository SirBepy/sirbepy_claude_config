<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the only hit, done/243-flutter-bump-resolve-workspace-write-contradiction.md, is about /flutter-bump's workspace-write rules. It matched on the words "fails/against/code" only. Nothing in the backlog covers red-checking a test. -->
# Script the red-check (prove a new test fails against pre-fix code)

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-02

## Goal

Turn "stash the fix, run the new test, confirm it fails, pop" into one helper, instead of a
hand-assembled `git stash push -- <paths>` every time.

## Context

Done three times by hand in one zng-app session on 2026-09-02 (sc-55355, sc-55390, sc-55388), each
time as a bespoke chained command:

```
git stash push -m "<ticket> red-check" -- <lib paths>
  && <test command> | <filter>
  && git stash pop
```

It earned its keep every time: all three sets of new tests failed against pre-fix code with the
exact ticket symptoms, which is the only thing that distinguishes a real regression guard from a
vacuously-passing test.

Two problems with doing it by hand:

1. **It is unsafe on a shared checkout.** zng-app and zng-biller share one working tree across
   concurrent Conductor sessions. While the fix is stashed, a peer session running `/commit` by
   pathspec on an overlapping file would commit the *reverted* state, and a peer running the test
   suite sees phantom failures. During the 2026-09-02 run three peers were live in that tree; the
   window was only ~30s each time, but nothing made it safe, it was just short.
2. **Nothing enforces the pop.** If the test command hangs or the turn is interrupted between push
   and pop, the fix sits in the stash and the working tree silently looks unmodified. `/close` and
   `/commit` would both report a clean tree and neither would notice.

`CLAUDE.md`'s Testing & verification floor requires the checks but says nothing about proving a new
test is non-vacuous, so today this depends entirely on the session remembering to do it.

## Approach

A helper taking the fix paths and a test command, that:

- refuses to run if any path is outside the caller's own uncommitted changes
- prefers `git worktree add --detach HEAD <tmp>` over `git stash` when the repo is a shared
  checkout, so the live tree is never mutated at all. `/commit`'s own baseline-comparison step
  already uses exactly this trick for the same reason; reuse it rather than inventing a second
  mechanism
- runs the test in that worktree, asserts a non-zero exit, and prints the failing assertions
- tears the worktree down in a `finally`

Then reference it from wherever the verification floor is stated, so red-checking a new test is a
named step rather than a habit.

Worth checking first whether `/commit` step 6's baseline machinery can simply be exposed as this,
rather than adding a second script that does 80% of the same thing.

## Acceptance

- One command red-checks a new test without mutating the live working tree.
- Verified on a repo with a dirty peer file present, confirming that file is untouched throughout.
