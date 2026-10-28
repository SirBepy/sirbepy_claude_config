<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new defect in review-unpushed's dispatch template -->
# review-unpushed and code-check reviewer prompts let a read-only reviewer delete directories it did not create

**Type:** skill-improvement
**Origin:** ai
**Summary:** A reviewer dispatched by /review-unpushed or /code-check never deletes a path it did not create in that dispatch.

## Why

On 2026-10-28 a read-only reviewer ran rm -rf on /c/tmp/skills and /c/tmp/refs, which may have existed before the run.

## Goal
A reviewer dispatched by `/review-unpushed` or `/code-check` never deletes a path it did not create in that dispatch.

## Context
2026-10-28, release session push gate: a per-commit reviewer reproducing a bug ran `git archive ... | tar -x -C /c/tmp/` and then `rm -rf /c/tmp/skills /c/tmp/refs`. Those two paths may have existed before the run; the reviewer could not tell. Its prompt was `skills/review-unpushed/SKILL.md` Step 3's template, which says READ-ONLY DISPATCH and "Leave all changes unstaged" but has none of `refs/builder-preamble.md`'s cleanup rules ("Clean up only the exact files you created, by exact name", scratch dirs under a fresh unique path). `READ-ONLY DISPATCH` only exempts the screenshot id; reviewers still run commands that write scratch files. `skills/code-check/SKILL.md`'s dispatch block has the same gap apart from its worktree paragraph.

## Approach
Add to both templates: extract or copy into a fresh uniquely named scratch dir (e.g. `tempfile.mkdtemp()` / `New-Item` under `$env:TEMP` with a random suffix), never into an existing shared dir like `C:\tmp`, and delete only that dir by exact name.

## Acceptance
Both dispatch templates carry the rule; `hooks/dispatch-preamble-guard.py` still passes them.
