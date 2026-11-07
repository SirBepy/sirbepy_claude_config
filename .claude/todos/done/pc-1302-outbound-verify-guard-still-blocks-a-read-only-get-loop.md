<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/pc-1151 covers the same symptom and was closed; this records that the symptom came back -->
# outbound-verify-guard still blocks a read-only Shortcut GET in a for-loop

**Type:** skill-improvement
**Origin:** ai
**Summary:** A read-only Shortcut GET in a shell loop was blocked as a write again on 2026-11-02, after pc-1151 was closed as fixed.

## Goal

A read-only `curl` GET against `api.app.shortcut.com/api/v3/stories/<id>` is never denied by `hooks/outbound-verify-guard.py`, including inside a `for` loop with a piped `python -c` reader.

## Context

- 2026-11-02, zng-app session e2bc79e9: this shape was denied with `[outbound-verify-guard] Shortcut REST write blocked: its text is not visible in the call`:
  `TOKEN=$(grep ... ~/.claude/.env | ...); for id in 56544 56585 ...; do curl -s -H "Shortcut-Token: $TOKEN" https://api.app.shortcut.com/api/v3/stories/$id | python -I -c "import sys,json; d=json.load(sys.stdin); ..."; done; curl -s ... /workflows | python ...`
  It has no `-X` and no `-d`.
- `done/pc-1151-outbound-verify-guard-blocks-read-only-shortcut-get-loop.md` describes the same symptom. UNVERIFIED which predicate fired this time: the guard's `is_http_write`, or a match on text in the piped Python such as `-c` or `.get(`. Feeding the command above to the guard settles it.
- Workaround used: a Python GET script in a scratch folder, which cost a Write and a separate call each time.

## Approach

1. Feed the exact command shape to the guard through its self-test harness and see which predicate returns true.
2. Limit the write check to curl's own argv, so a piped reader cannot trigger it.
3. Add a regression case for this shape, plus a positive case that a real `-X POST -d @file` in a loop is still gated.

## Acceptance

- The command above passes the guard.
- A POST with a body in a loop is still gated.
- The guard's self-tests pass.

## Notes

- Dead on 2026-11-07 /loop-todos triage: replaying the GET-loop shape through hooks/outbound-verify-guard.py exits 0; fixed by 2a8087a (2026-11-03), covered by hooks/test_outbound_verify_guard.py:42-49. Duplicate of done/1151.
