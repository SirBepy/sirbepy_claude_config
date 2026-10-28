<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1179 is the verdict-line format inside template rounds, 1181 is batch poisoning plus the round cap; this one is ad-hoc "is this true?" rounds that never used the template at all -->
# Outbound verify: use the posting template from the first "is this true?" round on tracker-bound text

**Type:** skill-improvement
**Origin:** ai

## Goal

When Joe asks "ask 3 subagents if this is true" about a draft that will likely be posted to a tracker, the first round should already use the `refs/outbound-verify.md` template, so a passing round counts for `hooks/outbound-verify-guard.py` and no extra rounds are spent.

## Context

- zng-biller session, 2026-10-22: a reply to a dev's pushback on Shortcut sc-56481.
- Joe first asked to "ask 3 subagents if this is entirely true", then said "keep going until it doesn't fail", and later "post if 3 verifiers says it's good".
- Claude ran 4 rounds (12 verifiers) with an ad-hoc prompt. Round 4 passed 3/3, but the reports ended with "OVERALL: PASS", not the exact `OUTBOUND-VERDICT: PASS` line. So the guard would not count them, and 3 more formal rounds (9 verifiers) ran before posting.
- The ad-hoc rounds also lacked the template's ship-review step. That step caught real issues in the formal rounds: Won't Do announced on a story another dev owns, and a non-exhaustive "the other paths are" list.
- Data point for 1181's round cap: Joe's "keep going until it doesn't fail" again overrode the stop-after-round-2 rule. The third formal round passed 3/3.

## Approach

- `refs/outbound-verify.md`, Procedure step 2: add one line. Any verify request on text that is plausibly headed for a tracker or PR (a reply to a ticket comment, a ticket draft) uses this template from round 1, even when Joe has not yet said to post it.
- Optionally mention it in `skills/ticket/SKILL.md` where comment replies are drafted.

## Acceptance

- A cold session asked to "verify this ticket reply with 3 subagents" uses the template on round 1, and a 3/3 PASS round lets the post go through with no re-run.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): Procedure step 2 requires the OUTBOUND template and exact verdict line from round 1 for tracker- or PR-bound text. Optional ticket SKILL.md mention left out.
