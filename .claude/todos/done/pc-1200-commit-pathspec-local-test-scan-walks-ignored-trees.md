<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1157/1161/1169/1178/1192 are other commit-pathspec.sh defects (slug matching, argv length, --todo on excluded todos, step 7a messaging, absolute-path classification); none covers the find_recent_local_test scan cost -->
# 1200 - commit-pathspec.sh's local-only-test scan walks every ignored file and stalls for 10+ minutes

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-19

## Goal

A source-only commit in a local-only-tests repo finishes `[coverage-tests-check]` in seconds, not minutes.

## Context

2026-10-19, zng-app session fafa79c8: `commit-pathspec.sh --force coverage-tests -m "..." -- lib/api/session.dart` (a one-file dartdoc change) printed `[coverage-check] clean` and then sat for more than 10 minutes. The live process tree showed the script blocked in `git -C C:/Users/tecno/Desktop/Projects/zng-app ls-files -z --others -- .`.

Cause, read in `skills/commit/commit-pathspec.sh` `find_recent_local_test()` (around line 842): it runs `git ls-files -z --others -- .` WITHOUT `--exclude-standard` on purpose (so `.git/info/exclude`d tests count), which lists every ignored path in the repo: `build/`, `.dart_tool/`, `e2e/node_modules/`, and so on. For each path it calls `is_test_path`, then `date -r` (a process spawn per file on Windows) on any test-path match. The `--force coverage-tests` flag does not skip the scan, because the local-only branch (ii) runs before the force check.

The previous commit in the same session finished instantly because its pathspec named a tracked test file, so the scan never ran.

## Approach

1. Run the scan only when it can change the outcome, i.e. after the "pathspec names a test file" and `--force coverage-tests` checks, not before.
2. Narrow the walk: list only paths matching the test-path patterns (pass pathspecs like `':(glob)**/test/**' ':(glob)**/*_test.*'` to `ls-files`), instead of every ignored file.
3. Replace the per-file `date -r` with one batched `find -newermt` / `stat` over the matched paths.

## Acceptance

- In zng-app, a commit of one non-test source file with `--force coverage-tests` reaches `[commit]` in under 10 seconds.
- A local-only-tests repo with an excluded test touched in the last 24h still passes condition (ii) without `--force`.
- `python ci/run_all.py` green.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): local-test scan runs only when it can change the outcome (not under --force coverage-tests), walks only test-path globs, and batches mtimes in one stat. Not timed against real zng-app.
