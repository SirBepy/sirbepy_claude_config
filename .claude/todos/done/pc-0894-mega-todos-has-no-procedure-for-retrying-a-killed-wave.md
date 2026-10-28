<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "mega-todos", "session limit", "killed", "resume". 855 is
     the archival half, 879 is the auto-backgrounding half, 872 is the pathspec-sweep half. None
     covers what to do with the half-finished tree a killed wave leaves behind. -->
# /mega-todos has no procedure for retrying a wave that was killed mid-flight

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `skills/mega-todos/SKILL.md` an explicit retry procedure for a wave killed by an account
session limit or a process exit, so the orchestrator does not have to invent one under a half-built
tree every time.

## Context

Hit twice in one run, 2026-09-02, batch 3 of the `~/.claude` backlog.

Wave 1 dispatched 9 lanes; 7 agents died instantly on `You've hit your session limit`. Wave 2
(the retry) completed all 8 agents but the Claude Code process exited before the workflow returned
its result.

The skill covers a *barrier* failure ("A barrier failure is fixed forward, never reverted ...
dispatch a repair agent scoped to the failing lane") but says nothing about a *dispatch* failure,
which leaves a materially different mess:

1. **Some killed builders leave uncommitted, half-finished work in a shared tree.** Wave 1 left
   todo 402's diff complete-but-uncommitted and todo 794's genuinely half-done (one of its two
   scripts converted, the new shared helper created, the second script untouched). Nothing in the
   skill says how to tell those two apart or what to do with either. Both were handled by
   improvising: 402 was verified and committed from the main thread, 794's retry brief was rewritten
   to open with "THERE IS PRE-EXISTING UNCOMMITTED WORK IN YOUR OWNED FILES AND IT IS YOURS TO
   FINISH ... judge it rather than assuming it is correct."
2. **`resumeFromRunId` is the obvious tool and it does not fit.** Resuming replays cached results for
   completed agents and re-runs the failed ones with their ORIGINAL prompts - but a retry prompt
   usually has to change, precisely because the tree is no longer clean. Both retries here were
   authored as fresh scripts instead, duplicating ~200 lines of preamble each time.
3. **The lane map has to be recomputed**, because completed todos must be dropped from it while
   in-lane ordering has to survive for the ones left.

## Approach

1. Add a "Retrying a killed wave" section to `skills/mega-todos/SKILL.md`, after Step D. Order the
   triage explicitly, because the expensive mistake is re-dispatching a builder onto work that is
   already done:
   - `git log` first. An agent that committed is DONE; drop it from the retry map entirely.
   - Then `git status`. Anything dirty in a dead builder's owned files is its partial work.
   - Then, per partial, decide: complete-and-verifiable (main thread runs the verify floor and
     commits it, cheaper than a re-dispatch) versus genuinely half-done (re-dispatch, with the
     partial DESCRIBED in the brief and an explicit instruction to judge it rather than trust it).
2. State the `resumeFromRunId` limitation plainly so the next orchestrator does not discover it
   under pressure: resume is only correct when the retry prompts are unchanged, which a dirty tree
   usually makes false.
3. Extract the injected preamble + commit block into something a retry script can reference rather
   than re-paste. **Check `472` first** - it already proposes exactly this ("`/mega-todos`' builder
   block is hand-copied into every dispatch") and this todo is a second, independent argument for
   it, not a separate solution. If `472` is done, this step is already covered; say so and drop it.
4. Fold in the one prevention that demonstrably worked, since it is currently only in a memory and
   not in the skill: every builder prompt tells the builder to commit as soon as its work is
   verified and before writing its report. Wave 2's 8-for-8 survival through a process exit is the
   evidence. Cross-reference `872`, which is the other half of the injected block's known gaps.

## Acceptance

- `skills/mega-todos/SKILL.md` has a retry section covering all three of: an agent that committed, an
  agent that left complete-but-uncommitted work, and an agent that left half-done work.
- It states when `resumeFromRunId` is and is not usable.
- The commit-before-reporting instruction is in the injected builder block itself, not only in a
  memory.
- The recovery path for a lost workflow result is named: the run's `journal.jsonl` under its
  transcript dir carries each completed agent's full structured return value even when the run's own
  result is gone.

## Notes

- Worth roughly a 7. Two occurrences in one run, and each cost real reconstruction time that a
  written procedure would have removed.
- Related but distinct: `855` (archival is hand-rolled at every barrier), `872` (the injected commit
  block omits `/commit`'s working-tree diff check), `879` (builders park when the harness
  auto-backgrounds a long run), `472` (the builder block is hand-copied per dispatch). This one is
  the dispatch-failure recovery gap; none of the four covers it.
- Completed in /mega-todos wave 1, commit 5d501ec: /mega-todos now has a Retrying a killed wave section covering the committed, complete-but-uncommitted and half-done states plus what resumeFromRunId can recover.
