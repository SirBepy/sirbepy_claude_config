<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# A project memory file still teaches the retired process-tree screenshot id

**Type:** task
**Origin:** ai

## Goal

Correct the last copy of the retired screenshot-subfolder convention so no session gets taught the
scheme that made folders un-cleanable.

## Context

Todo 339 landed 2026-08-15: `rename-session.ps1 -GetId` is now the single source of truth for the
`.for_bepy/screenshots/<id>/` subfolder id, replacing the `<claude-ancestor-pid>-<ancestor-start-ticks>`
process-tree walk that `rename-session.ps1` itself calls "fallback only, best-effort/unstable". The
old scheme is why three orphaned subfolders plus 49 loose root-level files exist in zng-biller alone
that `/close` could never prove ownership of.

That fix swept `CLAUDE.md`, `skills/close/`, `skills/screenshot/`, `skills/mockup/` and
`skills/flutter-e2e/`. A repo-wide grep of `*.md` under `skills/`, `refs/` and `CLAUDE.md` is now
clean.

One copy survives outside that sweep, reported by the builder:
`projects/c--Users-tecno-Desktop-Projects-claude-usage-in-taskbar/memory/feedback_subagent_overkill.md:16`
still describes the process-tree convention. It is a per-project Auto Memory file, which loads into
every session for that project, so it will keep teaching the retired scheme.

Historical copies inside `.claude/todos/` and `.claude/todos/done/` are the record of the bug and
are deliberately left alone.

## Approach

Per the memory rubric in `~/.claude/refs/memory-rubric.md`, this is an UPDATE, not a rewrite: the
memory's actual subject is subagent overkill, and the screenshot path is incidental detail that has
gone stale. Read the file first and decide whether the line should be corrected to point at
`rename-session.ps1 -GetId` or simply dropped, since a memory about dispatch cost may not need to
name a screenshot path at all.

Keep the edit line-scoped. Other sessions share these files and a whole-file overwrite from a stale
read destroys concurrent writes.

Record the absolute date and the reason, per the rubric, so a future session can see why it changed.

## Acceptance

- No live guidance anywhere on this machine, memory files included, names the process-tree walk as
  the way to derive the screenshot subfolder id.
- The memory's own point about subagent overkill survives the edit intact.
