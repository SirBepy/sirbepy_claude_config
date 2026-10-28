<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1181 is batch poisoning + round cap, 1179 is the verdict-line format, done/1110 added the ship-review lens; this one is the ship-review lens failing drafts on style taste with every fact confirmed -->
# outbound-verify: ship review fails drafts on style taste, not misreading

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the ship-review step of `refs/outbound-verify.md` from failing a draft whose every factual
claim is CONFIRMED only because one verifier prefers a different layout, while keeping it able to
fail genuinely misreadable wording.

## Context

revaire-mobile session, 2026-10-15 (REV-7345 PR #1152, its review text, and the Linear QA hand-off
comment). 15 verifier dispatches across 5 rounds; 5 FAILs. In every FAIL all factual claims were
CONFIRMED. Two FAILs were real misreading risks worth fixing (two acceptance facts joined under one
subject with opposite fixtures; numbered QA steps that cannot run in sequence on one flight). The
other three were taste: no closing "tests pass" line vs precedent PRs, `REV-N:` vs `REV-N -`
header, and a "Test steps," lead-in plus lettered list instead of the precedent's
"Test steps:" + numbered list. The step-3 wording in `refs/outbound-verify.md` ("flag wording a
teammate could misread even when it is factually true. Any finding here is a FAIL") lets "differs
from the nearest precedent" count as a finding, and the 2-round stop then needed Joe to authorize
a third round for a QA comment whose facts had passed 6 verifiers.

## Approach

In `refs/outbound-verify.md` step 3 of the verifier template, split ship-review findings into:
- FAIL: wording a reader would act on wrongly (wrong sequence, conflated conditions, wrong
  target/owner/field), or a non-text field that disagrees with the tracker.
- NOTE (does not fail): format or phrasing that differs from precedent but cannot be misread.
Require the verifier to state, for any FAIL, the concrete wrong action a reader would take.
Optionally let the main agent pass the nearest precedent's literal shape in the dispatch so the
draft can match it before round 1.

## Acceptance

A draft whose facts are all CONFIRMED and whose only finding is a precedent-format difference
returns PASS with a NOTE line; a draft with a conflated-condition sentence still returns FAIL with
the misreading named. Check the template text in `refs/outbound-verify.md` and the guard
`hooks/outbound-verify-guard.py` still parses the verdict line unchanged.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): ship-review findings split into FAIL (names the concrete wrong action) and NOTE (unmisreadable precedent difference, does not fail).
