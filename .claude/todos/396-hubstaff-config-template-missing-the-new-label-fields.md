<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=7, reconfirm-count=1, content-hash=1920f58b -->
<!-- duplicate-checked -->
# The clockify-reconciliator project-config template omits the two new HubStaff label fields

**Type:** task
**Origin:** ai

## Goal

Add `hubstaff_project_label` and `hubstaff_reason_label` to the project-config template in
`skills/clockify-reconciliator/SKILL.md`, so the template stays the single source of truth for every
HubStaff field the skill reads.

## Context

Todo 390 (archived 2026-08-19, commit `36073e6`) de-hardcoded `PROJECT_LABEL` and `REASON_LABEL` out
of `skills/clockify-reconciliator/scripts/hs_addtime.cjs` and moved them into the skill's shared
config source, then documented the new call site in `hubstaff.md`.

The gap: `SKILL.md`'s own "Project config template" block was owned by a different lane during that
run, so it still does not list either field. Anyone setting the skill up from that template gets a
config that `hs_addtime.cjs` cannot read, and the failure appears at run time against a live
HubStaff account rather than at setup.

Duplicate-checked against the five todos the content guard flagged (`100` playwright MCP assumption,
`232` token rotation, `285` on-demand optional modes, `288` npx cache, `34` audit mode). All five
share only the skill's name; none concerns the config template's field list.

## Approach

1. Read the current template block in `skills/clockify-reconciliator/SKILL.md` and the two fields as
   `hs_addtime.cjs` actually consumes them, so the names and shapes match exactly rather than
   approximately.
2. Add both as optional fields, marked optional, since the other scripts in the skill do not need
   them.
3. Confirm `hubstaff.md`'s new call-site section and the template agree on the names.

## Acceptance

- The template lists both fields with the names the script really reads.
- A fresh setup from the template alone is enough to run `hs_addtime.cjs`.
- No name drift between `SKILL.md`, `hubstaff.md` and `hs_addtime.cjs`.

## Notes

- `hs_addtime.cjs` has still never been run against a live HubStaff account. The dev validates the
  first real run; do not trigger one to test this.
