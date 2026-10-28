<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-06; done/392 swept skills/ for this bug class before step 4b existed; 1092 is the same fix in clockify-reconciliator, a different file. -->
# zirtue-release-backfill step 4b's subagent dispatch does not point at the builder preamble

**Type:** skill-improvement
**Origin:** ai

## Goal
Step 4b of `skills/zirtue-release-backfill/SKILL.md` builds its per-ticket subagent prompts from the
canonical preamble, so they pass `hooks/dispatch-preamble-guard.py` first time.

## Context
Found by the 2026-10-06 pre-push /code-check (Step 4, quoting `skills/bepy-skill-creator/SKILL.md`'s
FAIL checklist rule that every subagent dispatch carries the never-commit boilerplate). 03650c9 added
step 4b (`skills/zirtue-release-backfill/SKILL.md:211`), which dispatches "a read-only
`general-purpose` sonnet agent" per ticket and names none of the three markers
`refs/builder-preamble.md`'s "What the guard actually enforces" lists. done/392 fixed this exact
class across skills/ when this file had no dispatch at all; todo 1092 is the same gap in
clockify-reconciliator.

## Approach
Add one sentence to step 4b: paste the canonical preamble from `~/.claude/refs/builder-preamble.md`
with the `READ-ONLY DISPATCH` opt-out (the dispatch never writes to Shortcut).

## Acceptance
- Step 4b names `refs/builder-preamble.md`.
- `python ci/run_all.py` passes.

## Notes

- Done in loop-todos cycle 3 (2026-10-06): step 4b tells the dispatcher to paste refs/builder-preamble.md with the READ-ONLY DISPATCH opt-out, same wording as clockify 7a (todo 1092).
