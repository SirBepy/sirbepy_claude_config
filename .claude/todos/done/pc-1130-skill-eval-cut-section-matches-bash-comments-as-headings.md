<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; done/478 added --cut-section; no todo covers fenced-code awareness -->
# skill_eval.py `--cut-section` treats a `# comment` inside a fenced bash block as a heading

**Type:** task
**Origin:** ai

## Goal
`--cut-section <heading>` removes the whole section, not just the text up to the first bash comment
inside a code fence.

## Context
Found 2026-10-08 by the loop-todos builder that wrote `/wrangler`'s eval fixtures (todo 920).
`tools/skill_eval.py`'s `locate_section()` uses `HEADING_RE` `^(#{1,6})\s` with no fenced-code
awareness, so a `# comment` line inside a ```bash block reads as an ATX heading and ends the section
early. Cutting `## Deployment` removed 42 characters instead of about 1500, so the cut was a
near-no-op that still reported success. The builder worked around it for fixtures 2-4 by targeting
the bash comment line itself as the "heading" (documented in `skills/wrangler/evals/RESULTS.md`).

## Approach
Track fence state (lines starting with ``` or ~~~ toggle it) in `locate_section()` and ignore
heading matches inside a fence. Add a self-test case with a bash comment inside a fenced block. Then
re-point the wrangler fixtures' cut targets at the real section headings if RESULTS.md says so.

## Acceptance
- Cutting a section that contains a fenced bash block with `#` comments removes the whole section.
- `python ci/run_all.py` passes.

## Notes

- locate_section() is fence-aware (CommonMark open/close rule) via a _fence_mask helper; new RED-then-GREEN case in tools/test_skill_eval.py; wrangler fixtures 2-4 re-pointed at their real ### headings, each now spanning 265-697 chars instead of the 42-char near-no-op.
