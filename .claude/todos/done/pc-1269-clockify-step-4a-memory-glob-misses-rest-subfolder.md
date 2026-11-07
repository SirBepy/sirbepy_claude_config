<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped .claude/todos/ and done/ for rest/INDEX, memory/rest, feedback_clockify; pc-1017 (done) added the read-enforcement line, not the folder layout -->
# clockify-reconciliator step 4a globs only the memory dir root, but Clockify memories now live in `memory/rest/`

**Type:** skill-improvement
**Origin:** ai
**Summary:** Step 4a of the Clockify reconciliator finds every `feedback_clockify_*` / `reference_clockify_*` memory even after a memory cleanup moves them into a subfolder.

## Goal

`skills/clockify-reconciliator/SKILL.md` step 4a reliably reads every Clockify memory for the project, wherever the memory layout puts them.

## Context

Seen 2026-10-28/29 in the scheduled zng-app run (Zirtue, window Wed 2026-10-28). Step 4a says "Glob the project's memory dir for `feedback_clockify_*.md` and `reference_clockify_*.md`". A `/cleanup-memory` run on 2026-10-27 moved 257 memories of the zng-app project into `memory/rest/`, grouped by `rest/INDEX.md`, leaving only 24 in the root index. Both Clockify feedback memories (`feedback_clockify_dev_no_break_recall_vs_other_project_chats.md`, `feedback_clockify_no_late_night_entries_and_prefer_connected_chunks.md`) are now under `rest/`. A root-only glob (`cat feedback_clockify_*.md` in the memory dir) returned "No such file"; the run found them only because an `ls rest | grep clockify` happened to be in the same command. A run that globbed the root alone would have silently skipped the late-night and connected-chunks rules, the exact silent-skip failure pc-1017 was filed for.

## Approach

- In step 4a, change the glob to recursive (`**/feedback_clockify_*.md`, `**/reference_clockify_*.md`) under the memory dir, and say that `rest/` (or any subfolder) counts.
- Optionally mention `rest/INDEX.md`'s Clockify section as the place to cross-check the hit list.
- Check the same assumption elsewhere in the skill (`modes.md`, `hubstaff.md`) for any root-only memory path.

## Acceptance

- Step 4a's wording finds files in `memory/rest/` with no manual `ls` of the subfolder.
- Re-reading the step cold, a run in zng-app would list both Clockify feedback files above.

## Notes

- Step 4a now globs **/ and cross-checks rest/INDEX.md; modes.md and hubstaff.md have no root-only memory path. Prose-only change, no script test.
