<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=5, reconfirm-count=3, content-hash=de55cbd4 -->
<!-- duplicate-checked -->
# destructive-command-guard.py carries its own ask() instead of _hooklib's

**Type:** skill-improvement
**Origin:** ai

## Goal

Collapse `hooks/destructive-command-guard.py`'s local `ask()` emitter into `_hooklib.ask()`, so the
`permissionDecision: "ask"` wire format lives in exactly one place.

## Context

Filed 2026-08-21 by phase 2 of the harvest plan, which created the duplication on purpose and said
so in the code. Todos 419 and 420 were built by two builders **in parallel**, and both needed to emit
an `ask` decision. 420 owned `_hooklib.py`, so 419 was told not to touch it and to write a local
emitter instead. `hooks/destructive-command-guard.py`'s own docstring records the debt:

> The MIDDLE "ask" JSON emitter is written locally, not in _hooklib, because another builder is
> adding _hooklib.ask() in parallel; collapse into that in a later pass.

`_hooklib.ask(reason)` now exists (added in `ec6334d`) and does the same thing: prints the
`hookSpecificOutput` JSON to stdout and exits 0. Two guards therefore hold the same wire format.

Why it is worth fixing rather than shrugging at: the exit-0-plus-stdout contract is the part that is
easy to get wrong, and one of the harvest reference implementations got it wrong in exactly this way
(`poshan0126/dotclaude/hooks/scan-secrets.sh` emits the `ask` JSON and then exits 2, which makes the
JSON unread). A second copy is a second chance to drift into that bug.

## Approach

1. Import `ask` from `_hooklib` alongside the existing `deny`, matching how
   `hooks/secret-write-guard.py` already does it.
2. Delete the local `ask()` and keep the `OVERRIDE_HINT` suffix behaviour: the local version appends
   the bypass hint to the reason, so the call site must do that, not the helper.
3. Delete the docstring paragraph quoted above, since it stops being true.
4. `python hooks/test_destructive_command_guard.py` must still pass unchanged. It already asserts the
   wire format (a MIDDLE hit exits 0 with valid JSON whose `permissionDecision` is `ask`), so the
   existing tests are the proof, and no new test is needed.

## Acceptance

- `hooks/destructive-command-guard.py` defines no `ask()` of its own.
- The bypass hint still appears in a MIDDLE ask reason, verified by running the guard on
  `git reset --hard master` and reading the emitted JSON.
- `python ci/run_all.py` exits 0.

## Notes

Do not also move `deny()`'s prefix handling or refactor anything else in the file while there. The
whole change is one import and one deletion.
