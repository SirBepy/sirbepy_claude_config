<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/959 fixed exactly one skill, /close Phase 0, and its own scope was that
     one branch; this covers the two OTHER skills that carry the same shape, found only because 959's
     builder went looking -->
# `/brainstorm` and build-watch still post a card in a repo that opted out of being asked

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the remaining ask-points the same full-auto carve-out `/close` Phase 0 just got, or decide
deliberately that they keep asking and write down why.

## Context

Filed 2026-09-10 by `/loop-todos` cycle 1, from the out-of-scope findings of the builder that closed
`done/959-close-phase-0-asks-in-full-auto-repos.md`.

959 fixed one branch in one skill: `/close` Phase 0 now detects `@import
~/.claude/snippets/full-auto.md` in the repo's own `CLAUDE.md` and files the unfinished item instead
of posting a card. The builder then checked whether anything else in the tree has the same shape and
found two that do, plus two that deliberately do not:

- **`skills/brainstorm/SKILL.md:31`** - its step-5 checkpoint fires `AskUserQuestion` for any
  non-trivial creative or feature work, with no full-auto carve-out at all. Its only escape is a
  triviality test based on file scope, which is unrelated. This has the widest blast radius of the
  three, since `/brainstorm` gates nearly all feature work.
- **`skills/commit/build-watch.md:78`** - "Otherwise: STOP and ask" for an infra or judgment-call CI
  failure, no carve-out. Lower risk, because a judgment call is what it is FOR, which is exactly the
  question this todo has to answer rather than assume.

Two that are already fine and should not be touched:

- `skills/bepy-project-setup-roblox/SKILL.md` suppresses every card behind its own explicit `auto`
  invocation flag. Same outcome, different mechanism. Worth reading as precedent.
- `skills/delegate/SKILL.md:42` states as a hard rule that every fork reaches the dev with nothing
  auto-answered. That is the whole point of a mode the dev opts into by typing `/delegate`, so it is
  intentional, not a gap.

Note also that `/autopilot` and `/auto-do-todos` both carry a Precedence section that supersedes
nested `AskUserQuestion` steps, but both key off being in an unattended RUN of that skill, not off
the repo's own full-auto opt-in. So an ordinary interactive `/brainstorm` in a full-auto repo is
still uncovered by anything.

## Approach

1. Decide the boundary FIRST, before editing either file, and write it down: a repo that imports
   `full-auto.md` has opted out of being asked, but a card that exists to stop irreversible or
   expensive work is a different animal from one that exists to confirm a preference. `/close`'s
   answer was "take the safe branch and file what would have been lost". Each of these two needs its
   own version of that sentence.
2. `/brainstorm`: the checkpoint's purpose is showing a plan before building. In a full-auto repo the
   defensible auto-answer is to proceed with the plan it would have shown, and record the plan where
   the dev can find it afterwards, rather than to skip planning. Confirm that against the skill's own
   text rather than taking this todo's word for it.
3. `build-watch.md`: a red CI build that is NOT auto-fixable is exactly the case its own gated
   auto-fix rules already refuse to touch. The honest options are asking anyway even in a full-auto
   repo, or filing a High-priority todo and continuing. Pick one and say why in the file.
4. Reuse 959's detection verbatim - the literal `@import` line, mechanically checked, never a guess
   about which org owns the repo. Do not invent a second detection mechanism.

## Acceptance

- Both files either carry the carve-out or carry one sentence saying why they still ask.
- The detection, where added, is the same literal `@import` check `/close` Phase 0 uses.
- `python ci/run_all.py` exits 0.
- A trace per skill, in the report, of what happens in all three cases: interactive ordinary repo,
  interactive full-auto repo, unattended run.

## Notes

- Do not touch `skills/delegate/SKILL.md` or `skills/bepy-project-setup-roblox/SKILL.md`. Both were
  checked and are correct as they stand.
- If this grows past two files, stop and reconsider: at that point the carve-out wants to live in one
  place that the skills reference, rather than being pasted into each of them.
