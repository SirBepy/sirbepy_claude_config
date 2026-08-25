---
name: autopilot
description: "Dev is AFK and wants maximum autonomous progress: never block - delegate to subagents, resolve judgment calls via a bounded /iterate-it, auto-answer nested skills' questions, log only genuine blockers, and grind to a verified finish."
disable-model-invocation: true
argument-hint: "[--sleep]"
---

# /autopilot

> Dev is AFK and wants tokens spent on real progress. Never stop to ask. Orchestrate via subagents to stay lean, converge genuine uncertainty with a BOUNDED /iterate-it, auto-answer everything else, finish verified.

**Trigger:** `/autopilot` only. Never auto-invoke.

## Sidebar badge

`<cc-autopilot:on>` and `<cc-autopilot:off>` drive the "autopilot" badge on the session row in the sidebar, and are stripped from the rendered chat - Joe never sees them as text. Step 1 and step 6 below are the only place they get emitted; this section documents what they do, it is not a second instruction to emit them.

## Precedence

For the duration of an `/autopilot` run, this contract **SUPERSEDES** the global "front-load all questions before starting" rule and any invoked skill's `AskUserQuestion` step. Everything else stays in force unchanged: follow CLAUDE.md, `/commit` only (never raw `git commit`), auto-commit on qualifying turns (global default, all repos), push/deploy per project policy, and every Hard Stop below.

## Delegation doctrine (shared, not restated here)

An autopilot run ADOPTS `~/.claude/refs/delegation-doctrine.md` in full: the 90/10 rule (subagents do all building and all broad reading; the main loop keeps only surgical rights), dispatch discipline (scout spec packs, embedded verify floor, the verbatim stage-don't-commit line, restated global rules), orchestrator hygiene (keep one-line outcomes, discard transcripts), and the quality tells for distrusting a report. Read it at the start of the run. `/delegate` adopts the same file for interactive sessions; everything below is the AFK-only layer on top.

`hooks/dispatch-preamble-guard.py` rejects any `Agent`/`Task` dispatch missing three verbatim markers - name them here so a fan-out never gets built before the doctrine file is read: the staging line (`Stage your changes but do NOT commit` or `Leave all changes unstaged`), a `run_in_background` ... `FORBIDDEN` sentence, and either a `.for_bepy/screenshots/` id line or the `READ-ONLY DISPATCH` opt-out for read-only scouts. Paste the canonical block from `refs/builder-preamble.md` into every dispatch prompt.

## Behavior contract (hold until the task is fully complete AND verified)

1. **No questions to the dev.** A question never blocks progress.

2. **Context discipline (critical for big tasks).** Per the delegation doctrine above, the main loop is an ORCHESTRATOR, not the worker. Two AFK-specific additions:
   - The one-line outcome kept per chunk includes the commit sha (autopilot commits between chunks, so the sha is the only record of what landed).
   - If main context approaches its limit mid-run, write the remaining plan items to a scratch task-list file and continue from the file, not from memory. There is no dev to hand off to verbally.
   - Cadence: the main loop runs `/commit` between chunks, since subagents stage but never commit.
     Invoke and read the skill in full only for this run's first commit; every commit after that
     follows `/commit`'s procedure directly (session marker already written, prefilters, pathspec
     form, branch/overlap checks all still apply) without re-invoking the skill file.

3. **Tiered uncertainty resolution.**
   - Trivial / one clearly-correct answer -> decide, no log, no iterate-it.
   - Real judgment call you would normally ask the dev (design / architecture / UX / threshold, reversible blast radius) -> run a BOUNDED `/iterate-it`, log the verdict, proceed.
   - High-blast-radius AND hard-to-reverse (see Hard Stops) -> do NOT guess or iterate; park it.
   - `iterate-it` is a DECISION tool, not a delegation tool. Firing it counts against the per-run cap, so reserve it for genuine judgment calls - never for trivia or for work a plain subagent should do.

4. **BOUNDED iterate-it.** Invoke `/iterate-it --explore-max=2 --polish-max=1 <concrete hypothesis>` (fast convergence, ~50-150k tokens). Take the converged proposal as the decision. Hard cap: at most **3** iterate-it escalations per run; on a 4th genuine call, pick the most reversible option directly and log "escalation-cap hit, guessed" instead of spending more. Never re-litigate a converged call.

5. **Nested-question suppression contract (load-bearing).** Any invoked skill (iterate-it, rate-it, commit, rate-it-and-commit) that would fire `AskUserQuestion` must NOT relay to the dev.
   - Default rule: auto-select the option the skill marks best/long-term; if none is clearly best, pick the most reversible and log "autopilot guessed".
   - **iterate-it's terminal question is special-cased.** Its final ship / another-round / abandon prompt is control-flow, not an option-quality pick, so the default rule is undefined for it. ALWAYS choose **ship** (take the converged proposal as the decision) when the run hit `--floor` or the phase cap. NEVER auto-select "another round" (re-spends the cap on a converged call) and NEVER "abandon" (discards a decision autopilot explicitly asked for). The only non-ship path is iterate-it's own `unconverged` / `thrash` report: treat THAT as "no confident answer" and fall back to the most reversible option per Hard Stops, do not re-run.

6. **Spend tokens on quality, not filler.** Go deep: parallel subagents, write the test, run the loop, check edge cases. Not padding, not busywork.

7. **Verify before claiming done.** Run the project's fast-check floor (typecheck, unit tests, lint, build). Never end half-broken.

## Context self-regulation (do not bloat your own window)

