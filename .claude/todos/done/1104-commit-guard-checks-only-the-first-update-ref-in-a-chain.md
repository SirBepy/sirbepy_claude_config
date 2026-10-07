<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=4f85e91e -->
<!-- duplicate-checked: 2026-10-06; 1085 (done) added the update-ref matcher this extends; no live todo covers chained calls. -->
# commit-guard inspects only the first `git update-ref` in a chained command

**Type:** task
**Origin:** ai

## Goal
A chained command whose second or later `git update-ref` moves a branch is gated on the session
marker exactly like a single call.

## Context
Found by the 2026-10-06 pre-push review of loop-todos cycle 2. `_is_branch_update_ref_invocation`
(`hooks/commit-guard.py:162`) calls `_subcommand_index(tokens, "update-ref")`, which returns the first
match only, so it judges just the first update-ref. The reviewer ran
`is_commit_landing_invocation("git update-ref refs/notes/x a && git update-ref refs/heads/master b")`
and got False: a false negative, since the second call lands a branch move. Low practical risk (only
a session with no marker, chaining a notes update first), but the gate exists to catch exactly this
shape. `git branch -f` and `git reset --soft` are also ungated, which predates 1085.

## Approach
Loop over every `update-ref` occurrence in the token list (or split the command on `&&`/`;`/`||`
first) and return True if any one targets `HEAD` or `refs/heads/*`. Add the reviewer's chained input
to `LANDING_CASES` in `hooks/test_commit_guard.py` as a must-gate case.

## Acceptance
- The chained input above returns True; the existing 9 LANDING_CASES still pass.
- `python hooks/test_commit_guard.py` passes.

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): _is_branch_update_ref_invocation loops over every update-ref via a start index on _subcommand_index; two chained cases added to LANDING_CASES.
