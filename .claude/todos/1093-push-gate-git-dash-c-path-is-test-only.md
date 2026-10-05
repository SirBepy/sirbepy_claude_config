<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-05; grepped backlog + done/ for "git_dash_c_path", only done/1044 (the fix that introduced resolve_push_target) hits. -->
# push-gate.py's git_dash_c_path duplicates resolve_push_target and only a test calls it

**Type:** task
**Origin:** ai

## Goal
`hooks/push-gate.py` has one walk over the command's git segments, not two.

## Context
Found by the 2026-10-05 pre-push /code-check (class 2, DRY). After 2ab9510 (todo 1044),
`git_dash_c_path` (`hooks/push-gate.py:112`) repeats the `CHAIN_SPLIT_RE.split` +
`_tokenize_segment` + `_git_push_dash_c` loop that `resolve_push_target` (`hooks/push-gate.py:124`)
already runs, minus the `cd` fallback. `main()` calls only `resolve_push_target`; the sole caller of
`git_dash_c_path` is `hooks/test_push_gate.py:35`.

## Approach
Delete `git_dash_c_path` and point its test cases at `resolve_push_target` (or at
`_git_push_dash_c` directly), keeping every existing case's expectation.

## Acceptance
- `python hooks/test_push_gate.py` prints ALL PASS with the same case count.
- `grep -n git_dash_c_path hooks/` finds nothing.
