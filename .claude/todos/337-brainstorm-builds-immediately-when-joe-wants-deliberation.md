<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=8, reconfirm-count=1, content-hash=70dcc30f -->
# /brainstorm goes straight to implementation, but Joe invokes it for big calls expecting deliberation

**Type:** skill-improvement
**Origin:** ai

## Goal

Let `/brainstorm` tell apart the two things Joe uses it for, instead of always taking the second
one: a small feature where he wants the design picked and built, versus an architectural call where
he wants the idea stress-tested before a line is written.

## Context

`~/.claude/skills/brainstorm/SKILL.md` is explicit and deliberate about this. Step 3: *"Pick the
approach internally... Do not present the design for approval. Do not write a spec for the user to
read."* Step 4: *"State it in one line and build."* The `## Gate-free by design` section exists
specifically to promise no approval checkpoint.

On 2026-08-14 Joe opened with *"im here to /brainstorm it"* for a global rule change. The skill was
followed exactly: questions front-loaded in one card, approach picked, first edit started. His
response was **"dont start working on it yet, i first want you to brainstorm the heck out of this
hahah"**, followed by a request for a 3-subagent `/rate-it` panel on the plan.

The edit was reverted. What followed produced real value: two rating panels and a 5-round
`/iterate-it` moved the design from 4/10 to 8/10 and killed two fatal flaws before any code existed.
So the deliberation was correct for this task, and the skill steered away from it.

This is not Joe changing his mind mid-task. The memory
`feedback_adversarial_validation_on_tooling_decisions` already records the standing rule: *"Big
retire/replace/architecture calls get a rate-it/iterate-it panel first, never quick agreement with
Joe's lean."* `/brainstorm` is the one entry point that currently contradicts it, and it is the
entry point most likely to be used for exactly those calls.

## Approach

The skill already computes what it needs. Step 2 decides whether any genuine fork exists, and
CLAUDE.md's Execution Discipline section already splits inline from subagent-driven work by size.

1. Add a branch after step 2, before step 3: if the task is architectural (a global rule, a hook, a
   skill contract, a cross-project convention, or anything whose blast radius is not one feature in
   one repo), do NOT proceed to build. Write the proposal and hand it to `/rate-it` or
   `/iterate-it` first.
2. Keep the gate-free promise for the case it was written for: a feature, component, or behavior
   change inside one codebase still goes straight to implementation, unchanged.
3. State the branch condition concretely enough that it does not become a judgment call every time.
   Blast radius is the usable test: one repo means build, every future session means deliberate.
4. Update the `## Gate-free by design` section in the same edit so the two do not contradict, the
   way the current file would if a branch were bolted on without touching it.

## Acceptance

- `/brainstorm` on a component or feature behaves exactly as today, with no new checkpoint.
- `/brainstorm` on a global rule, hook, or skill contract produces a rated proposal before any edit.
- `SKILL.md` has no sentence promising gate-free behaviour that the new branch contradicts.

## Notes

- Filed by `/close` on 2026-08-14 from the correction in that session.
- The cost of getting this wrong is asymmetric: building the wrong global rule is expensive to
  unwind, while one extra rating pass on a small feature only wastes a few minutes.
- Do not solve this by adding an "are you sure?" prompt. CLAUDE.md's front-load rule and this
  skill's own design both reject mid-task approval gates; the branch has to be decided from the
  task's shape, not by asking.
