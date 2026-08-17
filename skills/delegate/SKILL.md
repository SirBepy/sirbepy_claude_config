---
name: delegate
description: Puts the MAIN agent into interactive orchestrator mode for the rest of the session - subagents do all building and broad reading, the main thread is for talking ideas through with the dev and dispatching. Genuine forks become question cards before dispatch; nothing is auto-answered. `/delegate off` ends the mode.
disable-model-invocation: true
---

# /delegate

> The dev is HERE. Talk ideas through in the main thread, dispatch every build. The main agent
> orchestrates and never becomes the worker.

**Trigger:** `/delegate` only. Never auto-invoke.

## Activation

On invocation, the session ADOPTS `~/.claude/refs/delegation-doctrine.md` for its whole
remainder. Read that file now and follow it as if it were written here: the 90/10 rule, dispatch
discipline, orchestrator hygiene, and the quality tells for distrusting a report.

Confirm activation in one line, then continue with whatever the dev was doing.

The mode is **sticky**: it survives across turns, across other skills invoked mid-session, and
across topic changes. It ends only when the dev types `/delegate off` (or the session ends).

## Deactivation

`/delegate off` -> acknowledge in one line that orchestrator mode is off, and revert to normal
behavior for the rest of the session. Nothing else changes; no summary, no cleanup.

## The interactive layer (this is the whole difference from /autopilot)

`/autopilot` runs the same doctrine with the dev AFK: it auto-answers nested skills' questions,
logs blockers to a file, and grinds to a finish. `/delegate` is the opposite posture on every one
of those points:

1. **Every question and fork reaches the dev, nothing auto-answered.** The global question rules
   stay FULLY in force: front-load before starting work, one `AskUserQuestion` with 2-4 options,
   domain tag, long/short-term picks marked inside the labels. A fork that surfaces while writing
   a dispatch prompt gets resolved BEFORE that dispatch goes out - never handed to a subagent to
   guess at. Nested skills that fire `AskUserQuestion` relay to the dev as normal; no
   `/iterate-it` substituting for a question the dev is sitting right there to answer.

2. **Ideas get discussed in the main thread, not delegated.** Design conversation, tradeoffs,
   naming, scoping: that is what the main agent's context is FOR. Only once the shape is agreed
   does anything get dispatched. Never answer a "what do you think about X" by spawning an agent.

3. **Blockers are surfaced, not logged.** There is no `autopilot-logs/` here. Say it in the
   response; the dev is reading.

## What the main agent still does itself

- Talks with the dev, plans, and decides.
- Writes dispatch prompts and reads reports.
- Runs `/commit` after subagent work lands (subagents stage only, never commit). Invoke and read the
  skill in full only for this run's first commit; every commit after that follows `/commit`'s
  procedure directly (session marker already written, prefilters, pathspec form, branch/overlap
  checks all still apply) without re-invoking the skill file.
- The surgical exception in the doctrine: a targeted read of a known `file:line`, a trivial
  one-line fix. Never a feature-sized edit.

## Notes

- No context self-regulation thresholds here on purpose: those are `/autopilot`'s AFK wind-down
  mechanism. The dev is present and can call the handoff himself. If context does get tight,
  say so and offer `/handoff` rather than ending anything unilaterally.
- Liveness and session-budget rules for dispatched subagents are NOT AFK-only: the doctrine's
  "Liveness and session budget" section (adopted above) applies exactly as written here - a dead or
  budget-killed subagent is just as invisible with the dev present as it is unattended.
