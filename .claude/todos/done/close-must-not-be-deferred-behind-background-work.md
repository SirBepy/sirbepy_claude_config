<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=8, reconfirm-count=1, content-hash=c936744e -->
# /close: state that Phases 0-4 run immediately, and narrow the background-work gate

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it structurally impossible to read `/close` as "run this once the optional in-flight work
finishes". Today the skill never says when to START, and its only mention of background work is the
Phase 6 skip condition, which is easy to over-apply to the whole skill.

## Context

2026-08-19, claude_usage_in_taskbar session. Joe asked "when youre done lets /close" while a
background `cargo test` rerun was in flight. I answered "once it returns I'll run /close" and ended
the turn having run zero phases. The host marked the chat done anyway, so the retrospective, the
code-check findings, the memory writes and the todos were all nearly lost. His correction: *"okay
well, this chat is marked as done... so... you didnt /close properly"*.

The skill text that permitted this reading is Phase 6's list: "Any background work is still running
in this session: spawned `Agent` with `run_in_background: true`, active `/loop`, or pending
`ScheduleWakeup`." That list is about the TERMINAL KILL only, but with no counterweight elsewhere it
reads as a global "wait until nothing is running" gate. Note the list also omits a plain
`run_in_background: true` Bash command, which is what was actually in flight.

## Approach

In `~/.claude/skills/close/SKILL.md`:

1. Add one line under `## When to run`: Phase 0 starts in the SAME turn `/close` is invoked.
   Background work never delays Phases 0-5; only Phase 6 is gated. Persistence is the point of the
   skill, so it must not be contingent on optional work landing green.
2. In Phase 6's skip list, add a long-running background Bash command to the enumerated kinds, so the
   gate is complete rather than implicitly narrow.
3. Consider a note in the Anti-patterns section: "Promising to run /close later. If the dev asked for
   it, its phases run now."

## Acceptance

- SKILL.md states the start-immediately rule where a reader hits it before Phase 0.
- Phase 6's background-work list names background Bash commands alongside Agent/loop/wakeup.
- No other phase implies a wait-for-quiet precondition.

## Notes

- Archived via mega-todos 2026-08-19. d808b01: the close skill now states Phases 0-5 start in the same turn it is invoked, and background work gates Phase 6 only. Plain backgrounded Bash commands added to the Phase 6 skip list.
