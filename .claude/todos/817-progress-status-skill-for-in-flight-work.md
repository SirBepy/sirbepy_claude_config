<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=e3b0c442 -->
# 817 - A skill that answers "where are you at right now?"

**Origin:** Joe, 2026-08-27, mid-session in zng-app while running `/delegate` with many subagents in flight. His words: "add a skill that tells me where youre at in your progress, i basically wish i had it now."

## The problem

During a long `/delegate` or `/autopilot` run the dev has no way to see the state of the work without asking, and the answer he gets is whatever the main agent happens to remember. That afternoon it was wrong twice: work reported as "written" had never been verified, and two items the agent believed were in progress had actually been abandoned by dead subagents.

Three failure modes showed up in one session:

1. **Silent subagent deaths.** Seven agents exited without ever reporting. The orchestrator only discovered this by probing `TaskStop` with a bogus id and diffing the tree by hand. Nothing surfaced it automatically.
2. **"Done" is ambiguous.** Code on disk, code that compiles, code that passes tests, and code a human reviewed are four different states, and the agent was collapsing them into one word.
3. **No cheap status read.** Asking cost a full turn, and the reply was prose the dev had to parse.

## What to build

A skill (`/status` or similar) that reports, per work item, in a scannable format:

- Its state, with an emoji marker rather than the word "done" - Joe asked for this explicitly in the same message.
- Whether a subagent is **currently alive** on it. `TaskStop` against a bogus task id returns the authoritative list of running agents and costs one throwaway call; that is the only reliable liveness probe (see the delegation doctrine's "Liveness and session budget" section - output-file mtime and size are both proven useless in either direction).
- **Evidence level**, not a verdict: written to disk / compiles / tests pass / reviewed by something other than the agent that wrote it. This is the distinction that misled the dev most.
- Which files each item owns, since file ownership is what forces serialization and is the usual answer to "why isn't this parallel?".

## Notes for whoever picks this up

- The status has to be derived from the tree and live probes, not from the orchestrator's memory. Memory is exactly what was wrong.
- Cheap sources that worked well that day: `git status --short` scoped to an item's paths, unused-import warnings from `flutter analyze` (that is how a half-wired feature was caught - the agent had added imports and died before using them), and the bogus-id `TaskStop` probe.
- Related: [[811-nothing-checks-a-dispatch-covers-every-item-in-its-source-todo]] covers the fan-out reconciliation half of this problem. This todo is the dev-facing view; that one is the orchestrator-facing check.
- Should work under both `/delegate` (dev present, wants a quick answer) and `/autopilot` (dev returning to a finished run).
