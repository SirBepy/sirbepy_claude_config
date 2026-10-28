<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1190 is timezone relabeling mid-reasoning, 1178 is /commit step 7a, 1016 and 1017 are done and about post-midnight placement and the step 4a memory read. None covers the step 6 transcript sweep's folder scope. done/1009 introduced the configured-repo sweep this extends. -->
# Clockify reconciliator: transcript sweep should also read non-project folders to rule out personal-project time

**Type:** skill-improvement
**Origin:** ai

## Goal

When `/clockify-reconciliator` sweeps AI chat transcripts for evidence (step 6), it also lists which OTHER Claude project folders were active in the same window, so a gap the dev remembers as "I was working the whole time" can be attributed to non-project work instead of being filled with the project's hours.

## Context

`skills/clockify-reconciliator/SKILL.md` step 6 limits the transcript sweep to `~/.claude-personal/projects/<sanitized-cwd>/*.jsonl` for each configured repo's cwd. On the Zirtue week of 2026-10-19 (run 2026-10-20) that scope showed Tue 17:07-18:04 as an empty gap, and the dev said he had no break 17:00-18:10. A scan of every folder under `~/.claude-personal/projects/` (a throwaway node script that groups message timestamps into windows split at 25-minute gaps) showed `claude-usage-in-taskbar` active 17:05-18:42 and `dashboard-a` active 17:33-17:56 on that day, both personal projects, while no zng chat was active between 17:07 and 18:04. Two read-only subagent checks that read the same folders both flagged the 17:05-18:10 block as unsupported, and the dev then chose the evidence-trimmed plan (Mon 5h40, Tue 4h30, written to Clockify) over the spread plan (Mon 6h20, Tue 6h). Without the all-folder view the first proposals would have written about 2h of Zirtue time that was personal-project time.

UNVERIFIED: that this recurs on most weeks. Would check by running the same all-folder scan on two earlier Zirtue weeks and comparing against their written entries.

## Approach

Add to step 6 (and mention in step 9's plan text) an "other active folders" pass: list every folder under `~/.claude-personal/projects/` that is not one of the configured repos, with its active windows inside the resolved window. Use it only as negative evidence (a stretch where only non-project folders were active is not project time), never as a reason to add hours. Keep it a script (the grouping logic is about 30 lines) rather than hand-reasoning, for the same reason the Audit mode text gives for scripting overlap checks. Rejected alternative: asking the dev to confirm every gap by memory, which is what produced the wrong 17:05-18:10 block here.

## Acceptance

- A run over the 2026-10-19 week prints the `claude-usage-in-taskbar` and `dashboard-a` windows for Tue 17:05-18:10 without the dev having to ask.
- Step 9's plan text names any proposed block that sits inside a window where only non-project folders were active.
- The pass reads the folders only, never writes, and never counts their time toward any total.

## Notes

- Related, already done: `done/1009-clockify-reconciliator-step-6-only-sees-committed-work-not-uncommitted-edits.md` introduced the configured-repo transcript sweep this extends.
- Completed 2026-10-23 (loop-todos cycle 1) in the clockify-reconciliator batch commit.
