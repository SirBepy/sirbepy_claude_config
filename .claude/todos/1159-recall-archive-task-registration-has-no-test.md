<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; 1158 is recall.py's archive-half split, not the scheduled-task script -->
# recall's `register-archive-task.ps1` ships with no test and no stated reason

**Type:** task
**Origin:** ai

## Goal

Either a test proves `skills/recall/register-archive-task.ps1` registers the monthly transcript-archive task correctly, or the reason it cannot be tested is written down where the testing floor asks for it.

## Context

Found by the pre-push `/code-check` on 2026-10-08 (range 009b69f..e7263e8). Commit 25471a1 added the script, which registers a Windows scheduled task. It has no sibling test and the commit message gives no reason, which `CLAUDE.md`'s testing floor requires ("one Claude cannot test says why in the commit report").

Also UNVERIFIED, from the same review: the task is registered without an explicit `-User`/`-Principal`, so it most likely runs only while Joe is logged on. Would check with `Get-ScheduledTask` after registering. That may be the intended behaviour (`refs/permanent-memory.md` describes it as StartWhenAvailable), but nothing confirms it.

## Approach

Add a `test_register_archive_task.ps1` (or a case in `skills/recall/test_recall.py`) that registers the task under a throwaway name, asserts its trigger, action and logon type via `Get-ScheduledTask`, then unregisters it. If that is judged too invasive, add one line to the script's header stating why it stays untested and what was checked by hand.

## Acceptance

- A test registers, verifies and removes a throwaway task, or the script's header states why it is untested.
- The task's logon type is known and matches what `refs/permanent-memory.md` describes.
