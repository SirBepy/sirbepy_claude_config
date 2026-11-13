<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: grepped the backlog for pathspec and rename; only pc-1342 (sidecar repeats, plumbing path) which is a different fix -->
# commit-pathspec.sh drops a brand-new file that sits at the old path of a staged `git mv`

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-11-13
**Summary:** A pathspec commit that names both ends of a `git mv` plus a new file created at the source path commits the rename but silently leaves the new file untracked, so HEAD is broken until a follow-up commit.

## Why

2026-11-13, rodge push gate: `git mv assistant/queries.ts assistant/assistantData.ts`, then a new `assistant/queries.ts` written at the old path. `commit-pathspec.sh -- ... assistantData.ts ... queries.ts ...` classified the old path as `index-removed (excluded from overlap-check/foreign-hunk-check - nothing left to diff)` and committed the rename only: `[commit] committed` exit 0, `queries.ts` stayed untracked, so the commit's HEAD failed to compile (every importer of `queries.ts`). It showed only in a `git status` after the commit; a second commit fixed it.

## Approach

In `skills/commit/commit-pathspec.sh`, classify a path that is `index-removed` in the index but present as an untracked file in the working tree as `untracked` (stage it like any new file), not `index-removed`. Or, minimum, print a loud warning and end non-zero when a pathspec path is still untracked after the commit. Add the case to the script's test.

## Acceptance

A test repo with a staged `git mv a b` and a new file at `a`: `commit-pathspec.sh -- a b` commits both, and `git status --porcelain` is empty afterwards.
