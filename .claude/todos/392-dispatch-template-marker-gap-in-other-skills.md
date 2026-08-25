<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Sweep every skill that embeds a dispatch template for the three-marker gap

**Type:** skill-improvement
**Origin:** ai

## Goal

Find and fix every remaining skill whose embedded Agent-dispatch template is missing one of the
three markers `hooks/dispatch-preamble-guard.py` hard-requires, so those skills stop being rejected
on their first dispatch.

## Context

Todo 373 fixed exactly two of these on 2026-08-19: `skills/rate-it/panel.md` and
`skills/autopilot/SKILL.md`. Todo 364 fixed a third, `skills/mega-todos/SKILL.md`'s injected commit
block. Both were scoped to their own files by lane ownership, and 373's Approach step 4 explicitly
asked for a wider sweep that neither could perform.

The hook requires three literal substrings (`hooks/dispatch-preamble-guard.py:36-44`):

- `Stage your changes but do NOT commit` OR `Leave all changes unstaged`
- both `run_in_background` and `FORBIDDEN`
- `.for_bepy/screenshots/` OR the `READ-ONLY DISPATCH` opt-out

A template missing any one of them produces a dispatch the harness refuses, and the failure surfaces
as a confusing hook error rather than as "this skill's template is stale".

Candidates named by 373 but not checked: `skills/iterate-it/`, `skills/delegate/`,
`skills/auto-do-todos/`, `skills/code-check/`. There may be others.

Confirmed hit 2026-08-24: `skills/disk-doctor/windows.md`'s "How to run a scan" section instructs
dispatching the scan to a `general-purpose` subagent but includes none of the three markers. A live
`/disk-doctor` session hit two straight hook rejections before hand-assembling a passing preamble.

## Approach

1. Grep the whole `skills/` tree for text that reads as a dispatch template (a prompt block passed
   to the Agent tool, a "Dispatch" heading, a "dispatch prompt" section).
2. For each hit, check it against the three markers above, mechanically, not by eye.
3. Fix by POINTING at `refs/builder-preamble.md` as the paste source rather than retyping the block,
   which is the whole reason that file exists. Hand-copied blocks are what drifted in the first
   place.
4. Do NOT modify `hooks/dispatch-preamble-guard.py`. The hook is correct; the templates are wrong.
   This was already settled for 364 and 373.

## Acceptance

- Every dispatch template in `skills/` either carries all three markers or points at
  `refs/builder-preamble.md` for them.
- A grep for the three marker strings across `skills/` shows no template missing one.
- The guard hook is unchanged.

## Notes

- Surfaced as an out-of-scope finding by todo 373's builder during the 2026-08-19 mega-todos run.
