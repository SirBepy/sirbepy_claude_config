<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 938 and 949 are about ESCAPING a preamble into a Workflow script (backticks, backslashes, -Compact/-AsJsLiteral) - mechanics of getting text in. This is the prior question of whether Workflow can host the run at all given the skill's own verify ladder. 1018 is the separate todo-write-guard conflict. -->
# /mega-todos names Workflow as its vehicle but its own barriers cannot run there

**Type:** skill-improvement
**Origin:** ai

## Goal

`/mega-todos` states one vehicle that actually works end to end, so a run does not have to improvise
the choice and then disclose a deviation.

## Context

Hit on a real 10-lane run on 2026-09-25 in `claude_usage_in_taskbar`.

`skills/mega-todos/SKILL.md` is built around the Workflow tool - the opening line says the whole
point is moving the grind into a Workflow script, and Step D says to author one with `pipeline()`
over lanes. But Step D then says, correctly:

> Barriers do NOT live in the script. **A Workflow script has no shell and no filesystem** ... so a
> barrier that runs `cargo check` or `pytest` cannot be a step in it. Return the workflow between
> batches and run the barrier in the MAIN THREAD.

And the verify ladder assigns every rung except the per-todo one to the main thread.

So a Workflow-hosted run is: author a script, return after batch 1, run the barrier, author another
script, return after batch 2, and so on. Each return costs a fresh script and a fresh
`-Compact -AsJsLiteral` escape pass per lane. Against the Agent tool the same structure is one
dispatch per lane and a barrier in between, with no escaping at all and no second authoring step.

The run in question used the Agent tool for all 10 lanes and disclosed it. That is arguably against
the letter of "never silently fall back for the whole run" - it was not silent, but it was the whole
run. The skill's own wording anticipates a per-LANE fallback ("if that is somehow still infeasible
for a given lane"), and does not describe the case where the barrier cadence makes Workflow the
worse vehicle for every lane.

## Approach

Decide which of these the skill means, and say it once, plainly:

1. **Workflow is for the batch, Agent is for the run.** Keep Workflow as the documented vehicle only
   where a batch is large enough that the escaping overhead is repaid by one authoring pass, and name
   the threshold (lane count? todo count?). Below it, the Agent tool is the documented default, not a
   fallback needing disclosure.
2. **Agent is the default, Workflow is the opt-in.** Simpler, and matches what the run actually did.
   The skill's framing would need rewriting, since "moves the whole grind into a Workflow script" is
   its opening justification - but the context-economy argument it rests on is mostly served by
   `-Compact` pointer prompts, which work identically through the Agent tool.

Either way, delete or rewrite the "never silently fall back for the whole run" clause so it stops
describing a correct choice as a deviation.

Check whether `/autopilot` and `/delegate` have the same latent conflict before fixing only this one.

## Acceptance

- [ ] `skills/mega-todos/SKILL.md` names one default vehicle, with the condition under which the
      other is used, and no clause that makes the documented path read as a deviation.
- [ ] The barrier-cadence cost is stated where the vehicle is chosen, not only in Step D.
- [ ] A reader can tell, before dispatching anything, which tool a given run will use.

## Notes

Measured on that run: 10 lanes, 2 waves, 6 concurrent at peak, 5 barriers. Under Workflow that is 5
separate scripts to author and escape; under the Agent tool it is 10 prompts and 5 shell barriers.
