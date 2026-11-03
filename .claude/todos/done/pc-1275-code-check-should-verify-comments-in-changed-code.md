<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-0450 is about when /code-check fires, pc-1261 about one push's findings; neither covers comment accuracy -->
# /code-check should verify that comments in changed code still match it

**Type:** skill-improvement
**Origin:** dev
**Summary:** /code-check checks that every comment and doc comment in code the range changed is still true, and skips that pass for files whose changes touch nothing a comment describes.

## Why

Joe, 2026-10-29: "personally i believe this should be something we always do in /code-check if we changed a function or a comment, we gotta check that the comment makes sense still. ofc if we changed smth in a file, but it doesnt affect any comments, then theres no point looking into that". A zng-app push that deleted an old flow left comments saying "sign-up detour" and one pointing at a deleted `LoanApplication.currentStep`; /code-check did not catch them, a separate docs review found them.

## Goal

A new step in `skills/code-check/SKILL.md` that, for each function or block the range changes, reads the comments and doc comments attached to it and to the symbols it references, and records a finding when one is now false. A changed file whose edits touch nothing a comment describes costs no comment pass.

## Context

- `skills/code-check/SKILL.md` Steps 1-4 cover size, DRY, dead code and written conventions. None checks comment truth.
- Root `CLAUDE.md` Code Style already says "A wrong comment is worse than none (AI readers trust it), so fix or delete it when its subject changes", so a stale comment is a breach of a written rule and fits Step 4's "quote the rule" bar.
- It is mechanical enough to be class 1 in Step 4a when the fix is a wording change; the exercise test is a grep for the removed symbol or phrase.

## Approach

Add the step after Step 3, scoped to hunks, not whole files. Judge with the quoted CLAUDE.md rule. Keep the finding shape the other steps use.

## Acceptance

Run /code-check on a range that deletes a function referenced in a nearby doc comment: it reports the comment. Run it on a range whose edits touch no comment's subject: it reports nothing about comments.

## Notes

- Fixed in a331d98.
