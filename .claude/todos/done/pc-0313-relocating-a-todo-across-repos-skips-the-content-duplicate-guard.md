<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Relocating a todo across repos skips the content-duplicate guard

**Type:** skill-improvement
**Origin:** ai

## Goal

Make a todo that moves from one repo's backlog into another run the same content-duplicate check a
newly written todo does, so a relocation cannot resurrect something the destination repo already
decided.

## Context

Found 2026-08-13 while executing todo 311. That todo asked for a PreToolUse hook enforcing the
"never chain shell commands" rule. The rule does not exist any more: commit `b28c296`, titled
"CHORE: retire the never-chain-shell-commands rule", deleted it from `CLAUDE.md` on 2026-08-11 at
Joe's explicit direction ("i no longer care about chaining, it doesnt matter anymore, this was
because of some bugs in old version of claude code").

311 is the SIXTH filing of this same request. `done/` already holds `07`, `21`, `64`, `79`, `208`
and `267`, and `267` was itself dropped on 2026-08-12 for exactly this reason. An agent spent a
full dispatch building and measuring a spike for a rule nobody wants enforced.

The dedupe machinery is not missing. Todo 286 confirmed on the same day that the content-duplicate
guard in `close/ai-todos-format.md` already reads "grep the destination backlog and `done/`", so
`done/267` was in scope and should have been hit. The gap is that 311 did not arrive through a
writer that runs that guard: it was RELOCATED from `zng-biller`'s backlog by `/cleanup-todos`,
which moves a file whose target is another repo without re-checking it against the destination.

So the guard covers authoring and does not cover immigration.

## Approach

Add the content-duplicate check to the relocation path, not just the authoring path. Concretely,
whatever step in `/cleanup-todos` decides "this todo belongs in another repo" must, before writing
it there, grep that destination's backlog AND its `done/` for the subject, and read the hits.

Three outcomes worth distinguishing, because they are not the same:

- The destination already has a live todo for it. Fold and do not create a second file.
- The destination ARCHIVED it as done. The relocation is stale; drop it and say so.
- The destination archived it as DECLINED, which is this case. Drop it and carry the decline reason
  across, so the seventh filing does not happen either.

Also worth deciding: whether a retired RULE (a deleted line in `CLAUDE.md`) needs its own trace.
The five prior todos were each caught only because someone happened to read `done/`. Nothing today
links "this rule was retired" to "stop accepting todos that enforce it".

## Acceptance

- A todo relocated into `~/.claude` from another repo is checked against this backlog and `done/`
  before it lands, with the check named explicitly in `/cleanup-todos`'s own steps.
- A relocation that collides with a DECLINED archive entry is dropped with the decline reason
  carried into the report, not silently filed.

## Notes

- Filed by the orchestrator of the 2026-08-13 `/auto-do-todos` run from a builder's out-of-scope
  report, per the channel todo 291 added to `refs/delegation-doctrine.md` earlier the same run.
- The spike the wasted dispatch produced is kept at `hooks/EXPERIMENTAL-command-chaining-detector.py`
  with its measurements, so a seventh filing can be closed by pointing at the numbers: 55 percent of
  30047 real commands on this machine would trip it, and roughly 80 percent of a manually
  classified sample were false positives.
- Done 2026-08-13, same run that filed it. The three-outcome rule and the retired-rule check live ONCE in close/ai-todos-format.md's Content-duplicate guard, which now explicitly names /cleanup-todos relocation as a covered writer: moving a todo into another repo's backlog is a write into that backlog and gets checked against the DESTINATION, not the source. A hit resolves to LIVE (fold), DONE (drop as stale) or DECLINED (drop and carry the decline reason forward), never a blind write. cleanup-todos/SKILL.md's Relocate block gained a step 1 that invokes the guard by reference and adds only skill-local mechanics (which of its own steps to skip per outcome), so the prose is not duplicated. Retired-rule trace: implemented rather than hand-waved, and deliberately NOT as a new ledger, which would have been process nobody executes. A rule retirement is already a commit with a descriptive message, so 'git log --oneline -- <the rule's file>' grepped for the todo's keywords surfaces it (b28c296 'CHORE: retire the never-chain-shell-commands rule' is one grep away), and that outcome reuses the existing DECLINED branch rather than inventing a fourth.
