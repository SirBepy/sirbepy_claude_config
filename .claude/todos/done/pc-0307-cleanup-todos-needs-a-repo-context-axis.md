<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=ba7d7ec8 -->
# /cleanup-todos scores intrinsic worth but never asks "should this be committed here at all"

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/cleanup-todos`'s Step 4 triage a repo-context dimension, so a backlog full of valid-but-cosmetic
refactors gets cut by the skill instead of by the dev afterwards.

## Context

Run on `zng-admin` (a CLIENT repo) on 2026-08-13. The skill's `worth` rubric graded 39 todos purely on
intrinsic merit and produced 27 keepers, nearly all `worth` 3-6 code-quality items: 5 file-splits, 6
dedupes, 2 dead-code nits, 1 defensive entity-adapter refactor.

Joe's immediate response: *"thing is, this is a project for a client, so i dont wanna do unnecessary
silly commits/changes. are we sure all of these should be done? lets narrow it down to stuff thats
actually necessary/helpful."* Re-triaging under that single question dropped 14 more todos in one pass
and took the backlog to 13.

The skill's own rubric text is the root cause. `3-4 = churn` is described in terms of the CHANGE
("restates a rule that exists elsewhere", "no enforcement path") and never in terms of the REPO the
change lands in. A behavior-neutral file split scores the same in a solo scratch project as in a
client repo other devs branch off, where it is several hundred lines of diff noise and a merge-conflict
magnet. `SKILL.md` mentions "client" zero times.

Note the skill ALSO already half-knows this: Step 6's item 4a says the low-worth roundup is "the list
the dev scans to decide what is worth their tokens" - i.e. it defers exactly this judgment to the dev,
which is what made the manual second pass necessary.

## Approach

Do NOT add a fourth verdict column - the CSV contract feeds `update-markers.ps1` and widening it
touches the diff gate. Prefer one of:

1. **Fold it into the `worth` rubric.** Add a sentence to the 3-4 and 1-2 tiers: a behavior-neutral
   change (file split, helper move, dead-code nit) in a repo with other contributors caps at 4,
   because the diff noise is a real cost the intrinsic score does not see. Cheapest, no schema change.
2. **Ask the triage subagent for repo context up front.** The dispatch prompt already states the repo;
   add "is this a shared/client repo?" to what the chunk agent is told, and instruct it to apply the
   cap above. Same effect, decided per-run rather than hardcoded.

Whichever is picked, the dev-facing framing that actually worked is worth stealing verbatim into the
rubric: **"is there a downside to keeping it as-is?"** If no concrete downside can be named, it is not
worth a commit. See the zng-admin memory `feedback_client_repo_change_bar` for the full incident.

## Acceptance

- A re-run of `/cleanup-todos` on a backlog of behavior-neutral refactors in a shared repo scores them
  at or below 4 without the dev having to say so.
- The `worth` rubric text names the repo-context factor explicitly.
- No change to the `file,complexity,worth,still_valid,relocate_dest` CSV contract or the Step 5 diff
  gate.

## Notes

- Completed via /auto-do-todos 2026-08-15: /cleanup-todos worth rubric 3-4 tier now caps behavior-neutral changes (file split, helper move, dead-code nit) at 4 when the repo origin remote sits outside the personal SirBepy account, reusing the gh-account-switch hook org signal so the check is detectable rather than vibes. No CSV column, no schema change, per the todo explicit rejection of one.
