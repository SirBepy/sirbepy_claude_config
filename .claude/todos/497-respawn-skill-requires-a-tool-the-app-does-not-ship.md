<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /respawn requires a `respawn` MCP tool that this Conductor build does not expose, so the skill cannot run at all

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/respawn` work again, either by shipping the `respawn` tool or by restoring a fallback the
skill is allowed to take.

## Context

Reproduced 2026-08-22. `/respawn` was invoked and **could not execute a single phase.**

Commit `f78b339` (2026-08-22 13:11, "FEAT: point /respawn at the single-call respawn tool") rewrote
`skills/respawn/SKILL.md` from the old two-call `spawn_chat` + `close_session` contract to a single
`respawn` tool, and hardened the precondition at the same time:

> **Requires the `respawn` MCP tool** (Conductor-hosted sessions only). If it isn't in your tool
> list, stop and say so - do not fall back to `spawn_chat` + `close_session`, do not write a handoff
> file, and do not close.

**That tool does not exist.** Searched twice in a live session, by exact name (`select:respawn`,
`select:mcp__cc_conductor__respawn`) and by keyword; both returned nothing. `spawn_chat` and
`close_session` are both present, and `spawn_chat`'s own tool description still documents the old
contract verbatim: *"Used by the `/respawn` skill ... call spawn_chat FIRST, since close_session
kills the process that would make this call."*

So the skill is ahead of the daemon, and its own guard turns that into a hard stop rather than a
degraded run. The guard is correct in isolation; the problem is that nothing verified the tool had
actually shipped before the skill started depending on it.

Note the commit landed **mid-session** from a concurrent session, ten minutes after an unrelated
session's first commit, which is how it was caught at all.

## Approach

1. Establish which side is wrong. Check whether a Conductor build exposing `respawn` exists and is
   simply not installed here, or whether the tool was never implemented. `mcp__cc_conductor__*` tool
   registration happens at session start, so a session older than the build will not see a new tool
   even after an app update - rule that out first by checking a freshly started session.
2. If the tool exists in a newer build: the skill is fine and this is a version-skew note. Record
   the minimum build in the skill so the next person does not re-diagnose it.
3. If the tool does not exist: either implement it in the Conductor MCP server, or revert the skill
   to the `spawn_chat` + `close_session` ordering, which was working and whose hazard (close before
   spawn kills the process that would spawn) was already documented.
4. Whichever way it goes, the general defect is worth fixing separately: **a skill's hard
   precondition was pointed at a tool with no check that the tool shipped.** Consider whether
   `ci/check_skill_frontmatter.py` (or a sibling check in `ci/run_all.py`) can assert that any MCP
   tool a skill names as REQUIRED is one the app actually registers. That would have caught this
   before it reached a live invocation.

## Acceptance

- `/respawn` completes end to end in a real session, proven by an actual successor chat, not by
  reading the skill.
- The skill and the deployed tool set agree, and whichever one moved is recorded so the skew is not
  re-diagnosed.
- A decision is recorded on step 4: either a mechanical check exists for required-tool names, or the
  reason not to build one is written down.

## Notes

Do not "fix" this by softening the skill's guard into a silent fallback. The guard doing its job is
the only reason the failure was visible instead of producing a half-closed session with a lost
handoff. The bug is the missing tool, not the refusal to improvise around it.

Interim workaround for anyone blocked: `/handoff` writes a durable record without spawning, and the
phase plan in `.claude/todos/PLAN.md` is deliberately written so a cold session can execute from the
file alone.
