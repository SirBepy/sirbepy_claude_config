---
name: autopilot
description: Triggers on /autopilot only. Dev is AFK and wants maximum autonomous progress: never block - delegate to subagents, resolve judgment calls via a bounded /iterate-it, auto-answer nested skills' questions, log only genuine blockers, and grind to a verified finish.
---

# /autopilot

> Dev is AFK and wants tokens spent on real progress. Never stop to ask. Orchestrate via subagents to stay lean, converge genuine uncertainty with a BOUNDED /iterate-it, auto-answer everything else, finish verified.

**Trigger:** `/autopilot` only. Never auto-invoke.

## Sidebar badge

Emit `<cc-autopilot:on>` at the end of your **first response** after activating autopilot. The app reads this marker and shows an "autopilot" badge on the session row in the sidebar so Joe knows the session is running unattended.

Emit `<cc-autopilot:off>` at the end of your **final response** when the run is fully complete (after the written summary). The badge disappears.

These markers are stripped from the rendered chat - Joe never sees them as text.

## Precedence

For the duration of an `/autopilot` run, this contract **SUPERSEDES** the global "front-load all questions before starting" rule and any invoked skill's `AskUserQuestion` step. Everything else stays in force unchanged: follow CLAUDE.md, `/commit` only (never raw `git commit`), auto-commit on qualifying turns in full-auto repos, push/deploy per project policy, and every Hard Stop below.

## Delegation doctrine (shared, not restated here)

An autopilot run ADOPTS `~/.claude/refs/delegation-doctrine.md` in full: the 90/10 rule (subagents do all building and all broad reading; the main loop keeps only surgical rights), dispatch discipline (scout spec packs, embedded verify floor, the verbatim stage-don't-commit line, restated global rules), orchestrator hygiene (keep one-line outcomes, discard transcripts), and the quality tells for distrusting a report. Read it at the start of the run. `/delegate` adopts the same file for interactive sessions; everything below is the AFK-only layer on top.

## Behavior contract (hold until the task is fully complete AND verified)

1. **No questions to the dev.** A question never blocks progress.

2. **Context discipline (critical for big tasks).** Per the delegation doctrine above, the main loop is an ORCHESTRATOR, not the worker. Two AFK-specific additions:
   - The one-line outcome kept per chunk includes the commit sha (autopilot commits between chunks, so the sha is the only record of what landed).
   - If main context approaches its limit mid-run, write the remaining plan items to a scratch task-list file and continue from the file, not from memory. There is no dev to hand off to verbally.
   - Cadence: the main loop runs `/commit` between chunks, since subagents stage but never commit.

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
- **HARD_STOP_AT = 60% used:** STOP taking new work. Immediately, in order: (a) `/commit` anything staged, (b) write every remaining planned item to `.claude/todos/` (one file each, per `close/ai-todos-format.md` - claim rules included) so nothing is lost, (c) write the final summary and END the run. Do NOT start another chunk past this line.

The context-% guard here is the single authoritative run-length guard. Rule 4's cap is orthogonal: it caps iterate-it ESCALATIONS, not tokens (a skill has no runtime token-spend signal - context % via context-left.mjs is the only one). Context % bounds how long a run goes; the escalation cap bounds how often autopilot spends a judgment call.

Caveat: because the orchestrator delegates, its own context % can stay low even on a long run, so this guard may never trip. The 3-strike guard bounds looping and the completion oracle bounds false completion, but neither caps total spend on slow real progress - that aggregate is unbounded BY DESIGN (the AFK "heavy but purposeful" contract), with the orchestrator's own context % as the only soft backstop. Wrapping up cleanly at 60% used and handing off via todos beats a degraded grind.

## Where decisions and parked items go (use the dev's existing taxonomy)

- **Routine auto-decisions** (trivial picks, bounded-iterate-it verdicts) -> decide and move on, no log. The dev has said he never reads a running decision log; git history + the final summary are the record.
- **Hard-stop needing the dev's physical action** (credentials, destructive op, hardware) -> autopilot is unattended, so there's no live response to surface it in. Write one file to `.for_bepy/autopilot-logs/<slug>.md` (see format below) and STOP that chunk.
- **"Dev may want to revisit" design/taste follow-up** -> `.claude/todos/<id>-<slug>.md` (per `close/ai-todos-format.md`).

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

1. **Restate the task + its success criteria in one line (the completion oracle), then proceed** - do not wait for confirmation. If the prompt is too vague to derive testable criteria, do NOT invent criteria and self-grade against them. Instead: (a) pick the narrowest defensible interpretation, (b) log it as `ASSUMED SCOPE: <X> - revisit`, (c) set the oracle = that scope's fast-check floor green + no regressions, (d) flag the assumption prominently in the final summary. **END THIS FIRST RESPONSE WITH `<cc-autopilot:on>`** (see "Sidebar badge" above) - do not rely on that section alone, this step is where it actually gets emitted.
2. For a big task, first produce a short plan / task list (delegate or do briefly in main), then execute chunk-by-chunk via subagents, running `/commit` between chunks.
3. Real judgment call -> bounded iterate-it (within the 3/run cap) -> log. Trivia -> decide.
4. Verify against the fast-check floor. **Runaway guard:** every loop is 3-strike. If the SAME verification fails 3x consecutively, OR a single chunk makes zero forward progress across 3 consecutive subagent dispatches, stop that loop, park the failure, and continue other unblocked work. There is no infinite retry.
5. `/commit` (and push/deploy) per project rules.
6. **Completion oracle:** done = stated success criteria met AND fast-check floor green. Never self-vibe done. End with a written summary.

## Hard stops (autopilot does NOT override these)

Park to the right channel above (do NOT guess) on: destructive/irreversible action not already authorized (force-push, history rewrite, hard reset dropping work, mass delete, DB migration, prod deploy); credential/secret or physical action needed; a choice with major hard-to-reverse blast radius that iterate-it cannot de-risk on available facts. Keep progress on everything not blocked; surface all parked items in the final summary.

## Relationship to /sleep-when-done

Shares `/sleep-when-done`'s auto-answer contract and the same `.for_bepy/autopilot-logs/` blocker format; differs only in not sleeping the PC. Do not fork divergent logic.
