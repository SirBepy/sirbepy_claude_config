<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=2, content-hash=2cd646f6 -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "live-verify", "EXCLUDE-LIVE", "live verify". The only hit
     is 480 (respawn skill), an unrelated mention. 405 and 413 are mega-todos todos about barriers
     and scout file-sets, different subjects. -->
# /mega-todos tells you to drop every live-verify todo without ever checking reachability

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/mega-todos/SKILL.md` Step B (Exclusions) instructs a run to remove, from the AUTO queue,
regardless of what triage said:

> **`live-verify` / `verify ... live` todos.** They need the running app and the dev's eyes. A green
> verify floor cannot see "this looks wrong" (delegation doctrine, Visual work). Park them.

That instruction is keyed on the todo's TITLE, not on whether anything can actually render it. In a
project with a working view harness it is wrong most of the time, and it fails silently: the run
reports a tidy exclusion count and nobody learns the todos were droppable in name only.

## Context

**Measured on 2026-08-22 in `claude_usage_in_taskbar`.** A run triaged 49 todos, excluded **24** as
live-verify per this rule, and reported to Joe that his backlog was blocked on him. His reply was
"and are you able to look at the app".

A re-triage of those same 24 against the project's real harness API found:

- **8 fully reachable**, 10 partially, **6 genuinely dev-only** (a real Android device, a Mac,
  Sysinternals ProcMon, a cold-boot recurrence, a real daemon turn, one preference reading)
- **4 were already answered** by specs that had existed for weeks and nobody had connected to them
- 14 were then shot in one run, which found **4 real bugs**, two of which the todos never suspected,
  including one where a fix had been silently reverted and the two rendered states were SHA-identical

So the rule discarded 18 actionable todos and, worse, produced a confident wrong report to the dev.

**The rule's stated reason is sound and should be kept**: a green verify floor genuinely cannot see
"this looks wrong". What is wrong is jumping from that to "so drop anything named live-verify". A
screenshot the dev looks at is exactly how a harness answers a visual question, and most of these
todos wanted a picture, not a running binary.

## Approach

Replace the blanket exclusion with a reachability question, and put the burden on naming the blocker
rather than on the title.

Step B should ask, per todo: **what specifically can a renderer not produce here?** Exclude only if
the answer is one of a short, concrete list:

- real hardware (a phone, another OS)
- a real backend process or a real streamed turn
- an OS-level capture (crash log, process trace, cold boot)
- the dev's own taste, or his installed build specifically

If none of those apply, it belongs in the AUTO queue with a capture step, not in the exclusion pile.

Two supporting changes worth making at the same time:

1. **Check for an existing spec before excluding OR building.** Four of the 24 were already covered.
   A grep of the project's spec directory for the feature name is cheap and would have caught them.
2. **The exclusion report should name the blocker per todo**, not just tally a count. "24 live-verify"
   is unfalsifiable; "6 excluded: 2 need a real device, 1 needs a Mac, 3 need a real daemon turn"
   is reviewable, and a wrong entry in it is visible.

Note the skill cannot assume a harness exists. Word it as "if the project has a way to render a view
without its real backend, use it" and let the run discover that, the same way the verify ladder
already resolves per-project commands rather than hardcoding them.

## Acceptance

- Step B no longer excludes on the title alone; it requires naming which of the concrete blockers
  applies.
- The Step E summary reports exclusions with a reason each, not a bare count.
- Step C (or triage) checks for an already-existing spec covering the todo before it is queued or
  dropped.
- The rewritten step, read cold, would have put the 18 reachable todos above into the AUTO queue.
