<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=53392849 -->
# Todo creation has no content-duplicate check, only an id-collision guard

**Type:** skill-improvement

## Goal

Stop `/handoff`, `/create-todo` and `/close`'s Phase 3 from silently filing a todo that duplicates one already sitting in the same backlog.

## Context

`~/.claude/skills/close/ai-todos-format.md` has a "Creation race guard" but it only protects against two sessions grabbing the same numeric id. There is nothing about the far more likely failure: filing a second todo for work another session already wrote up.

Hit for real on 2026-07-30. A session was asked to write a handoff in `zng-admin` for the Partner service fee fix (Shortcut SC-54910). Two todos already covered it: `47-fix-partner-fee-copy-and-preview-calculator.md` (with much better history than the new session could reconstruct, including the Slack quote establishing the fee model) and `48-handoff-resume-partner-fee-fix-after-stevan-reply.md`. Both were already pinned in PLAN.md.

The duplicate was caught only because scanning for the next free id happens to print every filename, and one of them read as obviously related. That is luck, not process. With less obvious slugs it would have shipped a third redundant todo, and the new one would have been worse, because the older file held session history that could not be reconstructed.

Note the correct behaviour once a duplicate IS found: the contract says a handoff never edits or deletes a prior handoff, so the right move is a new superseding file that references the old ones, not an edit. That part worked fine. Only the detection is missing.

## Approach

Add a step to the handoff/creation flow in `~/.claude/skills/close/ai-todos-format.md`, in the "Backlog file: filename and id" section next to the existing race guard:

1. Before writing, grep the backlog and `done/` for overlap with the new todo's subject. Cheap version: match on the slug's significant words plus any Shortcut ticket id mentioned in the body.
2. If a candidate match exists, read it before writing anything.
3. If it genuinely covers the same work, either write a superseding handoff that references it by id (per the existing never-edit-a-prior-handoff rule) or skip creation and say so, rather than filing a silent duplicate.

Keep it cheap. This should be one grep and at most one file read, not a semantic dedupe pass. `/cleanup-todos` already exists for the heavyweight version and runs on demand; this is about preventing the duplicate at write time.

## Acceptance

- Filing a handoff into a backlog that already contains a todo for the same ticket or subject surfaces the existing one instead of silently adding another.
- The existing id-collision race guard still works unchanged.
- No new blocking prompt in unattended runs (`/sleep-when-done`, autopilot): finding a duplicate there should log and supersede, not stop and ask.

## Notes

- completed, commit e6f2199
