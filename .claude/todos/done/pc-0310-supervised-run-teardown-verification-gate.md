<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Skill: supervised-run teardown should prompt for undelivered verification artifacts

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a checkpoint to `/supervised-run`'s stop/teardown step (or the CLAUDE.md "UI & visual changes" rule it serves) that catches "I took a screenshot to verify this but never sent it" before the dev server gets stopped and the evidence becomes hard to re-capture.

## Context

2026-07-17, zng-biller: brought up the dev server via `/supervised-run` specifically to verify a UI fix visually. Took real, successful screenshots proving the fix worked. Then, in the same breath as cleaning up throwaway artifacts, deleted the screenshots without ever calling `SendUserFile` - violating the global CLAUDE.md rule "User-facing/visual change: show Joe ... capture a screenshot via SendUserFile." Two attempts to re-capture after restarting the server both failed on a Flutter-web dev-server blank-canvas flakiness, permanently losing the evidence (the underlying fix was still correct and committed - only the delivery of proof was lost).

The root issue: nothing in the `/supervised-run` flow (or the broader verification habit) pauses to ask "did the required delivery step (SendUserFile) actually happen" before the server - and the ability to cheaply re-verify - goes away.

## Approach

Add a line to `~/.claude-personal/skills/supervised-run/SKILL.md`'s stop guidance (or wherever the "stop the process when done" step lives): before calling `/procs/<id>/stop` after a verification session that involved screenshots, confirm `SendUserFile` was actually called for any screenshot that CLAUDE.md's UI-change rule requires sending - if not, send it now, THEN stop the server. This turns an easy-to-skip mental checklist item into something the skill's own text nudges on, similar to how the proxy-port note (a prior landed todo) turned a recurring gotcha into documented skill text.

Related self-correction: also never delete a throwaway screenshot before it has been sent, and use `.for_bepy/screenshots/` for throwaway verification images rather than an arbitrary `C:\tmp` path, per CLAUDE.md's own "UI & visual changes" section.

## Acceptance

- `/supervised-run`'s SKILL.md (or CLAUDE.md's UI & visual changes section) explicitly says: don't stop a dev server started for visual verification until any required screenshot has been sent via SendUserFile.
- A future session that takes a verification screenshot and forgets to send it gets caught by this checklist before the server (and the cheap ability to re-verify) goes away.

## Notes

Relocated from 46 in zng-biller via /cleanup-todos 2026-08-13: targets the global ~/.claude/skills/supervised-run/SKILL.md, nothing zng-biller-specific in the fix itself.
- Done 2026-08-13. skills/supervised-run/SKILL.md's Stop bullet now gates teardown on verification actually having been delivered: before sv.ps1 stop, confirm SendUserFile was called for any verification screenshot taken this session, send it first if not, and never delete a throwaway screenshot before it has been sent. Implemented as the todo specified, no deviation needed.
