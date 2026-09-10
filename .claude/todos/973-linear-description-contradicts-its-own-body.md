<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/842 was about the "Triggers on /X only" prose in 15 skills' descriptions
     and resolved 14 of them; this is the one it deliberately left, and it is a different defect -
     the description contradicts the body about what the skill DOES, not about how it is invoked -->
# `/linear`'s description says it files issues, its body says writes live in `/ticket`

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/linear/SKILL.md`'s description agree with its own body about whether the skill writes,
then settle whether it should carry `disable-model-invocation: true`.

## Context

Filed 2026-09-10 by `/loop-todos` cycle 3, from the out-of-scope findings of the builder that closed
`done/842-eighteen-skills-declare-slash-only-but-are-model-invocable.md`.

842's sweep classified 15 skills whose description opened with "Triggers on /X only" while their
frontmatter left them model-invocable. Its important finding was that most of them are genuine chain
callees - `bepy-project-setup-web` runs eight of them in order, `/autopilot` and `/auto-do-todos`
invoke `/iterate-it`, `/rate-it-and-commit` invokes `/rate-it` - so flagging them would have broken
those chains silently. Those got the false "only" sentence deleted and stayed invocable.

`linear` was the one it deliberately left alone, for a reason worth preserving: it found NO confirmed
Skill-tool chain caller (`skills/ticket/*` reuses its `Invoke-Linear` PowerShell helper as code,
which is not invocation), so on the chain-caller test it looks flaggable. But its description
advertises creating and filing issues while its body says writes live in `/ticket`. That
contradiction means the invocability question cannot be answered from the description, because the
description may simply be wrong about what the skill does.

Deciding blind is the failure mode 842 was careful to avoid: adding `disable-model-invocation: true`
to a skill something expects to fire silently breaks it, and that breakage is invisible until Joe
wonders why nothing happened.

## Approach

1. Read `skills/linear/SKILL.md` in full and establish what it actually does today: does any code
   path in it WRITE to Linear (create or update an issue), or is it read-only query and lookup with
   every write delegated to `/ticket`?
2. Fix the description to match that answer. This is the load-bearing half; the invocability
   question follows from it and cannot be settled first.
3. Then decide invocability on the corrected description, using the chain-caller test
   `skills/bepy-skill-creator/SKILL.md:101` already documents: a skill any other skill invokes via
   the Skill tool must NOT be flagged. Re-run that check rather than trusting 842's, since the tree
   has moved.
4. If it is genuinely dev-only with no caller, add `disable-model-invocation: true`. If it is
   ambiguous a second time, leave it flagged as ambiguous IN THE FILE rather than in a todo, so the
   next reader inherits the finding instead of re-deriving it.

## Acceptance

- The description states what the skill does, and nothing in the body contradicts it.
- The invocability decision is made and its reason recorded, or the ambiguity is recorded in the
  file itself.
- `python ci/run_all.py` exits 0, including the frontmatter check.

## Notes

- Do not batch this with other description edits. 842 already did the mechanical sweep; what is left
  here is a single judgement call that needs the skill read in full.
