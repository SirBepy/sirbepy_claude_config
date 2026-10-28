<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# "Subagents NEVER commit" is now contradicted by /mega-todos

**Type:** doc-consistency
**Origin:** ai

## Goal

Reconcile global `CLAUDE.md` and `refs/delegation-doctrine.md` with `/mega-todos`, which
deliberately lets its agents commit. Right now a cold session reading the global rules would
conclude the new skill is a violation and either refuse to run it correctly or "fix" it.

## Context

Written 2026-08-10 while building `/mega-todos` (committed `9d1937f`).

Global `CLAUDE.md` says, under Git Commits: "Subagents can't invoke skills, so subagents NEVER
commit." `delegation-doctrine.md` enforces it via the verbatim stage-don't-commit line in every
dispatch.

The stated REASON is mechanical (cannot invoke skills), not a safety property. That reason turns out
to be defeatable: `/commit` is pure procedure - git commands, one awk prefilter, and a marker file -
so its steps can be pasted into a dispatch prompt and followed by an agent that cannot invoke skills.

Two facts checked on 2026-08-10 that make it actually safe, not just possible:

- `/commit` step 8 commits BY PATHSPEC and explicitly "never reads the index", which is documented in
  the skill as being for exactly this case: concurrent sessions sharing one `.git/index`.
- The commit-guard marker was already made concurrency-safe: each commit writes its own uniquely
  suffixed marker and the hook consumes only the oldest, so parallel agents cannot steal each other's.

The residual hazards are NOT the index, and they are what the exception must be conditioned on:

1. Two agents editing the same file. A pathspec commit captures working-tree state, so agent A's
   commit would sweep in agent B's half-written edit. `/mega-todos` handles this with file-ownership
   lanes (no two concurrent agents share a file).
2. Shared mutable files. `complete-todo.ps1` prunes `PLAN.md` per todo, so archival was moved to the
   orchestrator rather than left in agents.
3. Branch drift, per `55-commit-must-recheck-branch-before-each-commit.md`. A wide run is the worst
   case for it; `/mega-todos` injects a per-commit branch guard.

## Approach

In global `CLAUDE.md`, Git Commits section: keep "subagents NEVER commit" as the default, and add
that the ONLY sanctioned exception is a skill that injects the full `/commit` procedure AND
guarantees file-ownership isolation, per-commit branch guard, and no agent writes to shared backlog
files. Name `/mega-todos` as that skill.

In `delegation-doctrine.md`: note that the verbatim stage-don't-commit line is replaced, not dropped,
by such a skill, so the "no exception, ever" wording there does not read as violated.

Do NOT weaken the default. The rule is right for ordinary dispatches; the exception is expensive to
qualify for and should stay that way.

## Acceptance

- A cold session reading global `CLAUDE.md` can tell why `/mega-todos` is not a violation.
- The three preconditions (lane isolation, branch guard, no shared-file writes) are stated as
  REQUIREMENTS of the exception, not as incidental implementation details.
- The default stage-don't-commit line still applies to every dispatch that is not one of these.

## Notes

- Related: `55-commit-must-recheck-branch-before-each-commit.md`, `36-commit-skill-precommit-hook-shared-git.md`.
- `/mega-todos` had not yet been run against a real backlog as of 2026-08-10. If its first real run
  shows the injected block is unsafe, the honest fix is to delete the exception, not to patch around it.
- Shipped 2026-08-11 in commit df3d04e. Both absolute statements of 'subagents NEVER commit' now carve out /mega-todos by name, so a cold session cannot mistake the skill's deliberate branch-guarded commits for a rule violation and 'fix' it.
