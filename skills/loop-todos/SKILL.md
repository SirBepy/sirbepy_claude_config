---
name: loop-todos
description: Triggers on /loop-todos only. Loops /auto-do-todos until only dev-input todos remain, asking parked questions up front.
disable-model-invocation: true
argument-hint: "[max cycles, default 5] [--resumed]"
---

# /loop-todos

> `/auto-do-todos` on repeat. One question round before the first cycle, then grind, verify and
> respawn until the only todos left are ones the dev has to answer.

**Trigger:** `/loop-todos` only. Never auto-invoke.

## What this adds over a single /auto-do-todos run

Almost nothing except repetition and a stop condition, on purpose. `/auto-do-todos` already grinds
its AUTO queue via bounded `/iterate-it`, already runs `/code-check` on its own diff in its Step 9,
and already commits through `/commit`. This skill is a driver, not a second implementation:

- Phase 0 discharges every parked question ONCE, so cycles 2+ never stall on a card.
- Phase 2 makes `/test` and `/e2e` an explicit gate between cycles, not a best-effort footnote.
- Phase 4 keeps the loop alive across context exhaustion via `/respawn`.
- This skill runs no `/code-check` of its own. Step 9's diff-scoped one is the whole coverage.

## Precedence

Everything in `/auto-do-todos`'s own Precedence section stays in force for each cycle: CLAUDE.md,
`/commit` only, every `/autopilot` Hard Stop. This skill adds exactly one override, and only for
cycles running inside a loop:

**`/auto-do-todos` Step 5's second trigger (a todo carrying a pre-written `## Open questions`
block) is SUPPRESSED.** Phase 0 below is the loop's compliance with the global front-load rule, and
it leaves no `## Open questions` heading behind for that trigger to fire on anyway. Step 5's FIRST
trigger (empty AUTO queue) is not suppressed, but inside a loop it means "nothing left I can
decide", which is the loop's stop condition, so the loop ends rather than asking again.

Questions Step 8 parks DURING the loop belong to the NEXT `/loop-todos` invocation's Phase 0. They
are never asked mid-loop.

## Phase 0 - The one question round

Skipped entirely on a `--resumed` run (see Phase 4).

1. **Collect.** Grep the backlog for `## Open questions` blocks and read every unchecked `- [ ]`
   item in full, with its todo's Goal and Context.
2. **Filter before asking.** A question carrying a defensible default is a decision, not a
   question. Ask only what genuinely blocks: personal taste with no defensible default, a hard stop
   (credentials, destructive, physical action), or a large hard-to-reverse blast radius. Everything
   else is silently routed to autopilot in step 4. Same bar as `/auto-do-todos` Step 4's triage,
   applied to already-written questions.
3. **Ask.** ONE `mcp__cc_conductor__ask_user_question` call with every survivor (that tool has no
   4-question cap). Each question carries its domain tag, 2-4 concrete options with a
   recommendation, plus two standing options:
   - **"you decide - autopilot it"** - hands the fork straight back to bounded `/iterate-it`.
   - **"skip this todo"** - excludes that todo from the whole loop.

   If the card times out with no answer (roughly 30 minutes), treat every question as autopiloted.
   An unanswered card means the dev walked away, which is what this skill is for.
4. **Write the answers back, and remove the heading.** Per todo file:

   | Outcome | Edit |
   |---|---|
   | Answered | Delete the checkbox, add the answer + date as a bullet under `## Notes` (the contract's freeform-carryover section; create it if absent) |
   | Autopilot | Delete the checkbox, add `- <question> - dev delegated to autopilot on <date>` under `## Notes` |
   | Skipped | Rename the heading to `## Deferred questions` and add `<!-- loop-skip: dev deferred <date> -->` above it |

   No touched file may keep a `## Open questions` heading. That heading is the mid-loop stall.
5. **Build the skip list.** Every todo id matching `grep -l 'loop-skip' .claude/todos/*.md`. It is
   excluded from every cycle's triage and reported at the end.

## Phase 1 - Cycle

Repeat until a Phase 3 stop condition fires. Per cycle:

1. Record `CYCLE_START_SHA` (`git rev-parse HEAD`).
2. Run `/auto-do-todos` unattended, under the Precedence override above, with the skip list
   excluded from triage.
3. Note which todo ids completed, so Phase 3 can tell a productive cycle from a stalled one.

## Phase 2 - Verify between cycles

Runs after every cycle, before the next one starts.

1. `/test`. This is the loop's gate, not a repeat for its own sake: a cycle can end early or on a
   hard stop, before Step 9's floor runs.
2. `/e2e`, only if the repo matches a row in its delegate table. No suite means one line saying so,
   never an invented one.
3. **Red `/test` stops the loop.** Attempt one bounded fix inline and re-run; if still red, stop,
   leave the tree as-is, and report. Never start a new cycle on a red tree.
4. **Red `/e2e`** gets one retry, then a High-priority todo (`**Origin:** ai`) and a warning line.
   It does not stop the loop on its own.

## Phase 3 - Stop conditions

Checked after every cycle. First one to fire ends the loop:

| Condition | Meaning |
|---|---|
| Cycle cap reached | Default 5, or the number passed as an argument |
| The cycle's AUTO queue was empty | Goal state: only dev-input todos remain |
| The cycle completed zero todos | No progress, do not spin |
| `/test` still red after one fix | Phase 2 rule |
| An `/autopilot` Hard Stop | Same list `/auto-do-todos` adopts |
| The dev interrupts | Always wins |

## Phase 4 - Respawn only when context is low

After Phase 2, before the next cycle, run:

```
node ~/.claude/skills/context-left/context-left.mjs
```

At or above 35% remaining, start the next cycle in this chat. Below 35%, run `/respawn` so the
successor carries the loop on.

**The handoff prompt's FIRST characters must be the literal re-invocation**, because a slash
command only expands at the very start of a turn. Everything `/respawn` Phase 4 normally composes
goes underneath it:

```
/loop-todos <remaining cycles> --resumed

Loop state: Phase 0 discharged <date>, do not re-run it.
Cycles used: <n> of <cap>. Skipped todos: <ids>.
<the rest of /respawn's normal handoff body>
```

A `--resumed` run skips Phase 0 and reads its cycle count, cap and skip list from that state block.
Without `--resumed` the successor would re-ask everything the dev already answered.

## Phase 5 - Final report

One summary at the end covering: cycles used of the cap, todos completed per cycle with commit
shas, the stop condition that fired, questions asked and what was applied, questions autopiloted
and what was picked, todos skipped by the dev, everything Step 8 parked for the next invocation,
and the final `/test` + `/e2e` result.

## Notes

- This skill dispatches no subagents of its own; every dispatch happens inside `/auto-do-todos`
  under `refs/delegation-doctrine.md`.
- It never commits directly and never claims a todo. `/auto-do-todos` owns both.
- Backlog source of truth: `.claude/todos/` per `close/ai-todos-format.md`, resolved from the repo
  root of the session's own cwd.
