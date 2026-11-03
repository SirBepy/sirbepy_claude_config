<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the five hits share only vocabulary (step, skill, file); none concerns /commit step 6a running ci/run_all.py -->
# /commit step 6a runs the full ci/run_all.py for a four-file skill prose edit

**Type:** skill-improvement
**Origin:** dev
**Summary:** In `~/.claude`, `/commit` step 6a mandates `python ci/run_all.py` for every commit, which runs minutes of hook, tool and prefilter suites even when the diff is skill prose plus one pipeline-order test, and Joe objected on 2026-10-30.

## Goal

A commit that touches only skill markdown and its own test runs that test (and anything else cheap and relevant), and leaves the full `ci/run_all.py` to the push gate.

## Context

On 2026-10-30, committing the gate-chat 30%-threshold fix (four files: `skills/commit/SKILL.md`, `skills/gate-chat/SKILL.md`, `skills/release/SKILL.md`, `skills/release/test_pipeline_order.py`), Claude followed `skills/commit/SKILL.md` step 6a ("A `ci/run_all.py` at the repo root: run `python ci/run_all.py` and treat its verdict as the whole suite"). The first run hit a 110 s cap; the second was still in its prefilter self-tests after the hook suites (47/47) and tool suites (15/15) had passed when Joe said "idk why you thought you should run the full ci suite" and it was stopped. Claude had already run `skills/release/test_pipeline_order.py` directly (all PASS). The skill-frontmatter step also failed in that run on `skills/impeccable/SKILL.md` (118w description over budget), an uncommitted peer edit unrelated to the commit, so the whole-suite verdict is also noisy in a shared checkout.

## Approach

Edit step 6a's `ci/run_all.py` bullet in `skills/commit/SKILL.md`: scope it to a diff that touches `hooks/`, `tools/`, `ci/` or `CLAUDE.md`, and say a skill-prose diff runs only the test files that name the touched skill. Whether the narrowing belongs in step 6a or in `/test` is Joe's call; ask before editing.

## Acceptance

- A skill-prose-only commit in `~/.claude` finishes its test step in seconds.
- `ci/run_all.py` still runs in the push gate and in GitHub Actions, unchanged.

## Notes

- Fixed in cdfe1e6 (step 6a runs the full suite only for executable changes; decided option a per the todo approach).
