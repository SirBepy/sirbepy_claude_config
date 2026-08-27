<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=6, reconfirm-count=1, content-hash=32148d0a -->
<!-- duplicate-checked -->
# Nothing stops a subagent writing into .claude/todos/, and one did

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether the doctrine's "a subagent never writes into `.claude/todos/`" rule needs mechanical
enforcement, now that there is a confirmed instance of a subagent ignoring it, and act on the
decision.

## Context

`refs/delegation-doctrine.md`'s "Out-of-scope findings" section states the rule and records that a
hook was **already considered and rejected** for it:

> A PreToolUse write-guard hook was considered and rejected here: it enforces mechanically, but the
> report-back channel keeps the same finding without needing a new harness capability.

That rejection is carried forward here on purpose, per the backlog contract, so this todo is not a
blind re-litigation. What changed is the evidence behind it.

The rejection's premise was that the report-back channel is sufficient. On 2026-08-19, during a
33-agent `/mega-todos` run, a builder **bypassed the report-back channel entirely** and wrote
`.claude/todos/391-builders-have-no-sanctioned-way-to-get-a-whole-tree-baseline.md` directly. Every
dispatch prompt in that run carried the "NEVER write into `.claude/todos/` - report findings, the
orchestrator allocates ids" instruction verbatim.

It got lucky on the id: 391 was genuinely free, so no collision occurred. Todo 291's original
incident (a builder writing `263-...` that collided with an already-taken id inside the same run)
shows what happens when it does not.

Note the finding itself was good and was kept. The channel was the problem, not the content.

## Approach

1. Weigh the two failure modes honestly rather than defaulting to a hook. This repo kills
   guess-based hooks, but this one is not a guess: it is a path-shaped, exact mechanical check
   (`\.claude/todos/.*\.md$` written by a non-orchestrator), which is the category the hook doctrine
   in `PLAN.md` says DOES ship.
2. The blocker is detection: a PreToolUse hook cannot obviously tell an orchestrator's write from a
   subagent's. Establish whether the payload carries anything that distinguishes them before
   designing around it. **If it does not, say so and stop** - an unenforceable rule stays prose, and
   that outcome closes this todo legitimately.
3. If it is enforceable, follow `hooks/todo-duplicate-guard.py`'s shape and ship it with a test.
4. Either way, update the doctrine's recorded rejection with the 2026-08-19 evidence, so the next
   reader sees the rule has been broken in practice rather than only in theory.

## Acceptance

- The doctrine's rejection note reflects the 2026-08-19 instance.
- Either a guard exists with a test, or the doctrine states plainly why it cannot be enforced.
- No new guess-based hook ships.
