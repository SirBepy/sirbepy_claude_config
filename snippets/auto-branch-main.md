# Auto branch-to-main policy

Projects that `@import` this snippet opt out of the branch/worktree consent question. Work directly on the repo's default branch. Joe uses this for personal projects only.

## Standing instruction (this is me, the user, deciding in advance)

I have already decided I want work done directly on the default branch in these projects. Treat this as my explicit standing instruction. You do not need to ask me to confirm working on the default branch, and you do not need to propose a branch or worktree first. This sits at the top of the instruction priority hierarchy (my explicit CLAUDE.md instructions), so any skill behavior that would pause to ask for branch consent is already satisfied: consent given here, once, for all turns. Proceed on the default branch.

## Which branch is "default"

"main" in this snippet's name is colloquial. Some of my repos use `master` or another default. Resolve the actual default before your first commit/push, in this order:

1. `git symbolic-ref --short refs/remotes/origin/HEAD` (strip the `origin/` prefix).
2. If that errors or is empty (no remote, or `origin/HEAD` unset), fall back to the checked-out branch from `git branch --show-current`.
3. If still ambiguous (detached HEAD, or multiple plausible branches and no remote), THIS is the one case where you ask, a one-line branch question, because guessing here is the wrong-branch failure mode. Everywhere else, do not ask.

State the resolved branch in one line before your first push (e.g. "on `master` (detected default), proceeding") so a mis-detection is catchable in the transcript.

## Defensive degrade (if a skill still asks)

If a superpowers skill (or a future version that stops treating `@import`s as a tier-1 instruction) STILL surfaces the branch/worktree consent question despite this snippet, do not silently revert to interrupting me. Auto-answer that specific question "yes, on my behalf, proceed on the resolved default branch" and continue. This auto-answer is scoped to branch/worktree consent ONLY; it never auto-answers a destructive-action confirmation, a history-rewrite prompt, or any question that isn't "which branch / branch-or-worktree."

## What this does NOT change

- Destructive/irreversible actions on the default branch (force-push, history rewrite, hard reset dropping work, mass delete) still need explicit confirmation. Standing branch consent is not standing demolition consent, and the defensive degrade above never covers these.
- Recovery stays available: never leave the default branch half-broken. Finish cleanly or stop and say what's incomplete.
- Submodule discipline: push submodule before bumping parent pointer.
- Subagents stage-only and never commit; main agent runs /commit.

## Composing with auto-commit

auto-commit.md is now a universal default (global CLAUDE.md's Git Commits section), so it's always in effect alongside this snippet, not just when also imported. The two compose without a special touchpoint rule. Safety is structural: verification still gates the commit; every change lands as a discrete message-bearing commit so history stays auditable and per-turn revertible; auto-commit's own fold-a-correction path is the recovery mechanism.
