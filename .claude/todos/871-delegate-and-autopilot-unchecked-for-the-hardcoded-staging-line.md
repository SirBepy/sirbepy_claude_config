<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /delegate and /autopilot were never checked for the hardcoded staging line

**Type:** skill-improvement
**Origin:** ai

## Goal

Finish the sweep todo 828 started: check whether `/delegate` and `/autopilot` also present
"Stage your changes but do NOT commit" as the only accepted staging wording, and fix them the same
way if they do.

## Context

Filed 2026-09-01 by the `/mega-todos` builder that closed todo 828 (commit `4e177f9`), as an
out-of-scope finding. 828's own Approach step 3 named `/delegate` and `/autopilot` as skills to
check, but they were outside that dispatch's owned paths, which covered only
`skills/code-check/SKILL.md`, `skills/close/SKILL.md`, `skills/rate-it/panel.md`,
`skills/mega-todos/SKILL.md` and `refs/builder-preamble.md`. The builder did not open or grep them,
so their state is genuinely unknown rather than assumed clean.

The defect 828 fixed: a template that hardcodes one staging sentence reads as if that exact string
is what `hooks/dispatch-preamble-guard.py` requires. It is not. The guard accepts EITHER
"Stage your changes but do NOT commit" or "Leave all changes unstaged", and the second is the
correct one for a repo sharing a git index with concurrent sessions. A template that names only
the first pushes a builder toward the wrong staging discipline in exactly the repos where it
matters most.

## Approach

1. Grep `skills/delegate/` and `skills/autopilot/` for the literal staging sentence. If neither
   hardcodes it, close this as not-a-problem and say so; do not manufacture an edit.
2. Where one does, apply the same treatment `4e177f9` used: name both variants inline and reword
   any surrounding claim so it says the guard requires a staging line and accepts either wording,
   not that these exact strings are what it checks. Read that commit first so the phrasing matches
   rather than drifting into a third wording.
3. Do not weaken the three literal markers `hooks/dispatch-preamble-guard.py` string-checks. Read
   the hook and name all three in the commit message to prove you did.

## Acceptance

- `skills/delegate/` and `skills/autopilot/` either name both staging variants, or are confirmed by
  grep to contain neither and the todo is closed with that evidence quoted.
- No change weakens or removes any of the guard's three literal markers.
- `python ci/run_all.py` exits 0, and every path referenced by a changed markdown file resolves.
