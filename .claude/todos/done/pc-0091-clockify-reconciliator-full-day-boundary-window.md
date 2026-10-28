<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=d2a6e1c5 -->
# clockify-reconciliator: git-log day windows must be true midnight-to-midnight + spillover check

**Type:** skill-improvement

## Goal

Fix `~/.claude-personal/skills/clockify-reconciliator/SKILL.md` Step 3 (Resolve window) / Step 6 (Read commits) so a single-day lookup (`yesterday`, `today`) can't silently clip a late-night session the way it did on 2026-07-28.

## Context

During the 2026-07-27 "yesterday" reconciliation, the git log window used was `--since="<day> 22:00" --until="<day+1> 22:00"` (local time) instead of true midnight-to-midnight. That cut off 2 hours early and missed a commit at 23:09 CEST, plus an entire follow-on session that ran to 01:11 CEST the next calendar day. Joe caught the gap by noticing his own commit history didn't match what got billed - Claude did not catch it.

This is a different failure mode than the one already covered in `feedback_verify_date_calculations.md` (computing the WRONG date for "Monday"/"yesterday"). Here the date itself was right, but the time-of-day boundary was wrong, and there was no check for a session spilling into the next calendar day.

## Approach

In `~/.claude-personal/skills/clockify-reconciliator/SKILL.md`:

- Step 3 (Resolve window): when lookback resolves to a single day (`today`, `yesterday`, or an explicit single `YYYY-MM-DD`), always compute the git-log bound as `<day> 00:00` to `<day+1> 00:00` local time - never a rounded/approximate cutoff like `22:00`.
- Step 6 (Read commits): after fetching commits for the target day, always run one more `git log` pass for the first ~4 hours of the NEXT calendar day (`<day+1> 00:00` to `<day+1> 04:00`) and flag any hits as "late-night spillover from <day>" so they get attributed to the right reconciliation, split across the midnight boundary per the pattern confirmed 2026-07-28 (real wall-clock minutes on each calendar day, not all dumped onto one day).
- Cross-link `feedback_verify_date_calculations.md` (which now documents both incidents) from the skill file itself, not just from memory, so a cold read of the skill carries the warning.

## Acceptance

- A "yesterday" run that has commits between 23:00 and 01:xx the next day surfaces ALL of them, not just the ones before an arbitrary early cutoff.
- The skill explicitly checks past-midnight spillover every time, not only when a human happens to notice a mismatch.

## Notes

Related: todo 32 (clockify-reconciliator memory-check-and-unlogged-day) covers a different set of gaps found the same day (billable flag default, overlap check, net-new-hours policy, project-from-cwd inference). This todo is scoped narrowly to the day-boundary/spillover bug only.
- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - true midnight window (SKILL.md:63) and the 4-hour spillover pass (SKILL.md:78-82) are both already implemented. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
