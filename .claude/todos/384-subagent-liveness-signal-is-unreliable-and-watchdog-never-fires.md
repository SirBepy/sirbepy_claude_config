<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The doctrine's subagent liveness signal is unreliable, and its watchdog rule never actually fires

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `~/.claude/refs/delegation-doctrine.md`'s "Liveness and session budget" section produce a
check that actually detects a dead subagent, and make its watchdog requirement hard to skip.

## Context

Incident, zng-app session `7ed111fd`, 2026-08-18/19. Across one `/delegate` session, **four
dispatched agents ended without ever delivering a report**:

- a screenshot agent (captured 4 of 6 shots, then stopped)
- the first Verify-suffix builder (**died mid-edit, leaving the working tree not compiling**)
- the suffix-centering builder (made its edit, never reported)
- the routing/swap builder (made its edits, never reported)

A fifth failed loudly and correctly with an API 500, which is the behaviour the others should have
had.

Nothing in the harness surfaced any of this. Every one was caught only because the orchestrator
manually ran `fvm flutter analyze` and `git diff --stat` after noticing silence. The broken tree
in particular would have been committed blind by a less paranoid run.

### Problem 1: the documented liveness signal does not work

The doctrine currently says:

> check the task output dir's `LastWriteTime` (the `output_file` path is in every Agent tool
> result) against dispatch time - NOT file size, a 0-byte output file is not evidence of death,
> one legitimately succeeded that way. No growth in roughly the last 10 minutes on a dispatch
> expected to take 1-3 minutes (a read-only scout) means presumed dead.

Measured this session, both halves of that failed:

- An agent that was **demonstrably alive** (actively writing PNGs to disk, timestamps 70 seconds
  old) had an `output_file` whose `LastWriteTime` was **775 seconds** stale. Applying the rule as
  written would have declared a healthy agent dead.
- Every one of the four dead agents had an `output_file` of **0 bytes**, which the doctrine
  explicitly says not to treat as evidence.

So the transcript file is not flushed continuously and its mtime tracks something other than agent
activity. The rule reads authoritative and is close to useless.

### Problem 2: the watchdog requirement never fired

The same section says:

> Any fan-out of 3+ agents, or one with a 5-minute-plus ETA, additionally gets a background
> watchdog: `Bash` with `run_in_background: true` running `sleep N` then a directory listing of the
> task output dir.

This session dispatched 8 agents, several with multi-minute ETAs, and **never set up a single
watchdog**. Not a deliberate skip: the rule sits in a long reference file adopted at session start
and simply never resurfaced at any of the eight dispatch moments. Compare the builder preamble,
which is enforced by `hooks/dispatch-preamble-guard.py` and consequently was never once omitted -
it blocked two dispatches this same session for missing markers, and both were fixed immediately.

The contrast is the whole finding: **the preamble rule has a hook and held perfectly; the watchdog
rule is prose and held zero times out of eight.**

## Approach

Two changes, the second mattering more than the first.

1. **Fix the liveness signal in the doctrine.** Replace the `output_file` mtime heuristic with one
   that measures the agent's actual effects, since those are what proved reliable:
   - the working tree (`git status --short` / `git diff --stat` scoped to the agent's owned paths)
   - artifacts it was told to write (screenshots in the session's screenshot subfolder)
   - whether the agent still appears in the running list, which IS authoritative - a `TaskStop`
     against a bogus id conveniently prints "Running background agents: ..." and is the cheapest
     true liveness probe found this session. Document that trick explicitly.

   State plainly that a 0-byte or stale `output_file` means nothing in either direction.

2. **Give the watchdog rule teeth, or delete it.** A rule that fires 0 out of 8 times is not a rule.
   Options, in rough order of preference:
   - Extend `hooks/dispatch-preamble-guard.py`: it already inspects every `Agent` dispatch, so it
     can count dispatches in the current turn and warn or block on the 3rd without an accompanying
     watchdog. Same mechanism that already works.
   - Or fold the check into the orchestrator's own turn-end discipline, somewhere it is forced to be
     re-read rather than recalled.
   - Or drop the watchdog entirely and replace it with "verify the tree yourself after every
     dispatch returns or goes quiet", which is what actually caught all four failures this session
     and is cheap enough to do unconditionally.

   The third option is worth serious consideration over the first two: it needs no new machinery,
   and it is the behaviour that empirically worked.

## Acceptance

- The doctrine no longer tells a reader to judge liveness by `output_file` mtime or size.
- The doctrine names a liveness check that would have flagged all four of this session's silent
  deaths, and would NOT have flagged the healthy agent with the 775-second-stale output file.
- Whatever replaces the watchdog rule is either mechanically enforced, or simple and unconditional
  enough that it does not depend on remembering a threshold mid-fan-out.
- `refs/delegation-doctrine.md`'s "Recovery when a fan-out is interrupted with no report" paragraph
  is reconciled with the change, since it currently assumes the no-report case is rare.

## Notes

- Do not treat this as an argument against delegating. The session's actual output was fine; the
  cost was wall-clock spent re-dispatching and manually auditing, plus one near-miss where a
  non-compiling tree could have been committed.
- The related orchestrator behaviour that DID work, worth preserving in whatever replaces the rule:
  after every silent death, re-running the project's own fast checks in the main thread
  immediately reconstructed the true state, and a re-dispatch of the identical prompt succeeded.
