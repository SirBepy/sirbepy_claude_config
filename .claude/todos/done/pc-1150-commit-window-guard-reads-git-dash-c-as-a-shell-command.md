<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=0d8ec1bf -->
<!-- duplicate-checked: 2026-10-08; 1140 is date-override scoping in the same guard, done/1111 its tokenizer duplication; neither covers the inline-command flag match -->
# commit-window-guard reads git's own `-c key=value` as a nested shell command

**Type:** task
**Origin:** ai

## Goal
Only a real shell wrapper's `-c` / `-lc` / `-Command` / `/c` makes the guard re-scan the next
token as a command, so a read-only git call is never refused during the client-repo window.

## Context
Found by the pre-push /code-check (2026-10-08, range 9bc83ae..911d37e, commit fce4a26):
`hooks/commit-window-guard.py` `landing_targets()` (around lines 80 and 171) treats the token after
any flag whose lowercase form is in `INLINE_COMMAND_FLAGS = {"-c", "-lc", "-command", "/c"}` as a
nested command, which also catches git's own `-c key=value` and, through `.lower()`, `-C <dir>`.
Verified by the reviewer: `git -c core.editor="git commit -m x" status` is classified as a commit
landing and would be denied in a client repo from 23:00 to 10:59. It can only over-block.
`hooks/test_commit_window_guard.py` has no `git -c` case.

## Approach
Rescan the next token only when the PRECEDING token's basename is a shell (`bash`, `sh`, `zsh`,
`powershell`, `pwsh`, `cmd`, `cmd.exe`). Add the case above to the suite's DETECT_CASES expecting no
landing target. Live guard: one complete edit, run its test file right after.

## Acceptance
- `git -c core.editor="git commit -m x" status` yields no landing target.
- `bash -c "git commit -m x"` in a client repo inside the window is still denied.
- `python hooks/test_commit_window_guard.py` passes.

## Notes

- Done 2026-10-08: the -c/-lc/-command//c rescan fires only after a shell basename, and a new _value_end() reads a git -c/-C value whole even when shlex(posix=False) split it at a mid-word quote, a second independent path to the same false deny. Test: git -c core.editor="git commit -m x" status yields no landing target; bash -c "git commit -m x" still does.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved with the 1139-1144 batch. Same file as 1140; one lane, one commit each.
