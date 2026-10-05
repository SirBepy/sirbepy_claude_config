<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 375 is the archived ground-check gate rollout, 911 is destructive-command-guard; neither covers outbound-verify-guard.py -->
# Split hooks/outbound-verify-guard.py: move the transcript tally into its own module

**Type:** task
**Origin:** ai

## Goal
`hooks/outbound-verify-guard.py` (556 lines at commit 79eeed6) holds two separable concerns. Move
the transcript-verdict tally into a sibling module so each half reads on its own.

## Context
Filed by `/code-check shas:79eeed6` (size check, class 2 structural).

- Outbound-call detection: `Outbound`, `collect_prose`, `regex_prose`, `prose_from_body`,
  `read_file`, `split_tokens`, `flag_values`, `gh_calls`, `detect_gh_pr`, `detect_gh_api`,
  `is_http_write`, `rest_prose`, `detect_rest`, `detect_shell`, `detect`.
- Transcript tally: `entry_strings`, `tool_result_text`, `load_verdicts`, `uncovered`, plus the
  `DRAFT_RE`/`VERDICT_RE`/`AGENT_MESSAGE_RE`/`TASK_NOTIFICATION_RE` constants and
  `REQUIRED_PASSES`.
- The `main()` entrypoint glues the two together.

This repo has no documented no-split policy and no `upstream` remote, so no exemption applies.
The existing `hooks/_destructive_guard_*.py` modules show this repo's naming for a guard's
private helper modules.

## Approach
Create `hooks/_outbound_verify_transcript.py` holding the tally half: `entry_strings`,
`tool_result_text`, `load_verdicts`, `uncovered`, and the four transcript regexes plus
`REQUIRED_PASSES`/`MIN_PROSE_CHARS`. Have `outbound-verify-guard.py` import from it inside a loud
try/except, using the same shape as its `_hooklib` import (exit 2 on import failure). Write the
new file in ONE Write call, since a half-written module the live guard imports blocks shell
access in every session. Then check that `ci/run_all.py`'s hook import smoke covers it, and keep
`hooks/test_outbound_verify_guard.py` importing through the guard module.

## Acceptance
- `python hooks/test_outbound_verify_guard.py` prints ALL PASS.
- `python ci/run_all.py` passes, including the hook import smoke.
- A live `echo gh pr comment 1 --body-file -` from Bash is still denied by the guard.

## Notes

- 2026-10-05: done in the pre-push sweep. Transcript tally moved to hooks/_outbound_verify_transcript.py (150 lines); the guard is 435 lines; same 48 test cases pass before and after.
