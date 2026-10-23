<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no backlog file covers batch_untracked_diffs or print_taken_hunks -->
# commit-pathspec's batched untracked diff loses the "first changed line" in hunk(s) taken on trust

**Type:** bug
**Origin:** ai

## Goal

`--force foreign-hunk` always prints each trusted hunk's `@@` header AND its first changed line,
including for a file whose hunks came from the batched untracked diff.

## Context

Found by the 2026-10-23 loop-todos cycle-2 `/code-check` over `7269733..HEAD`, by reading the
code, not reproduced. `skills/commit/commit-pathspec.sh:734-757` (`batch_untracked_diffs`, used
when 16+ untracked files are in the pathspec) keeps only `diff --git` and `@@` lines. For an
untracked-class file that also has a HEAD blob (`git rm --cached`, then recreated), with 2+ live
session markers and `--force foreign-hunk`, `print_taken_hunks` (`:384-404`, called near `:803`)
then prints the `@@` line with no first changed line. Display-only: the refusal logic counts `@@`
lines and is unaffected. The visibility is what todo 1124's rule relies on before a peer's hunk is
taken whole.

## Approach

Have `batch_untracked_diffs` keep the first `+`/`-` line after each `@@`, or re-run the per-file
`diff --no-index` for a file that lands in `unverified_files` from the batch path.

## Acceptance

A test in `skills/commit/test_commit_pathspec.sh`: 16+ untracked files, one of them `git rm
--cached` and recreated, 2 session markers, `--force foreign-hunk`; the output's
`hunk(s) taken on trust:` block shows that file's first changed line. Fails before the fix.
