<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=5, reconfirm-count=1, content-hash=18148d92 -->
<!-- duplicate-checked: grepped for "per-repo"/"commit count"/"checked...repo" across the backlog,
no hit touches step 6's commit sweep or step 9's plan presentation -->
# clockify-reconciliator plan presentation should state per-repo commit counts up front

**Type:** skill-improvement
**Origin:** ai

## Goal

Step 9's plan presentation (the text/card shown before the apply/cancel `AskUserQuestion`) should
state how many commits step 6 found in each configured repo, so the dev can see the sweep was
thorough without having to ask.

## Context

Found 2026-09-30, zng-app, `/clockify-reconciliator zirtue` for "today". After presenting a
reconciled plan, the dev asked "Are you sure you checked zng admin and zng biller?" - a fair
question, since nothing in the presented plan had stated which repos were swept or how many
commits each produced. The session had in fact already run step 6's `--all`, no-author-filter
sweep across all four configured repos (zng-app: 6, zng-admin: 1, zng-biller: 3, zng-api: 0) before
presenting, but none of that was surfaced, so the dev had no way to tell the sweep was complete
without asking and waiting for a fresh re-check.

This is a trust/transparency gap, not a correctness gap - the underlying step 6 sweep was already
correct. The fix is presentation-only: make the evidence the skill already gathered visible instead
of silently trusting it.

## Approach

In step 9 (Present plan), before the date/duration/description table, add a one-line per-repo
summary: `Commits checked: zng-app 6, zng-admin 1, zng-biller 3, zng-api 0` (repo names and order
matching the config's `repos:` list). Source it directly from step 6's already-gathered commit
list - no extra fetch needed, this is purely surfacing data the skill already has in hand. Zero
commits in a repo is itself useful signal (confirms the repo was swept, not skipped) so it should
print `0`, never be omitted.

## Acceptance

- Every plan presentation (step 9) names every configured repo and its commit count for the
  resolved window, before the proposal table.
- A repo with zero commits in the window still appears in the line (proves it was checked, not
  silently dropped).

## Notes

Related to [[1008-clockify-week-remaining-on-a-partial-window-needs-a-sanctioned-real-fetch-path]]
(also a step 9/9a presentation-transparency gap, found in the same session) - different fix, same
root cause: the skill gathers more evidence than it currently shows the dev, so he has to ask for
things that were already checked.
- Completed by /loop-todos cycle 1 (2026-10-05), lane F1: skills/clockify-reconciliator/SKILL.md. Docs-only procedure change, untestable by Claude beyond ci/run_all.py (drives live Clockify/HubStaff/Shortcut APIs).
