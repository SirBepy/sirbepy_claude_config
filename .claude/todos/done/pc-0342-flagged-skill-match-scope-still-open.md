<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# flagged-skill-mention still matches first_line only, and nobody has decided whether that is right

**Type:** skill-improvement
**Origin:** dev

## Goal

Settle the match-scope question that todo 332 raised and deliberately left open, so
`hooks/flagged-skill-mention.py` stops matching on a rule nobody has actually chosen.

## Context

Todo 332 had two halves. The narrow half shipped 2026-08-15: the hook now strips zero-width
characters and skips any prompt whose normalized start is a run of bracketed `[tag]` groups, so
machine-injected peer, daemon and task-notification envelopes no longer trigger a SKILL.md
injection. That was verified by reproducing the original failure (19126 bytes of `close/SKILL.md`
injected into an unrelated session) and showing it gone, while a genuine typed `/close` still fires.

The wider half was excluded on purpose and is this todo. The hook still matches only against
`first_line` (`hooks/flagged-skill-mention.py`, the `first_line` variable). Nobody has decided
whether that is correct:

- **Narrower or unchanged** means a real `/skill` invocation Joe types on line three of a longer
  prompt never fires.
- **Wider (whole prompt)** means a skill name quoted inside a pasted log, a diff, or a code block
  fires an injection that was never an invocation.

This repo's hook doctrine (see `.claude/todos/PLAN.md`) is the relevant constraint: exact mechanical
checks ship, heuristic judgment calls do not. Three detectors were killed in one day on that basis.
Whichever scope wins has to be mechanical.

There is also a named, already-accepted tradeoff from the narrow fix: a prompt Joe himself types
that happens to open with `[bracket text]` reads as an envelope and is skipped. That was accepted
knowingly, and it interacts with any scope change, so decide them together.

## Approach

This is a decision first and an edit second. Do not widen the scope without evidence.

1. Measure before deciding, per the doctrine. Sample real prompts from this machine's session
   transcripts and count, for each candidate scope: how many genuine `/skill` invocations it would
   catch, and how many quoted-in-a-log mentions it would falsely fire on. The bare-question and
   command-chaining detectors were both killed by exactly this kind of measurement, so the corpus
   exists and the method is established.
2. Only then pick a scope, and state the measured false-positive rate in the hook's own comments.
3. Extend `hooks/test_flagged_skill_mention.py`, which already covers seven cases including the
   bracket tradeoff.

An acceptable outcome is "keep `first_line`, now with the measurement recorded so nobody reopens
this". That is a real answer, not a non-answer.

## Acceptance

- The chosen scope is backed by a count against real prompts, not an argument.
- `hooks/test_flagged_skill_mention.py` covers the decided behaviour, and all hook suites pass.
- A genuine typed `/close` still fires; a peer envelope still does not.

## Notes

- Done 2026-08-16, commit aaeb1ca. Settled by measurement over 2574 real transcripts, 7128 Joe-typed prompts, 509 mentioning a flagged skill. first_line caught 300/493 true invocations with 0 false positives. whole_prompt caught all 493 but also all 16 false positives AND fired inside all 131 task-notification/auq-answer bodies, empirically reproducing the exact 19KB injection bug todo 332 fixed, so it is disqualified. first_line_or_explicit_slash_anywhere caught 374/493 with 0 false positives and 0 synthetic-body fires, so it won. The 119 remaining mid-sentence cases need semantic judgment and were deliberately left as a documented gap. Measurement written up in hooks/flagged-skill-mention.md.
