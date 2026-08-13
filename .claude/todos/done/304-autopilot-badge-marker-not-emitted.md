<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /autopilot never emitted its sidebar badge marker

**Type:** skill-improvement

## Goal

`/autopilot` ran a full task on 2026-07-31 without ever emitting `<cc-autopilot:on>`, so the sidebar badge never appeared and Joe had no visual signal the session was running unattended. `<cc-autopilot:off>` was emitted at the end, closing a badge that was never opened.

## Context

`~/.claude/skills/autopilot/SKILL.md` states the requirement twice: once in the "Sidebar badge" section, and again in "Order of operations" step 1, which even anticipates the failure with "do not rely on that section alone, this step is where it actually gets emitted."

It was still missed. The first response after activation opened with the completion-oracle line (also required by step 1) and went straight into tool calls; the marker was simply dropped. Being stated twice did not prevent it, which suggests the fix is structural rather than more emphasis.

## Approach

Restructure step 1 so the marker cannot be separated from the oracle, since both belong to the same first response. Options worth weighing:

- Make the required first-response output a single literal template block the skill can copy verbatim, oracle line and `<cc-autopilot:on>` together, rather than two separately-worded obligations in prose.
- Move the marker requirement into the same sentence as the oracle instead of a trailing "END THIS FIRST RESPONSE WITH" clause that reads as an aside.

Do not simply add a third restatement; two were already ignored.

## Acceptance

- The next `/autopilot` run emits `<cc-autopilot:on>` on its first response without special prompting.
- The skill file is not longer than before; this is a rewording, not an addition.

## Notes

- Relocated from `58` in `zng-admin` via /cleanup-todos 2026-08-13: it edits `~/.claude/skills/autopilot/SKILL.md`, a global skill file.
- Re-verified 2026-08-13: `SKILL.md:14-20` ("Sidebar badge") and `:92` (step 1, "END THIS FIRST RESPONSE WITH `<cc-autopilot:on>`") are still two separately-worded obligations; no single literal template block exists. Last edit to the file was `baea805` (2026-08-11), unrelated to this section.
- Done 2026-08-13. The marker obligation was stated twice in two different wordings, so neither read as mandatory. Now stated exactly once per marker, fused into the sentence of the step that fires it, with the Sidebar badge section demoted to documentation that explicitly says it is not a second instruction. skills/auto-do-todos/SKILL.md had the identical defect and got the identical fix. Net: both files are shorter than before.
