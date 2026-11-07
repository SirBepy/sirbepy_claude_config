<!-- Claim before executing: .claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1170 is the remove-item guard, a different surface -->
# Guard tokenizer residual gaps: mid-word continuation and second `gh pr edit` target

**Type:** task
**Origin:** ai
**Summary:** Two low-severity false allows left over after the commit-guard family fix (review-unpushed items 1-4, lane F1); neither is a regression.

## Why

The 2026-11-07 fresh reviews of the F1 fixes found these two. Both behave the same on master, so they were not fixed in the F1 slice, which was scoped to the review-unpushed payloads.

## Goal

The payloads below are denied/gated, each with a regression test that is red before the fix.

## Context

- `hooks/_hooklib.py` `join_line_continuations` replaces a backslash-newline with a space. Bash removes it with no space, so `gi\<newline>t commit -m x` is `git commit` in bash, but the guards (`commit-guard.py`, `push-read-gate.py`, `pr-guard.py`) see `gi` and `t`. Fix idea: a third variant in `shell_word_variants` that joins with an empty string (bash reading), keeping the space-joined one for PowerShell's backtick. The `join_line_continuations` docstring claim ("can only merge words, never hide one") is wrong for this payload until then.
- `hooks/pr-guard.py` `main()` checks ownership of only the FIRST `gh pr edit` target: `gh pr edit 5; gh pr edit 99` passes when PR 5 is the dev's own, though PR 99 is not. Fix idea: collect every edit target from `gh_pr_action`'s call list and require all to be owned.

- `hooks/commit-guard.py` `extract_commit_pathspec` reads redirection tokens as paths: `git commit -m x -- a.py 2>&1` gives `['a.py', '2>']` (and `> out.txt` adds `>` and `out.txt`). The prefilter-gate then exits 2, which `main()` does not treat as a failure, so the commit-time prefilter re-check is skipped when a redirection follows the pathspec. Fix idea: stop the pathspec at any token starting with `>`/`<` or matching `\d*>&?\d*`.

## Approach

Add the payloads to `hooks/test_commit_guard.py`, `hooks/test_push_read_gate.py`, `hooks/test_pr_guard.py` first, prove red with `skills/close/red-check.ps1`, then fix. Run the hook import smoke after any `_hooklib` change.

## Acceptance

- `gi\<newline>t commit -m x` (bash reading) is gated by commit-guard, and `gi\<newline>t push` / `gh pr cre\<newline>ate` by their guards.
- `gh pr edit 5; gh pr edit 99` is blocked unless both targets are owned.
