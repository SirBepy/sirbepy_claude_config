<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=1, content-hash=7a1948ea -->
# /commit's marker write must be a SEPARATE tool call, not chained with the commit

**Type:** skill-improvement

## Goal

Stop `/commit` from being blocked by its own commit-guard hook on the first attempt, every time, in every repo.

## Context

`~/.claude/skills/commit/SKILL.md` tells the agent to write the authorisation marker "before EVERY `git commit` call this skill issues". It does not say the marker write must be its own tool invocation.

The natural reading is to chain them in one shell call:

```powershell
Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"; git commit -m "..." -- <files>
```

That always fails. `commit-guard.py` is a **PreToolUse** hook: it inspects the command string before the tool runs, so at hook-evaluation time the `Set-Content` has not executed and no fresh marker exists on disk. The hook sees a raw `git commit` and blocks with "Raw `git commit` is blocked. Use the /commit skill instead" - which is actively misleading, because the skill *was* being followed.

Hit for real on 2026-08-11 in `claude_usage_in_taskbar` while committing the MCP idle-timeout fix. Cost one wasted tool call plus the moment of wondering whether the skill itself was broken. The error text points at the wrong cause, so the obvious next move (re-read the skill, or reach for `CLAUDE_COMMIT_HOOK_BYPASS=1`) is wrong in both directions.

This is not repo-specific and not Windows-specific. It is inherent to PreToolUse evaluation order, so it reproduces on every commit in every repo unless the agent already happens to split the calls.

## Approach

One sentence added to the commit-guard marker block in `~/.claude/skills/commit/SKILL.md`, stated as a constraint rather than a suggestion:

> Write the marker in its own tool call. The guard is a PreToolUse hook and evaluates the command string before it runs, so chaining the marker write and `git commit` in a single shell invocation is always blocked.

Optionally also improve `~/.claude/hooks/commit-guard.py`'s rejection message: if the blocked command *contains* a `.commit-marker-` write, say "marker written in the same call - split it into two calls" instead of the generic "use the /commit skill". That turns the most common failure into a self-correcting error.

Check whether `/mega-todos`' injected commit block (step 1) has the same ambiguity - builder agents follow that text verbatim and would each burn a call on the same mistake.

## Acceptance

- A fresh session following `/commit` verbatim commits on the first attempt, with no guard rejection.
- The guard still blocks a genuine raw `git commit` with no marker.
- `/mega-todos`' injected block carries the same clarification.

## Notes

- Duplicate of 265, which covers both skills/commit/SKILL.md and mega-todos' injected commit block - merged during /cleanup-todos 2026-08-12. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
