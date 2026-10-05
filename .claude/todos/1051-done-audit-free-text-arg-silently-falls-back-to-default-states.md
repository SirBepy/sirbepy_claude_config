<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=b8cff8cb -->
<!-- duplicate-checked: 1023 (backlog read before fan-out), 1010 (7b script deletion), 1019 (history endpoint), 312 (ID arg mode) are the same skill but different defects; none covers free-text args. -->
# 1051 - shortcut-done-audit treats a free-text arg as "no arg" and audits the wrong columns

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-30

## Goal

When `/shortcut-done-audit` gets an arg that is neither state names nor ticket ids, it asks instead
of silently running the default `Backlog,To Do,In Progress` scan, and it routes release-shaped
phrasing ("we just did a new version", "shipped FE 1.1.0+1") to the Ready for deploy close-out.

## Context

zng-app session, 2026-09-29/30. Joe invoked `/shortcut-done-audit we just did a new version FE 1.1.0+1`.
The skill's Args section only defines two shapes (state names, numeric ids) and says to ask on an
unknown state name. Claude treated the sentence as no arg, scanned the default three columns,
dispatched 3 sonnet subagents on 3 To Do/Backlog tickets, and reported. Joe's reply: "why are you
looking at those 3 columns bro, why arent you looking at the ready for deploy column?" What he
wanted was the release close-out: Ready for deploy tickets whose code is in the new tag moved to
Complete with the Release field set, i.e. `/zirtue-release-backfill`'s job. The 3-agent run was
wasted work (~300k subagent tokens).

## Approach

In `C:\Users\tecno\.claude\skills\shortcut-done-audit\SKILL.md`, Args section:

- Add a third parse outcome: an arg that contains neither a known state name nor only numerics is
  free text. Never treat it as "no arg".
- If the free text mentions a version, release, tag, deploy or "new version" (regex over
  `v?\d+\.\d+\.\d+\+\d+`, "release", "version", "deploy", "shipped"), stop and tell the dev that
  closing Ready for deploy tickets for a release is `/zirtue-release-backfill`, and offer to run the
  audit against `Ready for deploy` instead.
- Otherwise ask via the question tool which states to scan, listing the ENG - Core Workflow names.

## Acceptance

- `/shortcut-done-audit we just did a new version FE 1.1.0+1` no longer scans Backlog/To Do/In
  Progress; it redirects to the backfill or asks.
- Plain state-name args and numeric-id args behave exactly as before.

## Notes

- The follow-on manual backfill in that session also surfaced gaps in `/zirtue-release-backfill`
  itself, filed separately as 1052.
