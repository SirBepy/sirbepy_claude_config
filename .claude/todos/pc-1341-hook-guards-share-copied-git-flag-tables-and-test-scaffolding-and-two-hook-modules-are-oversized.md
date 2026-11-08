<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep of backlog and done/ for VALUE_FLAGS, _hooklib split, test scaffolding found only pc-1111 (commit-window-guard tokenize, done) and pc-1297/1300 (quote splitting, done); none covers the flag tables or the test helpers. -->
# Hook guards copy the git global-flag table and test scaffolding instead of sharing them

**Type:** task
**Origin:** ai
**Summary:** Move the git value-flag table, the wrapper-body extraction and the repeated test helpers into shared modules so one fix reaches every guard.

## Goal

One owner for each duplicated piece in `hooks/`, so a flag added to one guard cannot be missed by its siblings.

## Context

From the push-gate `/code-check` over the 2026-11-07/08 range (hooks slices):

- `VALUE_FLAGS` (git global flags that take a value) is copied in `hooks/push-gate.py`, `push-read-gate.py`, `commit-guard.py`, `commit-window-guard.py:97`, `git-workdir-guard.py:53`, `list-peers-pre-edit-guard.py:80` and `agent-shared-tree-guard.py:61`. The range widened it in `push-read-gate.py` and `commit-guard.py` (`--config-env`, `--super-prefix`, `--attr-source`); `push-gate.py` was brought back in line in the gate run, but `commit-window-guard.py`, `git-workdir-guard.py`, `list-peers-pre-edit-guard.py` and `agent-shared-tree-guard.py` still carry the old set. Same failing shape as the push-gate bug: `git --attr-source HEAD -C <other> ...` hides the `-C`.
- `hooks/cargo-test-pipe-guard.py:159-181` (`WRAPPER_ARG_RE`, `EVAL_ARG_RE`, `_wrapper_arguments`) re-implements the `-c` / `-Command` wrapper-body extraction that `hooks/_hooklib.py` (`_INLINE_FLAG_RE`, `wrapper_command_bodies`, `nested_command_bodies`) now owns. Class 3: the regex scan and the token scan may differ on some inputs, and `test_cargo_test_pipe_guard.py` pins the regex behaviour.
- `hooks/push-gate.py:219` `all_pushes_upload_nothing` repeats the segment walk of `all_pushes_delete_only` (line 184); only the final predicate differs.
- `hooks/lessons-index.py:27` and `hooks/_memory_triggers.py:115` both resolve `CLAUDE_LESSONS_DIR` then `~/.claude/lessons`. `lessons-index.py` is deliberately stdlib-only and fail-open, so leaving it is acceptable.
- Tests: `test_deferred_tool_blind_call_guard.py:20-57` and `test_chat_title_guard.py:20-43` carry identical `make_transcript`, `run_hook` and tool-use helpers; `test_lessons.py`, `test_memory_trigger.py`, `test_gate_quoted_separators.py` and `test_outbound_window.py` hand-roll `case()`/`expect()` reporters instead of `_testlib.report`; `test_shortcut_create_guard.py:23` and `test_outbound_verify_guard.py:36` both define `py(body)`; `test_testing_floor_guard.py` defines `FakeProc` six times (lines 465, 511, 973, 1030, 1261, 1298).
- Size: `hooks/_hooklib.py` is about 930 lines, roughly 550 of them added by the range, mixing guard scaffolding with a self-contained shell parser (`join_line_continuations` through `without_display_segments`). `hooks/_memory_triggers.py` is about 610 lines mixing table compilation with per-call matching (weak seam).

## Approach

1. Put the git global value-flag set in `_hooklib.py` and import it in all seven guards; add a `DASH_C_CASES`-style test row per guard for one of the three new flags.
2. Move the repeated test helpers into `hooks/_testlib.py` (`make_transcript`, `run_hook`, `py`, a recorder, one `FakeProc`).
3. Optional, riskier: extract the shell parser from `_hooklib.py` into `hooks/_shellparse.py`. `_hookboot`'s SENTINELS and the last-statement sentinel need an entry for the new shared module, and the fail-closed behaviour of every guard must be re-proven (`python hooks/test_hookboot.py` plus every guard suite). Do this one alone, never in a batch.

## Acceptance

`python ci/run_all.py` green; `grep -n "VALUE_FLAGS = " hooks/*.py` shows one definition for the git flag set; each touched guard has a test that fails without its change.
