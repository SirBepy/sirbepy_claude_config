<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=1, content-hash=59618fe4 -->
# `/auto-do-todos` Step 6 mandates a subagent per todo, including for edits CLAUDE.md says to do inline

**Type:** skill-improvement
**Origin:** ai

## Goal

Say when `/auto-do-todos` executes a todo inline instead of dispatching a subagent for it, so a run
doing five one-paragraph doc edits does not have to either burn five dispatches or deviate silently.

## Context

Observed 2026-08-17, in the named-subset run that landed todos 352, 354, 358, 359 and 361.

`skills/auto-do-todos/SKILL.md` Step 6 says, per todo: "Execute via a subagent under the adopted
contracts above", and the skill adopts `refs/delegation-doctrine.md` "in full", including its 90/10
rule. Read literally that is five subagent dispatches.

Global `CLAUDE.md`'s "Subagent-Driven vs Inline Execution" section says the opposite for work of this
size: **Inline is the default** for "small features, fewer than 4 tasks, fewer than 3 files, tightly
sequential". Four of the five todos were a single edit to a single markdown file; the largest was two
files. The run executed all five inline.

That was the cheaper and, by CLAUDE.md's own rule, the correct call - but it is a deviation from a
step written without qualification, which is the third instance of this exact shape in this skill
(todo 347 on commit cadence, todo 358 on Steps 2-3, now Step 6). The pattern is worth naming: this
file keeps stating absolutes that real runs correctly ignore.

Note the interaction with 358, landed the same day: it added the **named-subset invocation**, where
the dev hands over the exact ids. That is precisely the invocation most likely to be a handful of
small chores, so the two rules meet head-on and neither yields.

## Approach

1. In Step 6, replace the unconditional "execute via a subagent" with a size gate that defers to
   CLAUDE.md's existing inline-versus-subagent split rather than restating it - one pointer, not a
   second copy that can drift.
2. Name the context-weight axis explicitly as the other trigger, since it is independent of size: a
   todo whose execution means reading material that gets discarded (wide greps, large files) still
   warrants a subagent even when it is a one-file edit.
3. Check whether `/batch-todos` Step 6 carries the same unqualified wording, and fix both together if
   so - they are meant to agree.
4. While in this file, consider whether the three-strikes-and-a-shape observation above belongs in the
   skill as a standing note: prefer stating the gate over stating an absolute.

## Acceptance

- A cold run with five one-file doc todos knows from the skill alone whether to dispatch or edit
  inline, without consulting CLAUDE.md to resolve a contradiction.
- The subagent path is still the default for genuinely large or context-heavy todos.
- `/auto-do-todos` and `/batch-todos` agree.

## Notes

- Filed 2026-08-17 by `/close` Phase 1, from the run's own deviation. The run flagged it rather than
  hiding it.
- Related: [[347-auto-do-todos-commit-cadence-is-unfollowable-as-written]] and
  [[358-auto-do-todos-steps-2-and-3-say-they-always-run-but-a-triage-agent-replaced-them]], both in
  `done/`, the same literal-instruction-versus-real-run gap in the same file.
