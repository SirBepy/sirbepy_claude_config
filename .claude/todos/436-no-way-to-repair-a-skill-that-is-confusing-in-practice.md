<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Nothing catches a skill that reads fine but confuses Claude in practice

**Type:** skill-improvement
**Origin:** ai

## Goal

A diagnostic path triggered by session-confusion signals, so a skill that keeps producing
back-and-forth gets diagnosed and patched instead of silently costing turns forever.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current skill-maintenance paths all require someone to already know a skill is broken:
`bepy-skill-creator` validates static conventions, `/code-check` reviews structure, and a
skill-improvement todo gets filed when Claude or Joe notices a gap. Nothing triggers on the actual
symptom: **a session where a skill is being followed but keeps going wrong.**

The evidence this gap is real is in this repo's own `done/` folder. Multiple archived todos are
retroactive fixes for skills that were confusing in practice, not malformed: 251 (a `/rate-it` rule
that was unsatisfiable in Conductor), 245 (nested menu precedence in `/rate-it-and-commit`), 261
(skills lacking AskUserQuestion timeout handling), 337 (`/brainstorm` building immediately when Joe
wanted deliberation), 230 (an `/iterate-it` phase gate). Every one of those was found by hitting it,
then filing a todo after the fact. That is the loop this todo tries to shorten.

Reference: `repos/justcarlson_dotfiles-claude/marketplace/justin-tools/skills/heal-skill`. Two ideas:

1. **Trigger on confusion signals rather than on request** - Claude self-correcting, the user saying
   "no that's wrong", repeated clarification on the same point, or a loop.
2. **A 7-pattern root-cause taxonomy** mapping symptom to cause: ambiguous branching, missing
   examples, implicit file references, missing variables, unclear workflow, wrong tool, loop-detection
   failure. Then patch the SKILL.md with user approval. Pure prompt and checklist, no code.

The taxonomy is the valuable half. The trigger is the hard half, and worth being honest about: "Claude
noticed it was confused" is exactly the kind of self-assessment that does not reliably fire, for the
same reason the harvest's own watchdog rule fired zero times across eight dispatches and got deleted
rather than fixed (recorded in `refs/delegation-doctrine.md`). A rule that depends on being remembered
mid-confusion does not survive being remembered.

So the design question is whether there is any mechanical confusion signal available. Candidates worth
checking: a hook counting consecutive turns that invoke the same skill, or Joe's own correction
phrases as a `UserPromptSubmit` pattern match. The corpus has precedent for the latter shape:
`ravila4`'s nudge system uses `UserPromptSubmit` to surface state on every prompt.

Note the overlap with todo 422: an eval harness catches a skill that fails against fixtures. This
catches a skill that fails against reality. They are complementary, and 422 is the stronger of the
two, so **422 should land first.**

## Approach

1. Read `heal-skill`'s SKILL.md for the taxonomy and the trigger wording.
2. Validate the taxonomy against real history rather than adopting it on faith. Take the five `done/`
   todos named above and classify each under the 7 patterns. **If most do not fit, rewrite the
   taxonomy from this repo's own failures instead** - that would be the better artifact anyway.
3. Solve the trigger honestly. Assess whether a mechanical signal exists (a hook counting repeated
   skill invocations, or matching Joe's correction phrases on `UserPromptSubmit`). If no mechanical
   signal is available, say so and ship it as an explicitly-invoked skill (`/heal-skill <name>`)
   rather than pretending it auto-triggers. **A skill that claims to fire on confusion but does not is
   worse than one Joe invokes deliberately.**
4. Write the skill: takes a skill name plus a description of what went wrong, walks the taxonomy,
   proposes a specific patch, applies it only with approval.
5. Make it write its finding somewhere durable. A confusion diagnosed and patched in one session
   should leave a record, since the same skill confusing two different sessions is the signal that the
   patch did not work.

## Acceptance

- The 5 named `done/` todos are classified against the taxonomy, and the taxonomy is revised if they
  do not fit.
- An explicit, honest statement of whether the trigger is mechanical or manual. No claimed
  auto-trigger without a demonstrated firing.
- The skill runs end to end on one real case and produces a specific patch, not general advice.
- Patches require approval before being applied.
- Runs after todo 422, or states why not.

## Notes

The temptation is to build the auto-trigger because it is the interesting part. The delegation
doctrine already documents what happens to rules that depend on being remembered at exactly the wrong
moment: they get deleted, not fixed. Manual invocation that works beats an auto-trigger that does not.
