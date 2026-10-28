<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /auto-do-todos names only 1 of the 3 markers its own dispatch guard requires

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/auto-do-todos` runs from having their first builder dispatches rejected by
`hooks/dispatch-preamble-guard.py`, by naming `refs/builder-preamble.md` where the skill already
lists what a dispatch must carry.

## Context

Hit 2026-08-19 during a `/auto-do-todos` run in the `hubbub` repo. Two builder dispatches were
written and both were rejected outright by the guard:

> [dispatch-preamble-guard] Dispatch prompt is missing required preamble marker(s):
> run_in_background ... FORBIDDEN line; .for_bepy/screenshots/ id line (or the READ-ONLY DISPATCH
> opt-out). Paste the canonical block from refs/builder-preamble.md before dispatching.

**The gap is a specific, checkable omission, not carelessness.** `skills/auto-do-todos/SKILL.md`'s
"Adopted contracts (referenced, not restated)" section reads:

> `~/.claude/refs/delegation-doctrine.md` in full - 90/10 rule, scout spec packs, the verbatim
> stage-don't-commit line in every dispatch, orchestrator hygiene, report quality tells.

That enumerates exactly ONE of the three literal substrings the guard enforces (the
stage-don't-commit line). It never names `refs/builder-preamble.md`, and never mentions the other
two markers:

1. `run_in_background` AND `FORBIDDEN` both present.
2. `.for_bepy/screenshots/` OR the literal line `READ-ONLY DISPATCH`.

`refs/builder-preamble.md`'s own "What the guard actually enforces" section documents all three and
states plainly that it is "a pure string check, not a semantic one, so pasting the block above
verbatim is what makes a dispatch pass, not merely following its intent". A run that follows
`/auto-do-todos` literally therefore satisfies 1 of 3 and gets blocked.

Cost is bounded but repeats every run: two fully-written dispatch prompts discarded, then a read of
`builder-preamble.md` and a rewrite. The guard's error message does name the file, so recovery is
fast - this is a wasted-work problem, not a correctness one.

## Approach

- In `skills/auto-do-todos/SKILL.md`'s "Adopted contracts" section, add `~/.claude/refs/builder-preamble.md`
  as an explicitly named contract, noting it is the literal paste source and that
  `hooks/dispatch-preamble-guard.py` string-checks three markers, not one. Keep it a reference, not
  a restatement - that section's whole point is not restating adopted contracts, and duplicating the
  block here would be a second copy to drift.
- Check whether `/delegate` and `/autopilot` have the same omission. Both adopt
  `delegation-doctrine.md` the same way, so the same first-dispatch rejection likely applies to them
  too; fix them in the same pass if so.
- Consider whether `delegation-doctrine.md`'s own "Canonical builder preamble" section should name
  all three enforced markers inline, since that is the file `/auto-do-todos` actually points at.

## Acceptance

- A cold session following `/auto-do-todos` (or `/delegate` / `/autopilot`) reaches
  `refs/builder-preamble.md` BEFORE writing its first dispatch, not after a guard rejection.
- No skill restates the preamble block itself - the paste source stays the single copy.

## Notes

Do NOT weaken or bypass `hooks/dispatch-preamble-guard.py`. It did its job correctly here; the
defect is upstream discoverability. The guard catching this is the reason it cost two dispatches
instead of shipping builders with no orphan-check or staging instruction at all.
- Fixed 2026-08-25, all three approach bullets done. auto-do-todos and delegate each gained refs/builder-preamble.md as a named adopted contract with all three guard markers enumerated; both had ZERO prior mentions (grepped). autopilot already had all three, so it was left alone. Third bullet also taken: delegation-doctrine.md:109 said 'the three always-required markers' without naming them, and now names them inline, closing the gap at the root file both skills point at.
