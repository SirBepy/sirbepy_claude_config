<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=5, reconfirm-count=1, content-hash=9b3cea37 -->
# clockify-reconciliator has no supported path for a day with zero Clockify entries

**Type:** skill-improvement
**Origin:** ai

## Goal

Let `/clockify-reconciliator` handle a day that has real git commits but zero Clockify entries at
all (not "empty description" - no entries exist), instead of just refusing.

## Context

Skill file: `~/.claude/skills/clockify-reconciliator/SKILL.md`. Its rule ("Never create entries in
empty time ranges. Only operate on existing entries (splits allowed)") assumes every day needing
reconciliation already has at least one entry to anchor start/end times to and fill/split.

Hit this 2026-08-07 (zng-app session) reconciling Zirtue's Thursday 2026-08-06: 9 real commits
across zng-app/zng-admin/zng-biller, zero Clockify entries for the day in any project. The skill
had nothing to do per its own rules. The dev explicitly asked to create entries anyway ("lets add
the entries"), which is out of scope for the current skill text.

Also relevant: when I asked the dev what Thursday's actual start/end clock times were (since there
was no entry to anchor to), he pushed back - "you usually figure that out from commits, idk why
youre asking this". See [[feedback_clockify_no_billable_flag_no_overlap]] (updated 2026-08-07) for
the inference method that worked and was approved.

## Approach

Add a step (before or replacing the current step 5 "Identify targets" for days with zero in-project
entries):

1. If a day in the window has commits but zero Clockify entries (in-project or other-project),
   don't skip it - build a from-scratch proposal instead of only targeting existing empty-description
   entries.
2. Infer the day's full start/end and chunk boundaries purely from commit timestamps: find the
   multi-hour gaps between consecutive commits across all repos that day, bucket commits into
   clusters by those gaps, set the first chunk's start ~2h before the first commit cluster (this
   2h lead-time was calibrated against 2026-08-05's actual entries, where the first logged entry's
   start preceded its anchoring commit by ~2h), and the last chunk's end shortly (~5-15 min,
   rounded to nearest 5-min mark) after the last commit.
3. Never ask the dev for start/end times in this path - infer and present in the step 9 plan for
   approval like normal, same as any other proposal.
4. Chunk sizing/description/ticket-suffix rules are unchanged from the existing step 7 - this only
   adds a way to get chunk boundaries when there's no existing entry duration to split.
5. Reverted-same-day commits (a commit whose subject is a `Revert "..."` of another commit in the
   same window) should not get their own description credit - fold the time into the chunk but
   don't describe shipped work that didn't ship. (Applied ad hoc 2026-08-07 for a `54854` commit
   that was pushed then reverted the same evening; wasn't a written rule anywhere.)

## Acceptance

- A day with commits but zero existing entries produces a proposal table in step 9, not a silent
  skip or a blocking question about clock times.
- Existing behavior (splitting/filling entries that already exist) is unchanged.
- The "day has zero commits at all" ask-first rule in step 7 is untouched - that's a different
  case (no source data at all) from this one (commits exist, entries don't).

## Notes

Two live examples of the inference method + revert-handling, both approved by the dev, are in the
2026-08-07 zng-app session transcript if a starting point for exact wording is useful.

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add the zero-entry-day fallback, whose 5 steps the Approach already fully
  specifies, to `clockify-reconciliator/SKILL.md` near its "never create entries in empty time
  ranges" rule. Important: this is a strict subset of todo 34's mandatory gap-detection step, so if
  34 lands first this todo is superseded, do not duplicate it. This was produced by a strict
  second-pass re-triage that specifically asked whether a defensible answer exists without the dev;
  it concluded yes. Not executed only because the session ended.
- Strict subset of 34 (full-month clockify audit/reconstruction mode), which supersedes it. Merged during /cleanup-todos 2026-08-12. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
