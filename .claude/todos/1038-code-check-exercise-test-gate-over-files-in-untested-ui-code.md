<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=809c957b -->
<!-- duplicate-checked: grepped todos, done/ and dropped-findings.log for "exercise test", "Step 4a" and "code-check" on 2026-09-28. Closest are done/451 (findings filed for a reader who never reads) and done/898 (findings resurface after being declined). This is a third, distinct failure: the gate's pass condition is structurally unreachable in UI code, so it routes to file even when the author could fix it in ten minutes. -->
# 1038 - code-check's exercise-test gate over-files in UI code that has no tests

**Type:** skill-improvement
**Origin:** dev

## Goal

`/code-check` stops filing a todo for a finding the author could safely fix in the same session, in
repos where the exercise test it demands can never exist.

## Context

`skills/code-check/SKILL.md` Step 4a gates applying any finding on naming "the specific test file or
command that would FAIL if this change were wrong". Class 1 applies only if that passes; class 2
files "unless the exercise test passes AND the suite is green".

In a Flutter UI repo that condition is structurally unreachable for most findings. zng-app's
`test/` has no widget test that imports the changed widget's internals, and its own memory
(`reference_no_authenticated_widget_tests`) records that authenticated screens are deliberately not
widget-tested. So every finding in a screen or component file routes to "file", regardless of size.

**The incident, 2026-09-28, zng-app sc-55787.** `/code-check` returned two DRY findings on code
written minutes earlier in the same session. Both were filed as todos per the table. Joe:
*"how come we didnt fix the 2 dry issues?"* One was a three-line duplicated provider read across two
call sites and was applied in about ten minutes once he asked, then re-verified with the ticket's own
Playwright sections (9/9) and folded into the still-unpushed commit. Filing it was the wrong call and
the skill's own routing table is what produced it.

The gate is not wrong in general: its stated rationale is the 2026-08-22 `strip_quotes` case, where a
dead-symbol scan was confident and wrong and the repo-wide suite could not have caught the deletion.
That risk is real for *deleting* a symbol the reviewer believes is unreferenced. It does not transfer
to the author tidying a duplication they introduced in the same session, on a surface they already
have a runtime probe for.

Related and already closed: `done/451` (findings filed for a reader who never reads them) and
`done/898` (findings resurfacing after being declined). This is the same backlog-pollution family,
different mechanism.

## Approach

1. Add a second, narrower pass condition to Step 4a's exercise test, so the gate can clear on
   evidence that is not a unit test. Proposed wording: the test passes if EITHER a named test/command
   would fail, OR all three of - the finding is inside code this same session authored, the change is
   behaviour-preserving, and a runtime probe covering the changed path exists and is re-run after
   applying with its output pasted.
2. Keep the strict form for anything the session did not author, and for any deletion of a symbol
   the reviewer believes is unreferenced. That is the case the gate was written for.
3. Check whether `/close` Phase 2 needs a matching note, since it is the main caller.

## Acceptance

- Re-reading Step 4a, a reviewer can tell which of the two pass conditions applies without guessing.
- Replayed against the 2026-09-28 zng-app findings, the wrapper duplication routes to "apply" and
  todo 203 (three emitters of one analytics event, needs a flow-neutral home and a scope decision)
  still routes to "file".
- Replayed against the 2026-08-22 `hooks/_hooklib.py` `strip_quotes` case, it still routes to "do not
  apply": that finding was not authored in-session and was a deletion.
- `python ci/run_all.py` green, since skill frontmatter validation runs there.
