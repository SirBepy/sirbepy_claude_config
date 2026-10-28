<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=50bccc1f -->
# /commit: state that the marker must be its own tool call

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `~/.claude/skills/commit/SKILL.md` say that the commit-guard marker has to be written in a SEPARATE tool call from `git commit`, not merely "immediately before" it.

## Context

`SKILL.md`'s commit-guard section says to write the marker "immediately before EVERY `git commit`". Read literally that permits one command doing both:

```powershell
Set-Content -Path "...\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"; git commit -m "..." -- <files>
```

That form ALWAYS fails. The `PreToolUse` hook evaluates the whole command string before any of it executes, so at hook time the marker does not exist yet and the commit is blocked:

```
[commit-guard] Raw `git commit` is blocked. Use the /commit skill instead - it writes the authorisation marker this hook checks.
```

Hit on 2026-08-12 in `claude_usage_in_taskbar`. The failure is self-inflicted and costs a wasted tool call plus a confusing error that reads like the skill was not invoked at all, which is misleading precisely when the skill IS being followed correctly.

Also relevant: `~/.claude/skills/mega-todos/SKILL.md`'s injected commit block carries the same wording, so its builder agents can hit this too. That file should get the same one-line clarification.

## Approach

In `commit/SKILL.md`'s commit-guard paragraph, add roughly: "Write the marker in its own tool call. The PreToolUse hook inspects the whole command string BEFORE it runs, so chaining the marker and the commit into one invocation (with `;` or `&&`) is always blocked - the marker does not exist yet at hook time."

Mirror the same sentence into `mega-todos/SKILL.md`'s injected commit block, step 1.

In `hooks/commit-guard.py`, extend the rejection message for the case where the blocked command string ITSELF contains a marker write: "the marker must be written in a separate tool call - this hook runs before your command does." Not optional. The current text sends the reader toward "invoke /commit" when they already are, so the block is unrecoverable without outside knowledge.

## Acceptance

- Both skill files state the separate-tool-call requirement explicitly.
- The wording says WHY (hook inspects before execution), so nobody re-optimises it back into one call.
- Chaining a marker write and `git commit` in one command produces a block message that explains why.

## Open questions

- Todo `09` wants to REMOVE the two-call cost entirely (hook redesign). If `09` lands first, this todo's wording becomes wrong and must be rewritten, not just kept. Sequence `09` before this one, or accept that this is the interim fix.

## Notes

- Merged from a duplicate during /cleanup-todos 2026-08-12. That copy's evidence: in the same `/mega-todos` run, 16 builder agents were handed the marker step as a numbered list with the commit as its own step and none of them tripped the guard - which is what makes the separate-call framing the actual fix rather than a guess.
- completed, commit 0796403
- This exact fix was independently filed 4 separate times: 98, 263, this file's own id-less
  predecessor (`done/commit-marker-must-be-its-own-tool-call.md`), and 265 itself. Consolidated
  by todo 286 on 2026-08-13; the other three were deleted (git history preserves them).
