<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=21b89da0 -->
# clockify-reconciliator's HubStaff steps have no documented default for partial-vs-full sync scope

**Type:** skill-improvement
**Origin:** ai

## Goal

When HubStaff is out of sync with Clockify for a reconciled window (e.g. zero HubStaff entries for
days that already have real Clockify entries), `hubstaff.md` step 11/12 should default to writing
the FULL window into HubStaff, not just the days the current run happened to touch.

## Context

Skill file: `~/.claude/skills/clockify-reconciliator/hubstaff.md`. Step 11 is report-only
("comparison... Do NOT auto-fix anything here"), and there's no documented "update mode" at all -
the actual HubStaff-writing flow this session (2026-08-10, zng-app) was improvised live using
`reference_hubstaff_ui_time_edit.md`'s UI-automation recipe, not anything in the skill file.

Hit live: dev asked to "update the hubstaff" after a Clockify gap-fill reconciled 2 previously-empty
days to hit a 30h weekly target. HubStaff came back with **zero entries for the entire week**, not
just the 2 newly-filled days. Claude asked the dev to choose scope (AskUserQuestion: "just the 2 new
days, 3 entries" recommended vs "whole week, 17 entries"), defaulting the recommended option to the
smaller scope on cost grounds. Dev picked the small scope, Claude executed it, then immediately
pushed back hard once he saw the result: "bro, add all the fkin hours to hubstaff for all the days,
defuq u doing." The correct read of "update the hubstaff" was "make it match Clockify", not "mirror
only what I touched this run" - the smaller-scope option should never have been the recommended
default. See [[feedback_sync_scope_default_full_source_of_truth]] for the general rule this
produced; this todo is the skill-specific fix so the next cold run doesn't re-ask the wrong-default
question.

## Approach

In `hubstaff.md`, add an explicit "HubStaff update mode" (distinct from the existing report-only
step 11 comparison):

1. When the dev asks to "update/sync HubStaff" after a Clockify reconciliation run, default to
   writing the FULL reconciled window (every in-project Clockify entry in the date range) into
   HubStaff, not just entries created/edited in the current run.
2. Cost tradeoff (entry count -> UI-automation call count) is still worth surfacing since each
   entry is a multi-step Playwright form fill, but frame it as "smaller scope" needing explicit
   opt-IN from the dev, not as the recommended default. E.g. present "Full week (N entries,
   recommended - matches Clockify)" vs "Just the days I touched this run (fewer, partial)".
3. Document the working UI-automation mechanics discovered this session (real-select `selectOption`
   for Project/Reason, `.from-hour-select`/`.to-hour-select` input typing + `.meridiem-toggle`
   click, `[data-testid="time-entries-form-dialog-billable"]` click to toggle Billable, `a:has-text
   ("Add note")` + `textarea[name="work_note"]` for the note) as the canonical "create HubStaff
   entries in bulk" recipe, cross-linked from `reference_hubstaff_ui_time_edit.md`.
4. HubStaff's own Billable checkbox defaults to checked and is a SEPARATE flag from Clockify's
   (Clockify's is deliberately always false, see [[feedback_clockify_no_billable_flag_no_overlap]]);
   don't silently reuse the Clockify convention here without asking, since HubStaff may be the real
   client-billing signal for Cinnamon. Dev's call this session: uncheck it. Treat that as a
   confirmed default going forward unless told otherwise, but still worth a one-line skill note
   rather than silently assuming.

## Acceptance

- A future "update HubStaff to match" ask, when HubStaff is more out-of-sync than just this run's
  new entries, defaults its recommended AskUserQuestion option to full-window sync.
- The working Playwright selector recipe for bulk HubStaff entry creation is written down somewhere
  a cold session can find it without re-deriving it (the Reason select2 field in particular:
  `.click()` on it produces unreliable/wrong selections, use `selectOption(value)` on the underlying
  hidden accessible `<select>` instead - confirmed reliable this session).

## Notes

Both HubStaff writes this session (3 entries, then the corrective 14 more) were verified live via
UI screenshot before/after each Save and via the weekly total (30:00:00, matching Clockify exactly)
- so the mechanics themselves are solid, this todo is purely about encoding the scope default and
the recipe so the next session doesn't re-derive or re-guess either.
- completed, commit 22b597a
