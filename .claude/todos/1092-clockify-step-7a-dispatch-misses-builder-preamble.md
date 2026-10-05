<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-05; grepped backlog + done/ for "7a" + "preamble" in clockify-reconciliator, no hit. -->
# clockify-reconciliator step 7a's subagent dispatch does not point at the builder preamble

**Type:** skill-improvement
**Origin:** ai

## Goal
Step 7a of `skills/clockify-reconciliator/SKILL.md` tells the session to build its two subagent
prompts from the canonical preamble, so they pass `hooks/dispatch-preamble-guard.py` first time.

## Context
Found by the 2026-10-05 pre-push /code-check (Step 4, quoting `skills/bepy-skill-creator/SKILL.md`'s
FAIL checklist: "Every subagent dispatch prompt includes the subagents-never-commit boilerplate").
`skills/clockify-reconciliator/SKILL.md:297-316` dispatches two `model: 'sonnet'` subagents and
only says "Both are READ-ONLY DISPATCH". Per `refs/builder-preamble.md`'s "What the guard actually
enforces", `READ-ONLY DISPATCH` exempts only the screenshot-id marker; the staging line and the
`run_in_background` + `FORBIDDEN` line are still required, or the guard rejects the dispatch.
Sibling dispatches added the same week (`skills/audit/SKILL.md:61-62`, `skills/commit/SKILL.md`'s
pre-push todo sweep) point at the preamble explicitly.

## Approach
Add one sentence to step 7a: paste the canonical preamble from `~/.claude/refs/builder-preamble.md`
with the `READ-ONLY DISPATCH` opt-out.

## Acceptance
- Step 7a names `refs/builder-preamble.md`.
- `python ci/run_all.py` passes.
