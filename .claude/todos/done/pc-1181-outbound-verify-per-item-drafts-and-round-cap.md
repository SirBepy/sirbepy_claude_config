<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1179 is the verdict-line format, done/1110 added the ship-review lens; this one is batch poisoning across separate comments plus the round cap -->
# outbound-verify: verify each posting as its own draft, and let Joe raise the round cap

**Type:** skill-improvement
**Origin:** ai

## Goal

Posting several ticket comments in one go should not need 6 verifier rounds. One FAIL on one comment should not lock the others, and the procedure should honor Joe's stated preference for more autofix rounds before handing back.

## Context

2026-10-15, zng-app session answering a PM's blocked-ticket follow-ups (sc-52123, sc-56142, sc-56215). Three Shortcut comments were verified as ONE batch draft per `refs/outbound-verify.md` "One draft can cover a batch". 18 verifier subagents (6 rounds of 3) ran before all three posted (comments 56380-56382). What drove the count:

- **Batch poisoning.** Every round that failed did so on a single comment, yet the FAIL poisoned the exact text of all three, because the hook (`hooks/outbound-verify-guard.py` + `_outbound_verify_transcript.py`) clears a field only if it sits inside a draft with 3 PASS and 0 FAIL. Twice, comments with zero objections had to be re-verified only because a sibling in the same batch failed.
- **Cross-comment pointers.** One comment said "see my comment there" about a sibling that was not posted yet. Two verifiers correctly failed it as a dangling pointer. Batch comments that reference each other depend on posting order, which the verifier cannot see.
- **Round cap.** The procedure says "Any FAIL, round 2: stop... Do not start a round 3" (`refs/outbound-verify.md`, step 3). Joe overrode this in the session: "keep doing rounds until you reach 7 rounds or you find a round where nobody disagrees, ofc, autofix on these rounds". With that cap, the next two rounds converged (one real fix: PR attribution `#238` vs `#233`, confirmed via `git show 423546ac^1:apps/core/src/modules/users/users.controller.ts`).

Each round also re-pastes the full ~60-line verifier prompt 3 times inline; that is the repeated manual step here.

## Approach

1. In `refs/outbound-verify.md`, replace "One draft can cover a batch" guidance with: verify each independent posting (each comment) as its own draft, dispatching its 3 verifiers in the same message as the others, so a FAIL only blocks the text it is about. Keep batching only for fields of ONE posting (title + description).
2. Add a drafting rule: comments in one batch must be self-contained, with no "see my comment on X" pointers to unposted siblings.
3. Raise or make configurable the round cap. Joe's stated preference (2026-10-15): up to 7 autofix rounds, stopping early on a clean round. Decide whether that becomes the default or an opt-in phrase; ask Joe if unclear.
4. Optional: a small helper that renders the verifier prompt from (repo pointers, provenance, draft) so the main session does not hand-paste it 3x per round.

## Acceptance

- Re-running a 3-comment posting where one comment fails re-verifies only that comment.
- `refs/outbound-verify.md` states the round cap that matches Joe's preference.
- The hook's exact-match / 3-PASS / 0-FAIL guarantees are unchanged for each individual text.

## Notes

Related, separate: 1151 (guard blocks read-only GET loops; reproduced again this session with a `for id ...; curl -o` loop), 1179 (verdict-line prefix exact match).

2026-10-15, revaire-mobile PR #1151 (one PR title+body, not a batch): 7 rounds, about 21 verifier dispatches at 10-20 min each. Every round confirmed all facts. Each FAIL was a new nit the earlier rounds hadn't raised (a Windows caveat, a README badge, a doc mention). One FAIL was the verifier's own error: it read `riverpod`'s scheduler instead of `flutter_riverpod`'s `ProviderScope._flutterVsync`. Its WRONG verdict still poisoned correct text and forced a reword plus another round. Two ideas worth weighing:
- a FAIL whose receipt the orchestrator disproves at file:line should not poison the text;
- verifiers could get the prior rounds' resolved findings so they stop re-raising settled points.
- Completed 2026-10-23 (loop-todos cycle 1): one draft per independent posting, no cross-comment pointers, 7-round opt-in cap with the 2-round default kept; a disproved FAIL still needs changed text because the hook counts it. Optional prompt-renderer helper not built.
