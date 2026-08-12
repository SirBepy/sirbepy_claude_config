<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=1, content-hash=2d44b09b -->
# /commit: say that the marker must be a SEPARATE tool call from the commit

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop every session losing a round trip to the same hook rejection when it first commits.

## Context

Hit on 2026-08-12 in the hubbub project, on the first commit of the session.

`~/.claude/skills/commit/SKILL.md` opens with the commit-guard marker instruction:

> Before EVERY `git commit` call this skill issues, without exception, write a uniquely-suffixed
> marker: `Set-Content -Path "...\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"`

Read literally, batching that `Set-Content` and the `git commit` into one PowerShell call satisfies
"before every git commit" - the marker is written first within the command. That is what a session
naturally does, because the skill also encourages batching sequential commands into one call.

**It always fails.** The `PreToolUse` hook evaluates the whole command string *before* any of it
runs, so at hook time the marker does not exist yet:

```
[commit-guard] Raw `git commit` is blocked. Use the /commit skill instead - it writes the
authorisation marker this hook checks.
```

The error message compounds it: it says to use the /commit skill, which is exactly what the session
IS doing. So the natural next move is to doubt the skill invocation rather than the call structure.

Cost is small per occurrence (one wasted call) but it is per-session and universal, and the fix is
one sentence.

## Approach

In `~/.claude/skills/commit/SKILL.md`, at the marker instruction, add an explicit constraint -
something like: **"Write the marker in its own tool call. The hook inspects the command string
before execution, so a marker written in the same call as `git commit` does not exist yet when the
hook runs."**

Optionally also soften the hook's own message in `~/.claude/hooks/commit-guard.py` to name this
case, since "use the /commit skill" misdirects a session that is already following it. Lower value
than the SKILL.md line; the doc fix alone prevents the mistake.

## Acceptance

- A cold session following SKILL.md verbatim commits successfully on its first attempt.
- The batching guidance elsewhere in the skill no longer contradicts the marker step.

## Notes

- Filed from a hubbub session per the CLAUDE.md rule that global `~/.claude` findings belong in this
  repo's backlog, never the surfacing project's. No global files were edited from that session.
- Unrelated to the marker's own purpose; the multi-marker design (oldest-fresh consumed, others
  left) works correctly and handles concurrent sessions as documented.
- Duplicate of 265, which is the strict superset of this ask - merged during /cleanup-todos 2026-08-12. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
