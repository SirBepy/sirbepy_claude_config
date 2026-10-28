# Reconcile rate-it-and-commit's below-threshold flow with rate-it's own-turn rating rule

**Type:** skill-improvement

## Goal

Remove the contradiction between the two skills so a below-threshold rating never risks being swallowed by an AskUserQuestion picker, and the executing agent doesn't have to improvise.

## Context

`~/.claude-personal/skills/rate-it/SKILL.md` (post-incident, commit `e39e1c4`) mandates: deliver the rating as a complete text turn with NO tool call in that turn, because bundling AskUserQuestion with the rating text makes the host app's picker swallow the score. Its post-rating menu is explicitly "inline text - do not promote to an AskUserQuestion".

`~/.claude-personal/skills/rate-it-and-commit/SKILL.md` ("Below-threshold question" section) instructs the opposite: on score < threshold, "ask via AskUserQuestion" with 4 options.

Hit live on 2026-07-14 rating `skills/framer/` at 7/10: the agent resolved it by ending the turn on the rating with a plain-text next-move line (apply all / apply some / commit anyway / abandon), then acting on Joe's reply. That worked, but it's improvisation, not spec.

## Approach

Edit `rate-it-and-commit/SKILL.md`: replace the AskUserQuestion instruction in "Below-threshold question" with rate-it's two-turn pattern - turn 1 ends on the rating text plus a plain-text menu of the four options (keeping the conditional inclusion of "Accept suggestions" only when lifts reach threshold); turn 2, after Joe replies, may use AskUserQuestion for sub-choices (e.g. "apply some") since no rating text is at risk. Keep the existing option semantics unchanged.

Rejected alternative: changing rate-it to allow the picker again - that re-opens the original swallowed-score bug.

## Acceptance

- The two SKILL.md files give non-contradictory instructions for the below-threshold path.
- The rating text is always a complete turn with no tool call bundled.
- The four next-move options (accept-suggestions-if-lifts-reach-threshold / iterate / commit anyway / abandon) survive with the same meaning.

## Notes

Second live hit, 2026-07-17, rating `skills/mockup/SKILL.md` at 4/10: the agent called
`AskUserQuestion` with the score embedded directly in the question text (no preceding pure-text
turn), which timed out unanswered. Not proof the picker "swallowed" the score this time, but the
same bundling anti-pattern this todo describes - still unresolved, still worth fixing.

Third live hit, 2026-07-20/21, a full rate-it-and-commit sweep across 18 individually-committed
files (`.claude` dotfiles repo). For every below-threshold score, the agent again used rate-it's
own plain-text "Next move: apply all / apply some / ignore" line instead of the literal
AskUserQuestion 4-option template rate-it-and-commit specifies - consistently, across ~10
below-threshold ratings in one session, with no objection from Joe. One exception: for a 3/10
rating (`refs/design-principles-fibo-draft.md`, delete-vs-keep decision), the agent DID use
AskUserQuestion, because that specific case was a genuine judgment call needing Joe's input, not
a mechanical "apply the how-to-raise bullets" case - suggesting the real fix isn't "always use
plain text" but "use plain text for apply/iterate/abandon choices, AskUserQuestion only when the
choice itself needs Joe's judgment (e.g. delete vs. keep an ambiguous file)." Worth incorporating
into the Approach above rather than a blanket swap.

Fourth live hit, 2026-07-31, rating a batch of pending `.claude` skill changes at 7/10 (mechanical
"apply the how-to-raise bullets, then commit" case). Agent again used rate-it's own plain-text
next-move line instead of the AskUserQuestion template, consistent with hit 3's synthesized rule
(plain text for apply/iterate/abandon, AskUserQuestion reserved for a genuine judgment call). No
objection from Joe. Further corroboration that the Approach's refined rule, not a blanket swap, is
the right fix - still unimplemented.
- Duplicate of 245 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
