<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: remainder of pc-1332; pc-1297 is about pipes inside quotes for six other guards, not these two -->
# cargo-test-pipe-guard blocks a quoted grep pattern, and push-read-gate fires on gate chats

**Type:** task
**Origin:** ai
**Summary:** Two hook behaviours from the 0.2.146 release still cost retries: a `|cargo build` inside a quoted grep pattern, and a first-push read gate that a gate chat has no reason to trip.

## Goal
Neither block fires on a correct command during a release run.

## Context
Remainder of pc-1332 (its dev-server-guard and commit-trailer parts are done in 6dec5724).
- `hooks/cargo-test-pipe-guard.py` `find_violation` splits statements and segments on raw `;` and `|`, and its docstring says text inside a string is never preceded by a delimiter. A grep pattern like `"cache|cargo build|tauri build"` has `|cargo build` inside the quotes, so the guard read it as a piped cargo build and blocked a read-only grep (2026-11-06, claude_usage_in_taskbar). Masking quoted separators naively would stop it catching `bash -c "cargo test | tail"`, which `LEADING_WRAPPER_RE` handles on purpose, so the fix needs to keep scanning a `-c`/`-Command` argument.
- `hooks/push-read-gate.py` blocks a session's first `git push` until `snippets/auto-commit.md` is read, even in a gate chat or `/release` run whose push ask is quoted. Decide whether the gate-chat prompt should pre-read the file or the hook should accept the quoted ask.

## Approach
Mask separators inside quoted spans except when the span is the argument of a shell `-c`/`-Command` wrapper; add the grep-pattern case and the `bash -c` case to `hooks/test_cargo_test_pipe_guard.py`. For push-read-gate, pick one of the two options above and test it.

## Acceptance
`grep -E "a|cargo build|b" file` runs unblocked, `bash -c "cargo test | tail"` is still blocked, and a gate chat's first push is not stopped by the read gate.

## Notes

- cargo-test-pipe-guard now splits statements and pipes outside quotes only (plain-split fallback on unbalanced quotes) and scans a shell -c/-Command quoted argument recursively, so a quoted grep pattern naming cargo build passes and a piped cargo test inside bash -c is blocked (it was NOT blocked before). push-read-gate half, decided 2026-11-07: /gate-chat's spawn prompt now tells the child to read snippets/auto-commit.md before pushing. Tests: test_cargo_test_pipe_guard.py (quoted and -c cases, red on HEAD), test_push_read_gate.py gate-chat prompt assertion.
