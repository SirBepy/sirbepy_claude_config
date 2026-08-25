<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Nothing in the backlog or done/ covers what a skill should do when the Agent tool is absent;
     404/405/413 are about subagent BEHAVIOUR when subagents do run. -->
# Skills that mandate subagents have no defined behaviour when the Agent tool is unavailable

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the subagent-dependent skills a stated fallback, so a session where the Agent tool is off
degrades predictably instead of the model improvising and self-reporting a deviation.

## Context

Observed 2026-08-22 in `hubbub-game-split-opinions`. That session ran with a harness-level
directive in its system prompt:

> Do not call the AgentTool unless the user requested it. Do not use workflows or deep-research
> unless the user requested it.

Three skill steps assume subagents unconditionally and say nothing about this case:

- `/auto-do-todos` **Step 4**: "Dispatch ONE subagent (`model: 'sonnet'`) with the full text of
  every todo `/batch-todos` parked as HARD."
- `/auto-do-todos` **Step 9**: "Dispatch subagents to verify the run's whole diff."
- `/code-check` **Step 4.2**: "Delegate when a doc is expensive to read ... dispatch ONE subagent."

The directive and the skills are in direct conflict, and nothing resolves it. The session did the
work inline and reported the deviation in its summary both rounds, which worked out - but that was
a judgement call made twice under ambiguity, not a defined path, and a different session could as
easily have called the tool anyway or refused the step.

`/auto-do-todos` gets this right for a related case: its "Order of operations" section has explicit
named substitutions (questions-first invocation, named-subset invocation) that say which guarantees
move where. The same treatment is what is missing here.

Worth noting the inline fallback was not obviously worse for the todo-backlog case. Step 4's triage
is cheap when the todos are already in context, and Step 9's verification was stronger inline
(typecheck, tests, build, the platform's forced typecheck, and a before/after screenshot hash diff)
than a summarising subagent would likely have been. The fallback is a real option, not a degraded
mode, at least at small scope.

## Approach

Add a short shared clause, referenced rather than restated, covering: if the Agent tool is
unavailable in this session (harness directive, tool not present, user instruction), do the step
inline and name the substitution in the run's summary. Then point the three call sites at it.

Decide per site whether inline is acceptable or the step should be SKIPPED with a stated reason:

- `/auto-do-todos` Step 4 triage - inline is fine, the todos are already read.
- `/auto-do-todos` Step 9 verification - inline is fine and arguably better; the fan-out was for
  context economy, not capability.
- `/code-check` Step 4.2 - the subagent exists specifically to keep large doc bytes out of the main
  context, so inline is a genuine trade. Consider "read the docs inline anyway, but only when the
  scope is under N files" and skip-with-reason above that.

The right home for the shared clause is `~/.claude/refs/delegation-doctrine.md`, which already owns
the dispatch rules and is already adopted by reference from these skills.

## Acceptance

- A session with the Agent tool off can execute `/auto-do-todos` and `/code-check` end to end
  without improvising, and the summary text it should print is specified rather than invented.
- The clause lives in exactly one file, referenced from the three call sites.
