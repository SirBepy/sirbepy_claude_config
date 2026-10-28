<!-- Claim before executing: ~/.claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit: state that the marker must be its own tool call

**Type:** skill-improvement
**Origin:** ai

## Goal
Stop `/commit` failing its own hook on the first commit of a session.

## Context
`skills/commit/SKILL.md` says to write the commit-guard marker "before EVERY
`git commit`". Read literally that permits one shell invocation like:

```powershell
Set-Content -Path "...\.commit-marker-$guid" -Value "x"; git commit -m "..." -- <paths>
```

That fails. The `PreToolUse` hook evaluates the tool call *before* the command
body runs, so the marker does not exist yet when the guard checks, and the
commit is rejected with *"Raw `git commit` is blocked."*

Hit on 2026-08-11 in `revaire-mobile`. Cost one wasted round-trip and reads as
the skill being broken rather than mis-worded, which is the dangerous part - the
next agent may reach for `CLAUDE_COMMIT_HOOK_BYPASS=1` instead.

## Approach
Amend the commit-guard paragraph in `skills/commit/SKILL.md` to say explicitly
that the marker write and the `git commit` must be **two separate tool calls**,
and show the two-call shape rather than a one-liner. One sentence plus the
example is enough; do not restructure the section.

## Acceptance
`skills/commit/SKILL.md` states the separate-call requirement, and a fresh agent
following it lands its first commit without tripping the hook.

## Notes

- Migrated on 2026-08-12 from the dead top-level `~/.claude/todos/` path (was #03 there). That location was superseded by the repo-relative backlog on 2026-08-11; nothing reads it, so these were invisible to the Conductor app.
- Duplicate of 265 - sixth copy of the same commit-marker request. Merged during /cleanup-todos 2026-08-12. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
