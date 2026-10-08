<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=8, reconfirm-count=1, content-hash=ae7f9326 -->
<!-- duplicate-checked: 2026-10-06; grepped backlog + done/ for "per-commit review" and "review each unpushed", no hit. -->
# Script the per-commit review fan-out a reviewed push keeps rebuilding by hand

**Type:** skill-improvement
**Origin:** ai

## Goal
"Verify every unpushed commit before the push" runs from one written procedure instead of being
hand-built each time.

## Context
2026-10-05/06, this repo: Joe asked for every unpushed commit to be verified before `/commit push`.
The session hand-wrote the same read-only reviewer dispatch four times (57 commits in 5 slices,
then 26, then 5, then 9, then 13), each with the same verdict format, the same "judge at HEAD, never
the working tree" rule and the same NEEDS-IMPROVEMENT definition. The rounds found 8 real bugs
(including 2 regressions in safety hooks), which `/code-check` alone (structure, DRY, dead code)
does not look for. The loop-todos session then ran its own "review + push" round for the same
range. `skills/commit/SKILL.md`'s Pre-push gate has no per-commit correctness review.

## Approach
Pick one, ask Joe which:
1. Add an optional per-commit review step to `/commit`'s Pre-push gate (`/commit push review`),
   holding the dispatch template, slicing rule (about 10-13 commits per sonnet reviewer, grouped by
   area) and verdict format.
2. A small `/review-unpushed` skill that `/commit push` and `/loop-todos` both call.
Either way, keep the template's points that mattered: judge at HEAD, try one adjacent case each fix's
own tests skip, cite file:line, zero findings is valid, and a fresh reviewer for the session's own
fixes.

## Acceptance
- One written procedure exists and is referenced from `/commit`'s Push pipeline.
- `python ci/run_all.py` passes.

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): new skills/review-unpushed/SKILL.md (6eec3be), wired into /loop-todos Phase 4.5 and /commit's Pre-push gate step 1 for long unpushed stacks.
