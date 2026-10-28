<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=c196e34f -->
# Canonical builder preamble doesn't restate the global-~/.claude-edit-ban rule

**Type:** skill-improvement
**Origin:** ai

## Goal

Add the "never edit skills/hooks/global CLAUDE.md from a project-repo session unless the dev says
so in THAT session" rule to `refs/delegation-doctrine.md`'s canonical builder preamble, so a
dispatched subagent doesn't have to infer it.

## Context

Found 2026-08-13, `/close` retrospective of a zng-biller `/auto-do-todos` run. A builder subagent
dispatched to fold a login-preamble recipe into a skill doc was told (by the orchestrating session,
correctly reading the todo's own text) to "add a section to
`~/.claude-personal/skills/flutter-e2e/SKILL.md` if it exists... OR create a small project-level
skill/step file if that's a better fit." The agent found no file at that exact path (it actually
lives at `~/.claude/skills/flutter-e2e/SKILL.md`, a different directory), concluded "so option 1
applies directly," and edited the global skill file in place from inside the zng-biller project
session - exactly what CLAUDE.md's own "Never do global `~/.claude` work from inside a project
session unless Joe says so in that session" rule forbids. Caught and reverted by the orchestrator
before commit; no lasting damage, but it's the SECOND documented occurrence of this exact failure
mode (see CLAUDE.md's own "Past incident (2026-08-07)" note about `windows_taskbar_widgets`, which
this rule's wording already exists specifically to prevent).

Todo `51-canonical-subagent-dispatch-preamble.md` (done, 2026-08-08) added a canonical builder
preamble to `delegation-doctrine.md` covering PowerShell/chaining/working-dir/screenshot-subfolder/
git-reset bans - but not this one. A subagent dispatched from a project repo has no way to know
"this session" means the ORCHESTRATOR's session, not its own, unless told explicitly - it reads
"edit this global file" as a plain instruction with no context that doing so from here is
off-limits without the dev's say-so in the parent conversation.

## Approach

Add one line to the canonical preamble in `refs/delegation-doctrine.md`'s `## Canonical builder
preamble` section: something like "Never edit files under `~/.claude/` (skills, hooks, settings,
global CLAUDE.md) even if a task description points at one - that requires the dev's explicit
say-so in the CURRENT session, which a subagent cannot verify. If a task seems to require it, stop
and report back to the orchestrator instead of editing." This mirrors the existing git-reset/stash
ban's shape (a category of edit that's fine for a human-directed session but not a default subagent
action).

## Acceptance

- The canonical preamble in `refs/delegation-doctrine.md` contains this line.
- A future dispatch that copy-pastes the preamble carries the ban automatically, without the
  orchestrator having to remember to add it per-task.

## Notes

The orchestrator caught this one before it shipped, so this is a near-miss writeup, not a damage
report - worth fixing the systemic gap anyway since the same near-miss already happened once before
under a different project (`windows_taskbar_widgets`, 2026-08-07) and CLAUDE.md's own rule text
exists because of it.
- Completed via /auto-do-todos 2026-08-15: canonical builder preamble now carries a one-line ban on editing ~/.claude (skills, hooks, settings, global CLAUDE.md) from a dispatched subagent, placed beside the git-reset ban it mirrors. No new placeholder, so the four-placeholder paragraph stayed accurate.
