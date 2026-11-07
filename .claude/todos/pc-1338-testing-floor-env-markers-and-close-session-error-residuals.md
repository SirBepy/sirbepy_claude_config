<!-- Claim before executing: .claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1337 is the commit-guard tokenizer family, a different surface -->
# Testing-floor guard: environment-failure markers match echoed output, close_session counts on the tool_use alone

**Type:** task
**Origin:** ai
**Summary:** Two low-severity residuals from review-unpushed item 9 (lane F2) that were left out of the dont-test regex fix.

## Why

The 2026-11-07 review-unpushed pass flagged both as "also low". The item-9 regex fix (clause-start openers only) was done; these two need a design choice, so they were not forced into the same slice.

## Goal

Each payload below behaves as listed, with a regression test that is red before the fix.

## Context

- `hooks/_testing_floor_lib.py` `run_stack_check` (~609-613): `_ENVIRONMENT_FAILURE_MARKERS` (`0xc0000005`, `no space left on device`, `os error 112`, ...) match anywhere in the output of a non-zero run. A genuinely failing test that prints one of them (a test asserting on the string `no space left on device`, a fixture echoing `os error 112`) reads as "died from the environment; not verified" and the red check is waved through. Fix idea: take the marker only from the tail of the output, or only when no per-test failure line (`FAIL`, `failed`, `error[E`) also appears, or require the marker on a line that is not inside a captured test body.
- `hooks/testing-floor-guard.py` `closed_this_turn` / `turn_called_tool` (~119-133): the `close_session` exemption fires on the tool_use alone, even if the call errored (the session then did not close, but the gate stayed off). `iter_turn_tool_uses` in `hooks/_hooklib.py` yields only tool_use blocks, so a fix needs the matching tool_result (`is_error`) paired by `tool_use_id`.

- Lane F2 residuals found by the 2026-11-07 fresh reviews, not fixed: (a) `hooks/dev-server-guard.py` `_INTERPRETER_RE` is an allow-list of words that run a heredoc or here-string body, so an unlisted interpreter (`lua <<EOF\nnpm run dev\nEOF`) reads the body as data; a deny-list of known data sinks (cat/tee/git/Set-Content) would fail closed instead. (b) A 3000-fold repeated `echo $(` takes about 19 s through dev-server-guard (8.5 s before the nesting-limit raise), so a hook timeout shorter than that fails open; the cost is the quadratic tokenizing of one huge segment, not the substitution scan.

## Approach

Add the payloads to `hooks/test_testing_floor_guard.py` (the `environment_failure_checks` and `close_session_checks` groups), prove red with `skills/close/red-check.ps1`, then fix.

## Acceptance

- A non-zero run whose own failing test prints `no space left on device` still fails the floor; a genuine disk-full death (marker with no other failure line) is still "not verified".
- A turn whose `close_session` call returned an error does not exempt the gate.
