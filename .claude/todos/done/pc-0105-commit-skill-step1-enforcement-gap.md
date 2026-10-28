<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=5bdfd97b -->
# /commit step 1 (read commit-style.md) has no enforcement, gets silently skipped

**Type:** skill-improvement

## Goal

Make the global `/commit` skill's step 1 ("Check for project-level overrides at `.claude/commit-style.md`. If it exists, read it fully") actually enforced, instead of depending on the model remembering to do it before the first `git commit` of a session.

## Context

sc-54844 (2026-08-10, zng-app): committed a fix, then a self-caught `/code-check` nit was committed as a *second, separate* commit. `.claude/commit-style.md`'s Grouping section already says explicitly: "One ticket = one commit (when unpushed)... Undo the previous commit (`git reset --soft HEAD~1`), restage everything together, and create a single fresh commit." Joe caught it: "why is it commited seperately? why not commit it together? i prefer folding than commiting new." The rule was sitting in a repo-committed file the skill's own step 1 says to read - it was never actually `Read`, just skipped past, same as todo [[87-enforce-memory-rubric-read-gate]]'s memory-rubric case.

This is the same enforcement-gap shape as that todo, but for a different skill/rule: a documented instruction with zero enforcement, silently skipped, model-recall-dependent.

## Approach

Not spec'd here, per this skill's own anti-pattern against drafting fixes inline. Directions worth considering (mirror todo 87's list):
- Give `/commit` step 1 the same explicit "precondition, checked right here" callout step 8 already has for the comment-noise prefilter, forcing a visible self-check before the first `git commit` call.
- A hook that fires on the first `git commit` of a session in a repo with `.claude/commit-style.md` present and nudges/blocks if the file hasn't been read yet this session.
- Fold both this and todo 87 into one general "read-gate enforcement" pattern if a shared mechanism emerges (session-start reminder, generic pre-tool-use check) rather than solving each skill one at a time.

## Acceptance

- A future session's first `/commit` in a repo with `.claude/commit-style.md` either already read it, or gets prompted to before running `git commit` - not solely dependent on model recall.

## Notes

Low severity this time (caught immediately, folded via `git reset --mixed` with no push in between). Filed because it's the second confirmed instance of this exact failure shape (see todo 87) - worth considering a shared fix rather than two skill-specific patches.
- completed, commit 6660f6c
