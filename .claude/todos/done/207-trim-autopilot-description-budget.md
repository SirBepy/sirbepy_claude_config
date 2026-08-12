<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=5, reconfirm-count=2, content-hash=61481ce9 -->
# Trim autopilot's SKILL.md description to the ~120-char budget

**Type:** task

## Goal

`skills/autopilot/SKILL.md` frontmatter description is 262 chars / 39 words - over the
description budget (~25 words / 120 chars) that loads into every session's system prompt.

## Context

Flagged by the 2026-07-15 /rate-it pass on the plan-layer work (which trimmed the four
descriptions that work touched, but autopilot's predates it and was out of scope). The budget
gate lives in `bepy-skill-creator/SKILL.md` and `code-check/SKILL.md` Step 0. Current text
packs trigger keywords (AFK, never block, delegate, iterate-it, auto-answer, blockers, grind).

## Approach

Rewrite the description keeping every trigger-bearing keyword ("/autopilot", AFK/autonomous
intent) and cutting restated mechanics (the how lives in the body). If it genuinely cannot reach
budget without dropping a trigger keyword, keep it over and note which keyword forced it - per
the gate's own exemption clause.

## Acceptance

- Description <= ~120 chars, or an explicit exemption note naming the protected keyword.
- `/autopilot` still triggers on the same phrasings (spot-check the description against its
  current when-to-use intent).

## Notes

- Dropped via /auto-do-todos 2026-08-12: not applicable. skills/autopilot/SKILL.md:4 sets disable-model-invocation: true, so the skill never loads into the model skill listing and the description-length budget this todo targets does not apply to it.
