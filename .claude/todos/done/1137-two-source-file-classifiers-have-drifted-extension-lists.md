<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; no live or done todo covers the two is_source_file copies -->
# Two "is this a source file" classifiers already disagree on extensions

**Type:** task
**Origin:** ai

## Goal
One stated relationship between the two source-file extension lists: either one source of truth, or
a comment on each saying why they differ.

## Context
Found by the loop-todos cycle 2 /code-check (2026-10-08, range b8e0e53..0ab7cd9), class 3:
- `skills/commit/commit-pathspec.sh` `is_source_file()` (added for the coverage-tests refusal,
  todo 1045) decides which changed files need a test-file companion.
- `hooks/_testing_floor_lib.py` `SOURCE_SUFFIXES` / `is_source_file()` decides which edits arm the
  testing-floor Stop gate (todo 427).

Same name and shape, but the bash list lacks `.kts`, `.hpp`, `.css`, `.scss`, `.less` and `.sql`,
which the python list has. That may be deliberate (stylesheets and SQL rarely get a unit test file,
but are still worth a fast-check run) or accidental; nothing says which.

## Approach
Decide whether "needs a test companion" and "arms the fast-check gate" should share one list. If
yes, have the bash side read it from the python module (the way `is_personal_repo` shells out to
`hooks/_client_repo.py`). If no, add one line beside each list naming the other and why they
differ.

## Acceptance
- Either a single extension list both callers use, or a comment beside each naming the other and
  the reason for the difference.
- `bash skills/commit/test_commit_pathspec.sh` and `python hooks/test_testing_floor_guard.py` pass.

## Notes

- Kept two lists on purpose and documented it beside each: the testing-floor list decides what is worth a fast-check run, commit-pathspec's what must ship with a test file, and .css/.scss/.less/.sql/.hpp/.kts rarely get one.
