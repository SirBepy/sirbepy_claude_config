<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=9, reconfirm-count=1, content-hash=f8697337 -->
<!-- duplicate-checked: hits 259 (mega-todos final barrier) and 421 (rate-it panel lens isolation) are different surfaces; this one is refs/outbound-verify.md's verifier prompt -->
# Outbound verify: add a "ship review" lens for fields, batch consistency and ambiguity

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `refs/outbound-verify.md`'s 3-verifier round also catch the non-factual mistakes that make a
posting look sloppy, not only false claims.

## Context

zng-admin session, 2026-10-05/06. A batch of 5 Shortcut writes (3 FE comments, 1 new BE ticket, 1
link) passed the standard outbound-verify prompt **3/3 PASS**. Joe then asked for 3 more
reviewers framed as "a skeptical teammate, don't let me look like an idiot". All 3 of those
returned CHANGES-NEEDED, with 3 real problems the fact-check prompt is structurally blind to:

1. **Ticket metadata, not prose.** The planned create named "ENG - Core Workflow" as the team. That is
   the workflow name; the team is the group "ZNG ENG TEAM" (`6880fd7c-...`). The fact-check prompt
   only lists claims *in the text*, so fields sent alongside the text (group, epic, custom fields,
   owner) are never checked.
2. **Batch inconsistency.** Two of three "waiting on BE" comments linked their blocking ticket and
   the third didn't. Every comment was individually true.
3. **Ambiguous antecedent.** "Per the description, this needs a PM check" sat right after a link to
   a different ticket, so a reader could take it as that ticket's description. The claim itself was
   true.

After the fixes, the round-2 ship review passed 3/3 and the batch was posted.

## Approach

In `refs/outbound-verify.md`'s verifier prompt template (step 2), add a second section after the
claim list:

- Judge the planned non-text fields of the call (team/group, epic, owner, custom fields, state
  moves, links) against the tracker's real values and the nearest precedent ticket.
- For a batch, check that the items are consistent with each other.
- Flag wording a teammate could misread, even when it is factually true.
- Any such finding is a FAIL, the same as a WRONG claim.

The prompt also needs one line of provenance (who asked, what the posting descends from). Per
zng-admin memory `feedback_give_reviewers_the_why`, reviewers without provenance flag sanctioned
work as rogue.

Keep `hooks/outbound-verify-guard.py` unchanged: it already keys on the verdict line, so this is a
prompt-only change.

## Acceptance

- `refs/outbound-verify.md`'s template contains the fields/consistency/ambiguity section.
- A dry run on a draft whose planned team name is wrong returns FAIL.

## Notes

- Cost: each extra round is ~3 x 100-140k subagent tokens. Folding the lens into the existing
  round, instead of a separate second round, is what saves the spend.
- Folded in from zng-app, 2026-10-06/07 (sc-56167): **causal conclusions also slip through as
  "not a claim".** A comment to Johanna said "so the app is sending them, they're getting dropped
  or hidden somewhere on the amplitude side". All 3 verifiers confirmed the code facts, then
  skipped that line as "a deduction from facts 1-3, not an independent claim", so it passed 3/3.
  Her Raw-payload reply the same evening showed nothing was blocked or hidden in Amplitude, so the
  conclusion was unproven and is now under re-investigation. Add to the template: a "so X" / "X is
  happening because Y" line is a factual claim about the system and needs its own receipt. If the
  only support is the other claims, mark it UNVERIFIABLE, which fails the round. That forces the
  draft to hedge it ("looks like it's getting dropped after the app, can you check...").
- Completed 2026-10-08 (loop-todos cycle 1): outbound-verify.md verifier template gains a provenance line, causal-claim handling, and a Ship review step (non-text fields vs tracker reality, batch consistency, ambiguous wording; any finding fails). Dry run against a live wrong-team draft not run (no staged tracker draft); verified by inspection.
