<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=fb879523 -->
# Batch all GIT_FLOW-required decisions into the first question round when opening a PR

**Type:** skill-improvement
**Origin:** ai

## Goal
When a task is about to touch GIT_FLOW.md-governed territory (branch strategy, reviewer, base), ask every decision GIT_FLOW.md requires in ONE AskUserQuestion call, not spread across multiple rounds as they're discovered mid-task.

## Context
Session 2026-07-10, PR #109 (PWA splash background color fix). GIT_FLOW.md was read in full (including Â§2 "at least one human reviewer must be assigned") *before* the first AskUserQuestion of the task ("push directly to develop vs. new branch + PR"). That question was asked correctly up front. But the reviewer question ("who should review PR #109?") was only asked *after* `gh pr create` had already run - a second, separate mid-task question round for something that was fully knowable from GIT_FLOW.md at the time of the first question.

This is a direct instance of the global CLAUDE.md rule: "Front-load all questions before starting work, trivial or not. Never ask mid-task; never assume." The rule was followed for the branch-strategy question but not for the reviewer question, even though both were derivable from the same already-read document at the same point in time.

Related but distinct: `.for_bepy/ai_todos/77-create-pr-step-order-enforcement.md` covers a different /create-pr step-ordering violation (visual-scan offer bundled into the final approval question). This todo is about the *initial* GIT_FLOW decision-gathering step, not /create-pr's internal step 6/7/8 sequence.

## Approach
When a task is heading toward a PR (either explicitly requested, or discovered to be the GIT_FLOW-compliant path partway through, as happened here), read GIT_FLOW.md fully **before** asking anything, then enumerate every decision it requires for this specific PR in one pass:
- Which branch/base (Â§0/Â§1).
- Reviewer, if any (Â§2) - note: for this project specifically, skip this one entirely per `feedback-never-assign-pr-reviewer` memory; Joe never wants a reviewer assigned. Keep the general principle (batch, don't drip-feed) for OTHER projects/decisions that don't have a standing override.
- Any deviation confirmation needed (Â§7), if the request contravenes the flow.

Ask all applicable ones together via AskUserQuestion's multi-question array (up to 4 questions per call) rather than a single question now and a follow-up later.

## Acceptance
Next time a task's first GIT_FLOW-governed question is asked, confirm (in the transcript) that all then-knowable GIT_FLOW decisions for that PR were included in the same AskUserQuestion call - no second "oh, also need to ask X" round for something that was already readable from GIT_FLOW.md at the time of the first question.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 78; renumbered to 13 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: in `create-pr/SKILL.md` step 1 Preconditions, when `GIT_FLOW.md` exists at repo
  root, read it fully before asking anything and batch every decision it implies (branch and base,
  reviewer, deviation confirmation) into ONE `AskUserQuestion`. The skill currently has zero
  `GIT_FLOW` handling, which is the concrete edit target the todo never named. This was produced by
  a strict second-pass re-triage that specifically asked whether a defensible answer exists without
  the dev; it concluded yes. Not executed only because the session ended.
- completed, commit 00737e5
