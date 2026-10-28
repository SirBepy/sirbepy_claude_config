<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=adeda2cf -->
<!-- duplicate-checked -->
# Nothing stops HEAD~n being used to undo a commit in a shared checkout

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "undo a commit" path refuse positional refs in repos where concurrent sessions share one
index, so it cannot silently un-commit another session's work.

## Context

Near-miss on 2026-08-26 in zng-app (`develop`, main checkout, multiple concurrent sessions sharing
one `.git`).

Joe asked for a commit to be undone so a peer session could move its work to a worktree.
`git reset --soft HEAD~1` was run. It was correct only by timing: that commit was still `HEAD`. A
peer session flagged straight afterwards that had its own commit landed first - it was committing to
the same branch at that moment - `HEAD~1` would have resolved to **their** commit and moved their
work into another session's index. No error, no warning.

`HEAD~n` is positional, so its meaning changes the instant anyone else commits. Reading `git log`
and then resetting is a two-step race.

Existing coverage and why it is not enough:

- `~/.claude/snippets/auto-commit.md` owns the fold/undo path but is written for a single-session
  repo.
- `/commit` has a branch guard, nothing about positional refs.
- The global CLAUDE.md rule requires `list_peers`/`post_message` before committing in a shared repo,
  which surfaces the peer but does not make the ref safe.
- A project memory now records the behaviour for zng-app
  (`feedback_never_head_tilde_in_shared_checkout`), but zng-biller shares the same hazard and has no
  such note, and a memory is guidance rather than enforcement.

## Approach

Preferred: a `PreToolUse` hook matching destructive git invocations that carry a positional ref
(`reset`, `rebase`, `checkout`, `branch -f` with `HEAD~`/`@~`/`HEAD^`), rejecting when the repo has
more than one live session. Detecting "shared" is the open question - candidates are `git worktree
list` showing the main checkout in use, or the Conductor peer list. Settle that before building; a
hook that fires everywhere will be disabled within a week.

Cheaper fallback if the detection proves unreliable: add an explicit rule to `auto-commit.md`'s undo
section requiring the sha the commit reported, plus a `git log -1 --format=%H` equality check
immediately before the reset.

Worktrees are not affected - each carries its own `HEAD` and `index` under `.git/worktrees/<name>/`
so it cannot collide this way. Scope any guard to the main checkout.

## Acceptance

- Running `git reset --soft HEAD~1` in a shared zng-app checkout is refused or warned, with the
  explicit-sha form named in the message.
- A worktree session is not affected.
- The single-session case stays prompt-free.

## Notes

- Completed in /mega-todos wave 1, commit 5099010: destructive-command-guard.py now covers positional-ref destructive git commands in a shared checkout, not just git reset --hard.
