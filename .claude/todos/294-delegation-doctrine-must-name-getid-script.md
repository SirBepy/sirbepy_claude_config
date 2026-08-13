<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# delegation-doctrine.md must name rename-session.ps1 -GetId for the screenshot path

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude/refs/delegation-doctrine.md` tells the orchestrator to hand subagents an
"already-resolved `.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/`" path but never says
how to resolve it. An orchestrator that walks the process tree gets a DIFFERENT id than the
authoritative one, producing screenshot folders `/close` can never clean up. Name the script.

## Context

Incident 2026-08-12, `claude_usage_in_taskbar`. The orchestrator resolved the ancestor by walking
`Win32_Process` parents looking for `claude.exe` and got `39824-639221583563482935`. At `/close`,
`rename-session.ps1 -GetId` returned `12232-134310477560968585` for the same session. Neither
matched, so:

- `.for_bepy/screenshots/39824-639221583563482935/` (4 files, written by a dispatched subagent) could
  not be claimed or deleted by `/close`, which is allowed to touch only its own authoritative
  subfolder.
- Worse, that folder turned out to hold files the orchestrator could not account for, so it may
  belong to a *different* session whose PID the walk happened to land on. Deleting it would have
  destroyed another session's evidence; leaving it means it is now orphaned forever.
- The same session also hand-picked a folder name (`626-e2e`, 6 files) for its own screenshots -
  equally un-cleanable, and equally a thing the doctrine does not explicitly forbid in so many words.

`close/SKILL.md` already documents the correct mechanism and the reason (todo 60: "the walk resolved
to two different PIDs at two points in the SAME session; the sessionId match is stable"). The gap is
purely that the doctrine - the file an orchestrator actually reads before dispatching - does not
repeat it or link to it. Two docs, one of which knows the answer, and the reader only sees the other.

## Approach

1. In `~/.claude/refs/delegation-doctrine.md`, in both the "Every builder prompt embeds" bullet and
   the "Canonical builder preamble" note about `.for_bepy/screenshots/`, add the literal resolution
   step: run `~/.claude/skills/close/rename-session.ps1 -GetId` (`.sh --get-id` on Unix) ONCE at the
   start of the session and reuse that id for every dispatch.
2. State the prohibition explicitly, since the failure mode is silent: never derive the id from a
   process-tree walk, and never hand-pick a folder name. Give the one-line reason (`/close` can only
   delete its own authoritative subfolder, so a wrong id is permanently un-cleanable and may collide
   with a live session's folder).
3. Consider whether `/close` Phase 3 step 3 should also REPORT un-claimable subfolders it finds
   rather than silently leaving them - that is what would have surfaced this on the first occurrence
   instead of the second.

## Acceptance

- `delegation-doctrine.md` names the script and the prohibition at both places it mentions the
  screenshot path.
- A fresh read of only that file is enough to resolve the id correctly, with no need to open
  `close/SKILL.md`.

## Notes

- Filed from a `claude_usage_in_taskbar` session per the global CLAUDE.md rule that `~/.claude`
  findings belong in this backlog, not the surfacing project's. Not executed there - editing global
  skills from a project session needs Joe's explicit say-so.
- The project-side half of this is already recorded in that project's memory
  (`feedback_subagent_overkill`), so a future session there will not repeat it even before this todo
  lands.
