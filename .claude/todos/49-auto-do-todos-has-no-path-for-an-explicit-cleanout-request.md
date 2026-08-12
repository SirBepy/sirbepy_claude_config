<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=dd7d9ed0 -->
# /auto-do-todos forces keep-all even when the dev's own prompt asked for a cleanout

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/auto-do-todos` a defined path for the case where the invoking prompt itself asks to drop
todos, instead of leaving the model to improvise a deviation from two skills whose contracts
contradict each other in exactly that case.

## Context

Observed 2026-08-07 in the fibo repo. Joe invoked it as: **"lets /auto-do-todos clear out any that we
dont need"**. Two adopted contracts then pointed opposite ways:

- `~/.claude/skills/auto-do-todos/SKILL.md` "Order of operations" step 2 runs `/cleanup-todos`
  **unattended**, and its "Steps 2-3" section says that run "auto-resolves as `keep all` - no merges,
  no drops, nothing archived", carrying candidates forward to a later run instead.
- `~/.claude/skills/cleanup-todos/SKILL.md` Non-goals: "**No auto-drop, ever, under any condition** -
  every removal from the backlog goes through the Step 7 confirm gate."
- Meanwhile `/auto-do-todos`'s Precedence section says the run **supersedes** the global front-load
  rule and every nested skill's `AskUserQuestion` step, and Step 5's question round only triggers when
  the AUTO queue is empty or a prior run left `## Open questions`. Neither trigger fired here.

So the literal reading of the skill is: Joe asks to clear out todos, and the run drops nothing, reports
candidates, and grinds unrelated work instead. That is the opposite of the ask. The session resolved it
by asking anyway, via one `AskUserQuestion` round covering the drops before any grinding, which worked
and Joe confirmed 14 drops plus 34 relocations. But that was a judgment-call deviation from the written
contract, and the next run has no reason to make the same call.

Two other things that same run exposed, worth folding into the fix:

- `/cleanup-todos` Step 4 caps its deep pass at **40 todos by ascending id**. The fibo backlog was
  101, so 61 would have gone unexamined for drops, and drop candidates were exactly what was asked
  for. The run widened it to all 101 via three parallel batched agents. A cleanout request should
  raise or remove that cap, since the cap's whole justification is token cost on a routine pass.
- The eventual confirm round found that **34 of 101 todos were misfiled global-tooling items** that
  root `CLAUDE.md` says belong in `~/.claude/todos/`. Relocation is a third disposition alongside
  keep and drop, and neither skill models it.

## Approach

1. In `/auto-do-todos`, add an explicit **cleanout-intent** case: when the invoking prompt asks to
   drop, clear out, prune, or clean up the backlog, the run's ONE permitted question round (Step 5)
   fires up front, before Step 6's grind, carrying `/cleanup-todos`'s confirm list. Do not invent a
   second question round, reuse Step 5 and move its trigger condition.
2. Say plainly in that case that Step 2's `keep all` auto-resolve is suspended, so the model is not
   choosing between two contracts on the fly.
3. In `/cleanup-todos` Step 4, make the 40-todo deep cap conditional: raise it (batched across
   parallel agents, one dispatch per chunk, never one per todo) when the run was invoked for a
   cleanout rather than as routine maintenance. Keep the cap for routine runs.
4. Add **relocate** as a first-class disposition in `/cleanup-todos`'s Step 6 confirm list and Step 7
   apply, for a todo whose subject is another repo or the global `~/.claude` tree. It needs its own
   Notes-line wording, and it must record the old id since renumbering to the destination's max+1 is
   required by `ai-todos-format.md`.
5. Leave `cleanup-todos`'s "no auto-drop, ever" rule exactly as it is. The gap is that the confirm
   gate was unreachable under autopilot, not that the gate is wrong.

## Acceptance

- Invoking `/auto-do-todos` with a cleanout phrase produces a confirm round for drops BEFORE any todo
  is executed, without the model having to reason about contract precedence.
- Invoking it bare still behaves exactly as today: keep-all, no questions, straight to the grind.
- `/cleanup-todos` run standalone is unchanged for a backlog under 40 todos.
- A relocated todo lands with a correct destination id and a Notes line recording where it came from.

## Notes

- The 2026-08-07 run's actual outcome, for reference: 101 todos to 52, being 14 archived to `done/` as
  already-shipped or superseded, 31 relocated to `~/.claude/todos/` as ids 13-43, and 3 merged into one
  new global todo 44.
- Related global todo: **21** (enforce the no-chained-shell-commands rule with a hook) contradicts
  existing global **07** (that rule is unworkable in PowerShell). Unrelated to this todo's fix, but both
  arrived in the same relocation batch and someone should reconcile them before either is executed.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: in `auto-do-todos/SKILL.md` add a cleanout-intent branch, triggered by drop, clear,
  prune or clean-up phrasing, that fires the question round up front carrying `/cleanup-todos`'s
  confirm list and suspends the keep-all auto-resolve for that run. In `cleanup-todos/SKILL.md` make
  the 40-id deep-pass cap conditional or raised for a cleanout run, batched across parallel agents,
  and add "relocate" as a first-class disposition. This was produced by a strict second-pass
  re-triage that specifically asked whether a defensible answer exists without the dev; it
  concluded yes. Not executed only because the session ended.
