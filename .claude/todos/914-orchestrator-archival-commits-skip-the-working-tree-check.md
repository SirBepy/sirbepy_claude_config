<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 872 (in done/) hardened this check for the BUILDER's injected commit block. This is the orchestrator's own barrier commit, which 872 explicitly did not cover. -->
# Orchestrator archival commits skip the working-tree check builders now enforce

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/mega-todos` Step E state that the orchestrator's own barrier commits obey `/commit` step 8's
working-tree diff check, and forbid building an archival pathspec from a directory-wide
`git status`.

## Context

Reproduced 2026-09-04 in the `/mega-todos` run over `~/.claude`, by the orchestrator, roughly two
hours after that same run committed todo 872 (`ae9ade1`), which added exactly this gate to the
builder's injected commit block.

What happened: the orchestrator needed to commit 20 parked todo files plus 4 new ones, and built
the pathspec as `git status --porcelain -- .claude/todos/` filtered by status prefix. That
directory also held `.claude/todos/dropped-findings.log`, which a wave-2 builder (todo 898) had
just appended a line to. The line was complete and correct, so nothing was corrupted, but it landed
in the orchestrator's commit `f5b5156` rather than its author's `a836f59`. Attribution loss, not
data loss - this time. The same pattern over a half-written file is the real hazard, and it is
precisely what `/commit` step 8's "account for every hunk" bullet exists to catch.

Two things made it reachable:

1. **Step E never says the orchestrator is bound by step 8.** 872 hardened the builder's block and
   the barrier `COMMIT_MODE` section; Step E's archival commit is neither, so it reads as exempt.
2. **A directory-wide `git status` is the natural way to build an archival pathspec**, since
   archiving is a bulk move, and it is exactly the wrong way while N builders hold uncommitted work
   in the same tree.

Note the fix already exists and was landed by this same run: `skills/mega-todos/archive-batch.ps1`
(todo 855, commit `9fa351b`) returns a `.Pathspec` naming both halves of every move plus `PLAN.md`,
derived from the ids being archived rather than from tree state. Using it makes this class of bug
unreachable. The orchestrator did not, for the reason the sibling todo covers.

## Approach

1. In Step E, state plainly that the archival commit is subject to `/commit` step 8 in full,
   including the working-tree diff check, and that the pathspec comes from `archive-batch.ps1`'s
   `.Pathspec` return - never from `git status` over a directory.
2. Add the same sentence to the barrier `COMMIT_MODE` section, which already substitutes "main
   thread" for "builder" throughout but inherits the same blind spot.
3. Consider having `archive-batch.ps1` itself refuse a pathspec entry it did not derive from an id
   it was given, so the guarantee is mechanical rather than a rule to remember.

## Acceptance

- Step E and the barrier `COMMIT_MODE` section both name step 8's working-tree check explicitly.
- A dry-run of the 2026-09-04 sequence - 24 todo files to commit while `dropped-findings.log` is
  dirty from a peer - leaves that file out of the pathspec.
- `/commit`'s own text is unchanged; this is a `/mega-todos` gap, not a `/commit` one.

## Notes

- Filed by /close on 2026-09-04 from the `/mega-todos` run's own retrospective. The incident is the
  orchestrator's, not a builder's.
