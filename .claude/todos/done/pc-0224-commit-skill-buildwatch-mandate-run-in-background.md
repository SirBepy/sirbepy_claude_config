<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit skill's Build watch launch instruction should mandate run_in_background explicitly

**Type:** skill-improvement

## Goal

`~/.claude/skills/commit/SKILL.md`'s "Build watch" section (step 3, "Launch the watcher in the
background") should explicitly say to use the PowerShell/Bash tool call's `run_in_background: true`
parameter - never `Start-Process`/OS-level detach - so this stops recurring.

## Context

This exact mistake has now happened TWICE on the same call site:
- 2026-07-22, in `~/.claude` itself (see `[[feedback_bg_watcher_use_tool_run_in_background]]`
  memory, written after that incident).
- 2026-07-29, in `claude_usage_in_taskbar`, during a `/commit pushnbump` - launched
  `watch-build.ps1` via `Start-Process -WindowStyle Hidden` again, despite the memory already
  existing. Caught and fixed within the same turn (killed the orphan process, relaunched via the
  tool's `run_in_background` param instead), but only because the mistake was noticed by chance,
  not prevented.

The memory alone has proven insufficient to prevent recurrence - relying on recall for a
skill-mandated action is weaker than the skill's own instruction being unambiguous. The current
SKILL.md wording (`skills/commit/SKILL.md`, "Build watch" section, step 3) says "Launch the watcher
in the background" without naming HOW - that's the actual gap; a vague instruction defaults back
to whatever launch pattern is most habitual (`Start-Process`), not the harness-tracked mechanism
the rest of the skill's design (re-invocation on completion, parsing `BUILD_RESULT` from stdout)
actually depends on.

## Approach

Edit `~/.claude/skills/commit/SKILL.md`'s Build watch section, step 3, to read something like:

> Launch the watcher via the PowerShell/Bash tool call itself with `run_in_background: true` set -
> never `Start-Process`, `nohup`, or any other OS-level detach. The skill depends on being
> re-invoked with the watcher's stdout on completion; a detached process is invisible to that
> mechanism and becomes an orphan.

Keep the literal-path guidance (no `$env:`-built paths) unchanged - only the launch-mechanism
sentence needs to change.

## Acceptance

- SKILL.md's Build watch section names `run_in_background: true` explicitly, with a one-line "why"
  (harness re-invocation depends on it).
- A future `/commit push*` run launches the watcher via the tool call's background flag on the
  first attempt, no self-correction needed.

## Notes

- Duplicate of 75 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
