<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep of the backlog for fileMode, chmod and executable bit found nothing -->
# commit-pathspec.sh drops an executable bit that only the index holds

**Type:** skill-improvement
**Origin:** ai
**Summary:** On Windows (`core.fileMode=false`) `commit-pathspec.sh` commits a file at mode 100644 even after `git update-index --chmod=+x`, so a script that must be executable on a Linux runner cannot be committed through the normal path.

## Goal

A pathspec commit keeps a mode change staged with `git update-index --chmod=+x`, or the script refuses with a plain message naming the workaround.

## Context

- Seen 2026-11-05 in the rodge repo: `git update-index --chmod=+x infra/trial/test/fake-aws` showed `M  infra/trial/test/fake-aws` staged, then `commit-pathspec.sh ... -- Dockerfile infra/trial/test/fake-aws` committed it, and `git ls-tree HEAD infra/trial/test/fake-aws` still printed `100644`. Cause (not proven by reading the script, only by this behaviour): `git commit -- <paths>` builds its temporary index from HEAD plus the working-tree files, and on NTFS the working-tree file has no executable bit.
- What worked: staging the mode with `git update-index --chmod=+x <file>` and then a plain `git commit -m ...` (nothing else staged; checked with `git diff --cached --name-status`) gave `100755`.
- The cost of not knowing: the file shipped as 644 in a release push, and the Linux CI run of 0.2.3 failed 11 object-lock tests with `Permission denied` on it.

## Approach

In `skills/commit/commit-pathspec.sh`, after the pathspec commit, compare `git ls-tree HEAD <path>` modes against `git ls-files -s <path>` modes taken before the commit for every pathspec file; on a mismatch print a warning naming the file and the `update-index --chmod` plus plain-commit workaround, or implement the mode-preserving commit (`git commit` of the index limited to files with a staged mode change). Add a case to `skills/commit/` tests if a suite for the script exists.

## Acceptance

- A test repo with `core.fileMode=false`: stage `--chmod=+x` on a file, run the script with that file in the pathspec, and `git ls-tree HEAD` shows 100755 (or the script printed the warning).

## Notes

- commit-pathspec.sh replays staged exec-bit changes through its plumbing commit under core.fileMode=false; chmod +x and -x cases in test_commit_pathspec.sh fail without it
