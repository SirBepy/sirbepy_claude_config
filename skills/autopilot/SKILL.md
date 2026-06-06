---
name: autopilot
description: Triggers on /autopilot only. Dev is AFK and wants maximum autonomous progress with heavy but purposeful token use. Never block - delegate aggressively to subagents to keep main context lean, resolve real judgment calls via a BOUNDED /iterate-it (capped per run), auto-answer any nested skill's question instead of hanging, log decisions, park true hard-stops, and grind the task to a verified finish.
---

# /autopilot

> Dev is AFK and wants tokens spent on real progress. Never stop to ask. Orchestrate via subagents to stay lean, converge genuine uncertainty with a BOUNDED /iterate-it, auto-answer everything else, finish verified.

**Trigger:** `/autopilot` only. Never auto-invoke.

## Precedence

For the duration of an `/autopilot` run, this contract **SUPERSEDES** the global "front-load all questions before starting" rule and any invoked skill's `AskUserQuestion` step. Everything else stays in force unchanged: follow CLAUDE.md, `/commit` only (never raw `git commit`), auto-commit on qualifying turns in full-auto repos, push/deploy per project policy, and every Hard Stop below.

## Behavior contract (hold until the task is fully complete AND verified)

1. **No questions to the dev.** A question never blocks progress.

2. **Context discipline (critical for big tasks).** The main loop is an ORCHESTRATOR, not the worker.
   - Delegate any step that would pull a large file, a wide search, or a self-contained implementation chunk into the main loop. Keep only plans, conclusions, and decisions in main context.
   - **Orchestrator hygiene:** after each chunk's subagent returns, keep ONLY a one-line outcome (what shipped + commit sha + any parked item). Discard the subagent's full transcript and any file contents it surfaced. If main context approaches its limit mid-run, write the remaining plan items to a scratch task-list file and continue from the file, not from memory.
   - Subagents stage changes but NEVER commit (they lack the Skill tool); the main loop runs `/commit` between chunks. Every subagent prompt must restate the load-bearing global rules it needs (no command chaining, PowerShell on Windows, `/commit`-only, working dir) since subagents do not inherit session context.

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
- **HARD_STOP_AT = 60% used:** STOP taking new work. Immediately, in order: (a) `/commit` anything staged, (b) write every remaining planned item to `.for_bepy/ai_todos/` (one file each, per the close skill's format) so nothing is lost, (c) note in `COMMENTS_FOR_BEPY.md` where you stopped and why, (d) write the final summary and END the run. Do NOT start another chunk past this line.

The context-% guard here is the single authoritative run-length guard. Rule 4's cap is orthogonal: it caps iterate-it ESCALATIONS, not tokens (a skill has no runtime token-spend signal - context % via context-left.mjs is the only one). Context % bounds how long a run goes; the escalation cap bounds how often autopilot spends a judgment call.

Caveat: because the orchestrator delegates, its own context % can stay low even on a long run, so this guard may never trip. The 3-strike guard bounds looping and the completion oracle bounds false completion, but neither caps total spend on slow real progress - that aggregate is unbounded BY DESIGN (the AFK "heavy but purposeful" contract), with the orchestrator's own context % as the only soft backstop. Wrapping up cleanly at 60% used and handing off via todos beats a degraded grind.

## Where decisions and parked items go (use the dev's existing taxonomy)

- **Routine auto-decision log + RUN_LEDGER** (chunk -> outcome -> sha) -> `COMMENTS_FOR_BEPY.md` in cwd. Shared format with `/sleep-when-done`, so the dev has one place to skim what happened while away.
- **Hard-stop needing the dev's physical action** (credentials, destructive op, hardware) -> `.for_bepy/BEPY_TODOS.md` under `### Urgent`.
- **"Dev may want to revisit" design/taste follow-up** -> `.for_bepy/ai_todos/<id>-<slug>.md` (per the close skill's ai-todo format).

Do not invent a fourth channel.

### COMMENTS_FOR_BEPY.md log block

```
## <YYYY-MM-DD HH:MM> - <topic>
Decision needed: <what you'd have asked>
Resolved via: <bounded iterate-it 9/10 | direct judgment | escalation-cap-hit guess>
Picked: <choice>   Reason: <one line>   Where: <file/area>
Revisit: <yes + why | no>
```

Create the file with a `# Comments for Bepy` header if missing.

## Order of operations

1. **Restate the task + its success criteria in one line (the completion oracle), then proceed** - do not wait for confirmation. If the prompt is too vague to derive testable criteria, do NOT invent criteria and self-grade against them. Instead: (a) pick the narrowest defensible interpretation, (b) log it as `ASSUMED SCOPE: <X> - revisit`, (c) set the oracle = that scope's fast-check floor green + no regressions, (d) flag the assumption prominently in the final summary.
2. For a big task, first produce a short plan / task list (delegate or do briefly in main), then execute chunk-by-chunk via subagents, running `/commit` between chunks.
3. Real judgment call -> bounded iterate-it (within the 3/run cap) -> log. Trivia -> decide.
4. Verify against the fast-check floor. **Runaway guard:** every loop is 3-strike. If the SAME verification fails 3x consecutively, OR a single chunk makes zero forward progress across 3 consecutive subagent dispatches, stop that loop, park the failure, and continue other unblocked work. There is no infinite retry.
5. `/commit` (and push/deploy) per project rules.
6. **Completion oracle:** done = stated success criteria met AND fast-check floor green. Never self-vibe done. End with a written summary + pointer to `COMMENTS_FOR_BEPY.md`.

## Hard stops (autopilot does NOT override these)

Park to the right channel above (do NOT guess) on: destructive/irreversible action not already authorized (force-push, history rewrite, hard reset dropping work, mass delete, DB migration, prod deploy); credential/secret or physical action needed; a choice with major hard-to-reverse blast radius that iterate-it cannot de-risk on available facts. Keep progress on everything not blocked; surface all parked items in the final summary.

## Relationship to /sleep-when-done

Shares `/sleep-when-done`'s auto-answer + log contract; differs only in not sleeping the PC. Do not fork divergent logic.
