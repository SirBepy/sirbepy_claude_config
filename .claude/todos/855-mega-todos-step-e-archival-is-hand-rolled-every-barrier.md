<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for archival helper / barrier pathspec / complete-todo loop: done/504 touches the script itself, nothing covers the batch-archival step. -->
# /mega-todos Step E archival is hand-rolled at every barrier, and it broke twice

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/mega-todos` Step E a scripted archive-and-commit step, so a barrier does not rebuild the same
`complete-todo.ps1` loop plus exact-pathspec commit by hand, and so the id-prefix glob that broke it
twice cannot break it again.

## Context

Filed 2026-09-01 from a `/close` retrospective over a `/mega-todos` run that archived 36 todos across
four barriers.

`skills/mega-todos/SKILL.md` Step E says archival is main-thread only and lists the steps in prose:
run `complete-todo.ps1` per todo, commit the result, reconcile ids. It provides no helper, so each
barrier re-derives the same two things by hand:

1. a loop calling `complete-todo.ps1 -Id <stem> -Note "<text>"` for each passing todo, and
2. an exact commit pathspec naming BOTH halves of every archive move (the source
   `.claude/todos/<id>-<slug>.md` and the destination `done/<id>-<slug>.md`), because a bare
   `.claude/todos` pathspec would sweep in concurrent sessions' unrelated todo files.

It was written four times in one run and failed twice, both times on the same class of bug:

- **`ls .claude/todos/done/96-*.md` matched two files.** `done/` already contained
  `96-todo-creation-lacks-duplicate-check.md` alongside the newly archived
  `96-create-pr-trunk-gate-misses-non-gitflow-repos.md`. The glob returned both, the derived basename
  was garbage, and `git add` aborted with `fatal: pathspec ... did not match any files`, staging
  nothing. Note the ids do not have to collide in the LIVE backlog for this to bite; `done/`
  accumulates every id ever used.
- **A source path that no longer existed.** Todo `848` had been filed by a peer and was still
  untracked when it was archived, so after the move there was no `.claude/todos/848-*.md` to stage,
  only `done/848-*.md`. Naming the source path anyway aborted the whole `git add` again.

Both are recoverable in a minute, but they cost three wasted tool calls each and they will recur on
every wide run, because the glob-by-id-prefix shape is the obvious way to write it.

## Approach

1. Write `skills/mega-todos/archive-batch.ps1` (or extend a `skills/close/` helper if that is the
   better home, decide and say which) taking a list of `<id>|<note>` pairs and:
   - resolving each id to exactly ONE live backlog file, failing loudly on zero or multiple matches
     rather than globbing and hoping;
   - calling `complete-todo.ps1` per id;
   - emitting the exact commit pathspec afterwards, including only paths that EXIST, and covering
     both halves of each move.
2. Have it print the pathspec rather than committing, so `/commit`'s own gates (prefilter, branch
   guard, overlap check) still run from the caller. The helper should not grow its own commit path.
3. Point Step E at the helper and delete the prose reconstruction.
4. Test against a scratch copy of a backlog that deliberately contains a `done/` id sharing a prefix
   with a live todo, and an untracked todo, since those are the two shapes that actually broke.

## Acceptance

- [ ] A barrier archives N todos with one call, no hand-built glob
- [ ] An id whose prefix also exists in `done/` resolves correctly or fails loudly, never silently
- [ ] An untracked source todo archives without aborting the stage
- [ ] The emitted pathspec names both halves of every move and omits non-existent paths
- [ ] `/commit`'s gates still run from the caller; the helper does not commit
- [ ] Verified against a scratch backlog reproducing both failure shapes

## Notes

- Worth roughly a 6: it is pure orchestrator ergonomics with no user-facing effect, but it fired
  twice in one run and the failure mode is a silent no-op stage rather than a loud error, which is
  the part that makes it worth scripting.
- Related: `done/504-complete-todo-silently-no-ops-against-the-wrong-repo.md` hardened the underlying
  script's own messaging in the same run. This todo is about the caller-side loop, not that script.
- The `git mv` two-path rule this depends on was written into `/commit` step 8 by
  `done/495-commit-pathspec-drops-the-source-half-of-a-git-mv.md` in the same run, so the helper
  should cite it rather than re-explain it.
