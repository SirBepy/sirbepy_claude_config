<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=8d01fda9 -->
# /mockup: reconcile the 2-3 variant cap with "show me all the variants"

**Type:** skill-improvement

## Goal

Give `/mockup` a rule that survives the dev explicitly asking for every variant at once, instead of a
flat cap that has to be broken to satisfy him.

## Context

`C:\Users\tecno\.claude-fibo\skills\mockup\SKILL.md`, Staging section, says: "Labeled side-by-side
sections when comparing options ... Cap it at 2-3 options shown at once; a dense multi-variant grid
shrinks everything below legibility (a past incident with an 8-variant board drew 'i cant see anything
properly')."

On 2026-07-29 Joe asked for the opposite in as many words: "give me a /mockup of all the variants we
just mentioned ... i wanna see all the possible mockups you could have thought of." Six were built and
shown, and he judged them fine. The cap was broken deliberately and nothing went wrong.

The reason it worked is the thing the rule should actually say: the original incident was about
**scale**, not **count**. Eight variants failed because they were shrunk to fit one screen. Six
variants worked because each sheet was drawn at its true target width (390px) in a 3-across grid, so
nothing was scaled down and each one was individually legible. The board then needed two screenshots
to capture, one per row.

## Approach

1. Rewrite the cap in the Staging section as a legibility rule rather than a number: every variant
   renders at its real target size, never scaled to fit the board. If they no longer fit one viewport,
   that is fine, capture the board in sections (anchor ids plus URL fragments, see memory
   `screenshot-helper-flags`).
2. Keep a soft default of 2-3 for the case where the dev has NOT asked for breadth, since narrowing
   the field is usually the more useful service.
3. State the exception explicitly: when the dev asks for all variants, show all of them, at true size,
   and say how many there are up front.
4. While in that file, note that a per-variant one-line tradeoff caption under each stage is what makes
   a wide board usable, since it lets him compare without re-deriving each option's cost.

## Acceptance

- The skill no longer contains a bare numeric cap that an explicit "show me all of them" has to
  violate.
- The legibility requirement (true target size, no scaling) is the operative rule.
- The multi-shot capture technique is mentioned so a future session does not silently crop the board,
  which happened on the first attempt this session.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 178; renumbered to 35 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: rewrote the Staging bullet (`skills/mockup/SKILL.md:57-59`) as one coherent legibility rule - true target size, never scaled to fit, 2-3 soft default, "show me all" honored at true size with count stated up front, multi-shot capture via anchor ids/URL fragments, plus the per-variant tradeoff caption. No duplicate rule left.
