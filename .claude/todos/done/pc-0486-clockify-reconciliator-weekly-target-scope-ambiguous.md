<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=f75ece05 -->
<!-- duplicate-checked -->
# clockify-reconciliator doesn't confirm what a stated hour target covers

**Type:** skill-improvement
**Origin:** ai

## Goal

When the dev states a weekly hour target ("we need 30 hours total"), confirm
its exact scope before sizing anything toward it, instead of assuming.

## Context

Found 2026-08-22 on revaire-mobile. The dev said he needed 30 hours for the
week. The skill (reasonably) built a Mon-Fri gap-fill plan totaling ~30h and
presented it. The dev then said "no... we are meant to have 30 hours in total
by the end of the week... and also reserve like 2/3 hours for today" -
meaning the 30h included the 2 already-existing entries AND a reserve for
Saturday, not 30h of NEW Mon-Fri entries on top of them. Had to redo the
whole trim after presenting a table that overshot by ~4h.

Same session, separately: a plain arithmetic error (summing one day's block
durations wrong, 8h stated vs 10.5h actual) also wasn't caught until
presented - worth a acceptance check below too, since both are "the total
shown to the dev didn't match reality."

## Approach

In step 9 (Present plan) or wherever a stated target first gets used to size
work (Reconstruction mode, `modes.md`), add an explicit confirmation before
building any plan toward a stated total:

- Does the target include already-existing entries for the window, or is it
  additional/new hours only?
- Does the target's window match the reconciliation window exactly (e.g. does
  "this week" include today, or stop at yesterday)?

Cheap to ask up front, expensive to discover after building and presenting a
plan that has to be redone.

## Acceptance

- A stated target's scope (existing-inclusive vs new-only, exact day range)
  is confirmed before the first proposal table is built, not after the dev
  rejects one.
- Before presenting any table with a totals row, the sum shown is re-added
  from the actual block durations, not carried over from an earlier estimate
  - catches the class of bug where a stale/wrong subtotal survives into the
    dev-facing table.

## Notes

Related, filed separately: [[485-clockify-reconciliator-commit-sweep-misses-other-branches]].
- Done via /mega-todos batch 2, commit 82aff5c: step 3a now confirms a stated hour target's scope (existing-inclusive vs additional-only, and whether the window matches) BEFORE any proposal table is built, and step 9a requires re-summing totals from actual block durations at presentation time. modes.md cross-references step 3a rather than duplicating the rule.
