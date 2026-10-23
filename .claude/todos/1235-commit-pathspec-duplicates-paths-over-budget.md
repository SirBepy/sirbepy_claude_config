<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no backlog file covers args_over_budget or the PREFILTER_ARGV_BUDGET default -->
# commit-pathspec.sh duplicates the prefilter lib's argv-budget helper and default

**Type:** refactor
**Origin:** ai

## Goal

One helper and one `PREFILTER_ARGV_BUDGET` default decide when a path list is too long for one
command line, shared by `commit-pathspec.sh` and the prefilter scripts.

## Context

Found by the 2026-10-23 loop-todos cycle-2 `/code-check` over `7269733..HEAD`.
`skills/commit/commit-pathspec.sh:89,96-104` `args_over_budget` is `skills/commit/_prefilter-lib.sh:13,37-44`
`paths_over_budget` line for line (sum of length+1 per arg against a budget), and both default
`PREFILTER_ARGV_BUDGET` to 12000 at separate sites, so retuning one silently skips the other.

Not a call-site swap: `_prefilter-lib.sh` sets a global `repo=""` and defines its own `git_c`
(with `core.quotePath=false`), while `commit-pathspec.sh` defines a different `git_c` and uses
`repo_root`, so sourcing the lib into commit-pathspec.sh is a namespace decision.

## Approach

Move the budget default and the over-budget helper into a tiny shared file (for example
`skills/commit/_argv-budget.sh`) that both `_prefilter-lib.sh` and `commit-pathspec.sh` source, so
neither script's `git_c` changes. Read `refs/refactoring-method.md` first.

## Acceptance

- One definition of the helper and one of the default, grep-verified.
- `bash skills/commit/test_commit_pathspec.sh` (its r70/r71 cases reach the helper) and
  `bash skills/commit/test_prefilters.sh` pass.
