<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=4, reconfirm-count=1, content-hash=8ce1aa67 -->
# /commit's marker step should say it must be its OWN tool call

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop agents getting blocked by the commit guard on their first, correct attempt.

## Context

`~/.claude/skills/commit/SKILL.md` says:

> Before EVERY `git commit` call this skill issues, without exception, write a uniquely-suffixed marker

That reads as "write the marker, then commit", which naturally becomes one chained shell call:

```powershell
Set-Content -Path "...\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"; git commit -m "..." -- <files>
```

That is blocked every time. `commit-guard.py` is a **PreToolUse** hook, so it inspects the whole command string BEFORE any of it executes - the marker does not exist yet when the check runs. The fix is trivial once you know it (two separate tool calls), but nothing in the skill says so, and the error text ("Use the /commit skill instead") actively misleads: it implies the skill was not followed, when it was.

Hit 2026-08-12 in `claude_usage_in_taskbar` during a `/mega-todos` wrap-up. Cost one wasted round trip. The 16 builder agents in that same run were given the marker step as a numbered list with the commit as a separate step, and none of them tripped it - which is the evidence for the fix below.

## Approach

Two edits, both small:

1. In `SKILL.md`'s commit-guard paragraph, state it outright: the marker write and the `git commit` must be **separate tool calls**, because the hook is PreToolUse and evaluates the whole command before running any of it. Do not chain them with `;` or `&&`.
2. In `commit-guard.py`, add one line to the block message covering the case where the command string ITSELF contains a marker write: something like "the marker must be written in a separate tool call - this hook runs before your command does."

Point 2 is what turns a confusing block into a self-correcting one, so do it even if point 1 lands.

## Acceptance

- `SKILL.md` says "separate tool call" in the commit-guard paragraph.
- Chaining a marker write and `git commit` in one command produces a block message that explains why.
- An agent following the skill top-to-bottom commits successfully on the first attempt.

## Notes

- Duplicate of 265 - merged during /cleanup-todos 2026-08-12. This file's unique value (the 16-builder-agent evidence, and making the commit-guard.py message fix non-optional) was folded into 265 before archiving, so nothing was lost. This file also carried no numeric id prefix, violating the backlog contract in ai-todos-format.md. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
