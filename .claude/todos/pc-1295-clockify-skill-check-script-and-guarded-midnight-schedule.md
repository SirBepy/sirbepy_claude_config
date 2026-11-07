<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hits (pc-0082, pc-0085, pc-0091) are closed todos about the skill's memory check, a Playwright orphan check and the day boundary window, not a pre-fire check script -->
# Clockify skill check script and a guarded midnight schedule

**Type:** task
**Origin:** dev
**Summary:** Give the clockify-reconciliator skill a check script that reports whether it already ran for a day, then recreate schedule 131dfa6a with that script as its pre-fire guard.

## Why
Joe (2026-10-30): the 23:55 weekday run opens a new chat, reads the skill, finds a marker file and stops, spending tokens and relying on Claude following a step. If the skill already ran for the day, even partially or cancelled, the midnight run should not run again. He wants it done by Conductor in a script, not as a Clockify special case, and explicitly not as an interim per-skill hack.

## Goal
The midnight Clockify schedule no longer opens a chat on a day the skill already ran.

## Context
Conductor's schedule feature now supports a pre-fire guard (claude_usage_in_taskbar commits f0b61645, 93cd311d, 4abad7c2; on master but not yet released as of 2026-10-30). A guard is a shell command stored on a schedule item. The daemon runs it in the item's project folder just before a firing would create its chat, with a 30 second timeout. Exit code 0 skips the firing and the first stdout line is shown in the Schedule panel as the skip reason. Any other exit code, a crash, a timeout or a missing command fires normally. The environment carries `CC_SCHEDULE_DATE` (local `YYYY-MM-DD` of the firing) and `CC_SCHEDULE_ID`. Windows runs it through `powershell -NoProfile -Command`.

The skill owns its markers, at `.runs/<project>/<YYYY-MM-DD>` inside `C:\Users\tecno\.claude\skills\clockify-reconciliator`. Conductor must not guess "already ran" from prompt text or chat history: a manual `yesterday` run must not suppress tonight's run, so only the skill's own marker for the firing's date counts.

## Approach
1. Read the skill's SKILL.md to find exactly how and when it writes `.runs/<project>/<date>` markers and what the project name is for the schedule's target folder.
2. Add a small script in the skill folder (for example `check-ran.py`) that reads `CC_SCHEDULE_DATE` (fall back to today's local date), looks for the marker for that date and project, and exits 0 printing `already ran for <date>` when one exists. Exit 1 with no output otherwise. It must never exit 0 on an error (fail open).
3. Recreate schedule 131dfa6a through the `schedule` MCP tool (`action: add`, `target: new_chat`, `repeat: weekdays`, same prompt, `guard: python C:\Users\tecno\.claude\skills\clockify-reconciliator\check-ran.py`). Joe approves the card showing the exact command. Cancel the old item once the new one is confirmed in the Schedule panel.
4. Keep the skill's own "read the marker and stop" step as a fallback.

## Acceptance
Run the check script by hand with a marker present and absent for today's date (exit 0 with the reason, exit 1 silently). The recreated schedule shows the shield in the Schedule panel and its drawer lists the command. The next midnight with a marker present shows a "Skipped: already ran for <date>" line instead of a new chat.
