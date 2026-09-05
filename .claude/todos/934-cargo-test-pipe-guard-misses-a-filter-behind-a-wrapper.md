<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/908 introduced the command-position anchoring this regressed on, and done/780 is the original guard. Neither covers the wrapper-prefix gap the anchoring opened. -->
# cargo-test-pipe-guard misses a filter run behind env/nohup/time

**Type:** task
**Origin:** ai

## Goal

`cargo test | env FOO=BAR tail -40` is caught by the pipe guard, the same as `cargo test | tail -40`.

## Context

Found 2026-09-05 by an independent `/code-check` review of the `a915c22..HEAD` range, and verified
live rather than reasoned about.

Todo 908 changed `hooks/cargo-test-pipe-guard.py` from `PIPE_FILTER_RE.search(seg)` (match anywhere
in the segment) to `PIPE_FILTER_RE.match(_strip_leading_prefix(seg))` (must sit at the segment's own
start), so a filter word inside a quoted string stops tripping it. That was the right direction.

The gap it opened: `_strip_leading_prefix` strips only `sudo` and `VAR=value` assignments. It does
not strip the wrapper commands `env`, `time`, `nohup`, `nice`, `command` or `xargs`, which
`hooks/_destructive_guard_shared.py`'s `LEADING_WRAPPER_RE` already treats as a distinct concern.

The reviewer's receipt, both run against the current file:

    PIPE_FILTER_RE.search(' env FOO=BAR tail -40')                        -> True   (old behaviour)
    PIPE_FILTER_RE.match(_strip_leading_prefix(' env FOO=BAR tail -40'))  -> False  (now)

So `cargo test | env FOO=BAR tail -40` and `cargo test | nohup tail -f` now pass silently. This guard
exists because three prior incidents (hangs of 2h17m, 23min and 30min) went undetected exactly this
way, and a guard that stops catching something gives no signal that it has.

Severity is bounded: these are uncommon shapes, and the common `| tail`/`| head`/`| grep` forms are
still caught. It is a narrowed net, not a disabled guard.

## Approach

1. Read `hooks/cargo-test-pipe-guard.py`'s `_strip_leading_prefix` and
   `hooks/_destructive_guard_shared.py`'s `LEADING_WRAPPER_RE`.
2. Decide, and state which: share the wrapper list between the two (one definition, both callers),
   or keep them separate and widen `_strip_leading_prefix` locally. Sharing is tidier but couples a
   pipe guard to a destructive-command module; the reviewer flagged this as a real design call, not
   a mechanical fix, which is why it is filed rather than applied.
3. Whichever way, add test cases for `| env tail`, `| nohup tail` and a negative that must still
   pass (a filter word inside a quoted string).

## Acceptance

- `cargo test | env FOO=BAR tail -40` is blocked.
- The quoted-string false positive todo 908 fixed stays fixed. Prove it with the existing case, not
  by assertion.
- `python ci/run_all.py` passes.

## Notes

The sibling regression from the same todo-908 change, `flutter-workdir-guard.py` missing `fvm` and
PowerShell's `&` call operator, was fixed immediately in `b92d3d6` because it broke a hard-block
data-loss guard on this machine's primary invocation form. This one is filed instead because the
fix has a genuine design fork in it.