A bloated context degrades quality, so autopilot watches its OWN remaining context and winds down deliberately rather than grinding to exhaustion. At the START of each new chunk/iteration, check remaining context by running:

```
node ~/.claude/skills/context-left/context-left.mjs
```

Read pct used (= 100 - pct left). Two named thresholds, on context USED (tweak here if the dev changes them):

- **SLOW_AT = 50% used:** start winding down. Prefer FINISHING in-flight work over STARTING new chunks; tighten scope; avoid large new investigations or wide subagent fan-out; do not begin anything you cannot also finish AND verify within the remaining budget.
- **HARD_STOP_AT = 60% used:** STOP taking new work. Immediately, in order: (a) `/commit` anything staged, (b) write every remaining planned item to `.claude/todos/` (one file each, per `close/ai-todos-format.md` - claim rules included, `**Origin:** dev` since these are pieces of the dev's own approved run deferred by the context stop) so nothing is lost, (c) write the final summary and END the run. Do NOT start another chunk past this line.

## Where decisions and parked items go (use the dev's existing taxonomy)

- **Routine auto-decisions** (trivial picks, bounded-iterate-it verdicts) -> decide and move on, no log. The dev has said he never reads a running decision log; git history + the final summary are the record.
- **Hard-stop needing the dev's physical action** (credentials, destructive op, hardware) -> autopilot is unattended, so there's no live response to surface it in. Write one file to `.for_bepy/autopilot-logs/<slug>.md` (see format below) and STOP that chunk.
- **"Dev may want to revisit" design/taste follow-up** -> `.claude/todos/<id>-<slug>.md` (per `close/ai-todos-format.md`, `**Origin:** ai` - this is Claude's own observation, not something the dev asked for).

Do not invent a fourth channel.

### `.for_bepy/autopilot-logs/` format

One file per incident, named `<slug>.md` (create the `autopilot-logs/` folder if missing):

```
# <topic>

What happened: <what you were doing>
Why blocked: <credential / destructive-op / hardware / other, one line>
Needs from you: <the specific physical action required>
```

This folder is reserved for genuine blockers only - never for routine FYI notes.

## Order of operations

1. **Restate the task + its success criteria in one line (the completion oracle), then proceed** - do not wait for confirmation. If the prompt is too vague to derive testable criteria, do NOT invent criteria and self-grade against them. Instead: (a) pick the narrowest defensible interpretation, (b) log it as `ASSUMED SCOPE: <X> - revisit`, (c) set the oracle = that scope's fast-check floor green + no regressions, (d) flag the assumption prominently in the final summary. End this first response with the oracle line immediately followed by `<cc-autopilot:on>` on its own line, nothing after.
2. **Check remaining context first, every chunk including a single-chunk run** (see "Context self-regulation" above for thresholds and actions). Then, for a big task, produce a short plan / task list (delegate or do briefly in main), then execute chunk-by-chunk via subagents, running `/commit` between chunks.
3. Real judgment call -> bounded iterate-it (within the 3/run cap) -> log. Trivia -> decide.
4. Verify against the fast-check floor. **Runaway guard:** every loop is 3-strike. If the SAME verification fails 3x consecutively, OR a single chunk makes zero forward progress across 3 consecutive subagent dispatches, stop that loop, park the failure, and continue other unblocked work. There is no infinite retry.
5. `/commit` (and push/deploy) per project rules.
6. **Completion oracle:** done = stated success criteria met AND fast-check floor green. Never self-vibe done. End with a written summary immediately followed by `<cc-autopilot:off>` on its own line, nothing after.

## Hard stops (autopilot does NOT override these)

Park to the right channel above (do NOT guess) on: destructive/irreversible action not already authorized (force-push, history rewrite, hard reset dropping work, mass delete, DB migration, prod deploy); credential/secret or physical action needed; a choice with major hard-to-reverse blast radius that iterate-it cannot de-risk on available facts. Keep progress on everything not blocked; surface all parked items in the final summary.

**A task whose fix WRITES to `hooks/` or `settings*.json` is a hard stop for any SUBAGENT dispatch.** `hooks/sensitive-file-guard.py` returns `ask` on those paths, and an `ask` inside a dispatched agent's tool call is a hard block with nobody to answer it: attended mode does not reach there, since it governs only the orchestrator asking the dev. Route such a task to the main thread with the dev present, or park it. Judge by the actual write target, not by whether the text mentions a hook - most todos naming one are fixed elsewhere. `/mega-todos` Step B and `/auto-do-todos` Step 4 both inherit this list.

## --sleep flag

`/autopilot --sleep` adds one step to the end of a successful run: after step 6's completion oracle passes (stated success criteria met AND fast-check floor green), invoke `/sleep-when-done`'s sleep action as the absolute last thing the run does.

- Only fires on normal completion. If the run ends via a Hard Stop, a parked blocker, or the HARD_STOP_AT context wind-down, do NOT sleep - the dev needs to see the parked items, and a half-finished run is exactly the "never sleep on red" case `/sleep-when-done` guards against.
- Runs after the final written summary, same as `/sleep-when-done`'s own "no text after it" rule.

## Relationship to /sleep-when-done

Autopilot owns the unattended-work contract (tiered uncertainty resolution, nested-question suppression, context self-regulation, the completion oracle, the 3-strike runaway guard, the Hard Stops list); `/sleep-when-done` owns only the sleep action itself (platform command + the "never sleep on red" precondition). `--sleep` is autopilot invoking that action as its last step - it does not pull in a second contract, since `/sleep-when-done` no longer carries one. `/close /sleep-when-done` keeps working unchanged as its own chain (close/SKILL.md's argument grammar, untouched by this).
