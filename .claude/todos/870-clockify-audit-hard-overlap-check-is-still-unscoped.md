<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Clockify Audit mode's hard overlap check is still global, after 448 scoped the SKILL.md one

**Type:** skill-improvement
**Origin:** ai

## Goal

Apply todo 448's per-project scoping to the second copy of the overlap rule, in
`skills/clockify-reconciliator/modes.md`, so Audit mode stops flagging a legitimate cross-project
overlap as a bug.

## Context

Filed 2026-09-01 by the `/mega-todos` builder that closed todo 448 (commit `4df9983`), as an
out-of-scope finding: `modes.md` was outside that dispatch's owned paths, which were limited to
`skills/clockify-reconciliator/SKILL.md`.

448 fixed the overlap ban in `SKILL.md` to be per project, reusing the in-project versus
other-project split that step 4's fetch bucketing already performs. Audit mode carries its own
copy of the same rule in `modes.md`, at roughly line 38:

    Hard overlap check: any two entries in the range with overlapping [start, end) - always a bug

That "always" is exactly the wording 448 removed elsewhere. The dev's standing rule, restated live
three times (most recently 2026-08-31, zng-app): overlapping entries across two different projects
are fine, overlapping entries within one project are not.

**UNVERIFIED:** the line number is quoted from the 448 builder's report, not re-read. Confirm the
current text before editing, since `modes.md` may have moved since.

## Approach

1. Read `skills/clockify-reconciliator/modes.md` and find every overlap assertion, not just the one
   line quoted above. There may be more than one copy.
2. Scope each to same-project pairs, matching the wording and mechanism 448 landed in `SKILL.md` so
   the two files cannot drift again. Read `4df9983` first rather than inventing a second phrasing.
3. Consider whether the rule should live in one place that both modes reference, rather than being
   stated twice. Two copies is how this bug happened.

## Acceptance

- No overlap check in `modes.md` calls a cross-project overlap a bug.
- The same-project overlap is still flagged, in both Audit and Reconciliation mode.
- The rule reads the same way in `SKILL.md` and `modes.md`, or exists in exactly one place that
  both point at.
- `python ci/run_all.py` exits 0, and every path referenced by the changed markdown resolves.
