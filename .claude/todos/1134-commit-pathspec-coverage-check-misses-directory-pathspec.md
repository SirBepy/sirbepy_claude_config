<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; done/1073 fixed the same-basename false positive, done/1101 untracked files in a tracked dir; neither covers a directory pathspec -->
# commit-pathspec.sh coverage check refuses deletions that a directory pathspec already covers

**Type:** skill-improvement
**Origin:** ai

## Goal
Passing a directory as the pathspec (`-- skills/impeccable`) counts every tracked deletion under it as
covered, as `git commit -- <dir>` itself does.

## Context
2026-10-08, loop-todos cycle 1 (commit 80dd5a5, the impeccable 4.5.0 update): `commit-pathspec.sh ...
-- skills/impeccable agents .gitignore ...` refused at `[coverage-check]` listing about 30 deleted
`skills/impeccable/scripts/*.mjs` files as "not in the pathspec (possible half-committed move)",
although the directory pathspec includes them. It needed `--force coverage`, which also silenced the
real signal for an unrelated pending deletion (`.claude/todos/920-*.md`). The check appears to compare
literal paths, not pathspec membership.

## Approach
In the coverage check, treat a staged or deleted path as covered when it is equal to OR under any
pathspec entry that is a directory (or use `git ls-files -- <pathspec>` membership). Add a
`test_commit_pathspec.sh` case: delete two files under a tracked dir, commit with `-- <dir>`, expect
no refusal.

## Acceptance
- A directory-pathspec commit of deletions under that directory passes without `--force coverage`.
- A deletion outside every pathspec entry, sharing a directory with one, still refuses.
