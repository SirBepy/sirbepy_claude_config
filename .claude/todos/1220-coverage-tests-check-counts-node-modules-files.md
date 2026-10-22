<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1172 and 1163 are testing-floor hook bugs; this is commit-pathspec.sh's coverage-tests-check -->
# commit-pathspec.sh: the local-only-tests pass condition counts files inside node_modules

**Type:** hook-bug
**Origin:** ai

## Goal

In a local-only-tests repo, `[coverage-tests-check]` passes only on a test file Claude actually wrote or touched, never on a vendored file under `node_modules/` (or another dependency folder).

## Context

- 2026-10-22, zng-admin commit 51004fe (todo 86, the new `e2e/` suite). The commit was run with `--force coverage-tests`, but the check passed before the override mattered: `[coverage-tests-check] clean (local-only-tests repo: e2e/node_modules/playwright/lib/mcp/test/browserBackend.js was modified in the last 24h, untracked/ignored and deliberately kept off the pathspec)`.
- `find_recent_local_test` in `skills/commit/commit-pathspec.sh` walks `git ls-files --others` with no `--exclude-standard`, so ignored dependency trees are included on purpose (to see `.git/info/exclude`d tests). `npm install` writes thousands of fresh files, and any whose path has a `test/` segment satisfies `is_test_path`.
- Effect: in any local-only-tests repo with a freshly installed `node_modules` (zng-admin `e2e/`, zng-app `e2e/`), the check passes for every commit for 24h, test or no test.

## Approach

Skip paths with a `node_modules/` segment (and likely `.dart_tool/`, `build/`, `vendor/`) in `find_recent_local_test`, or restrict the walk to `.git/info/exclude`-listed paths plus untracked non-ignored ones. Add a fixture case to `test_commit_pathspec.sh`.

## Acceptance

- A fresh `node_modules/**/test/*.js` no longer satisfies the pass condition.
- A real untracked test listed in `.git/info/exclude` still does.
