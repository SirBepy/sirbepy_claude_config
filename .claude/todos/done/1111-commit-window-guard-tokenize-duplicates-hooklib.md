<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# commit-window-guard's _tokenize reimplements _hooklib.tokenize_segment

**Type:** task
**Origin:** ai

## Goal
Decide whether `hooks/commit-window-guard.py`'s private `_tokenize` should be replaced by `_hooklib.tokenize_segment`, and either swap it or record why the two must stay separate.

## Context
`hooks/commit-window-guard.py:111` (`_tokenize`) does shlex `posix=False` + `strip_quotes`, falling back to a whitespace split on unbalanced quotes - the same non-empty-fallback contract as `hooks/_hooklib.py:144` (`tokenize_segment`), whose docstring explains why an empty list would smuggle a blocked command past a hard-block guard. The difference: `tokenize_segment` also runs `flatten_tokens`, which splits every token on commas. In this guard that would split a `git -C "C:\a,b" commit` path or a comma inside `-m` text into extra tokens. The tokens feed `_segment_landings` (subcommand detection, `-C`/`--repo` target) and push-gate's `_pinned_cd`.

Found by `/code-check shas:fce4a26` (class 3, DRY). A sibling finding on the same commit (VALUE_FLAGS / CHAIN_SPLIT_RE duplicated with push-gate.py) was dropped as declined, by the 2026-09-10 precedent in `.claude/todos/dropped-findings.log` line 8 (guards kept independent on purpose).

## Approach
Either (a) add a `flatten: bool = True` parameter to `tokenize_segment` and call it with `flatten=False` from commit-window-guard, deleting `_tokenize`; or (b) keep `_tokenize` and expand its comment to state the comma-path reason so the next review does not re-raise it. Prefer (a) only if the other `tokenize_segment` callers stay unaffected.

## Acceptance
- `python hooks/test_commit_window_guard.py` passes, plus a new case: `git -C "<client repo path containing a comma>" commit` is still denied at 00:40.
- `python ci/run_all.py` green.

## Notes

- Archived via /cleanup-todos 2026-10-08 (loop-todos cycle 1): worth 4, ai-origin. No reproduced incident; a sibling DRY finding on the same guards was already declined in dropped-findings.log (guards kept independent on purpose).
