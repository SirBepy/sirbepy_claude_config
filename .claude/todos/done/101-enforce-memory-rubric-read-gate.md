<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforce the "read memory-rubric before first write" gate instead of relying on recall

**Type:** skill-improvement

## Goal

Make the "read `~/.claude/refs/memory-rubric.md` once per session, before the first memory write" rule (stated in global CLAUDE.md's Memory Discipline section, and repeated in `close/SKILL.md` Phase 3 step 1) actually enforced, instead of depending on the model remembering to do it unprompted.

## Context

Session `8d410bfe-808c-4bb7-b005-10f59d250db1` (2026-08-03, zng-app) wrote a memory update (`Edit` to `project_sc54926_plaid_skip_flag.md`) and later two new memory files, all before ever reading `~/.claude/refs/memory-rubric.md` this session. The rubric was only actually read afterward, during this same session's `/close` Phase 3, well after the writes had already happened. The rule is documented in two separate places (global CLAUDE.md, and this skill's own Phase 3 step 1) and was still silently skipped, because nothing actually checks or reminds - it's pure unprompted recall.

No concrete harm resulted this time (the writes happened to follow the gate's spirit anyway), but that's luck, not enforcement. This is exactly the "enforcement gap, not a 'be more careful' fix" case `/close` Phase 1 step 4 asks to flag.

## Approach

Not spec'd here - flagging for `/bepy-skill-creator` or a future review to weigh options, per this skill's own anti-pattern warning against drafting fixes inline. Directions worth considering:
- A session-start hook/reminder that surfaces the rubric path the first time a memory-writing tool call is about to fire.
- A stronger textual gate in CLAUDE.md itself (current wording is easy to read past).
- Some lightweight self-check the memory-writing step itself performs (e.g. "have I read the rubric this session?" as an explicit first line of any memory-write action).

## Acceptance

- A future session's first memory write either already followed a rubric read, or gets prompted to do one first - not solely dependent on the model recalling a CLAUDE.md rule unprompted.

## Notes

Low severity this time (no bad memory resulted), filed because the near-miss pattern (documented rule, zero enforcement, silently skipped) will keep recurring otherwise.
- Dropped via /cleanup-todos 2026-08-11: the todo itself records that zero harm resulted; enforcement for a rule already followed. Confirmed by dev 2026-08-11.
