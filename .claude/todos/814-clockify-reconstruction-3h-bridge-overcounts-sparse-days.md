<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=3, content-hash=d4a7d05d -->
<!-- duplicate-checked -->
# clockify-reconciliator Reconstruction mode's 3h-gap bridging overcounts sparse-commit days

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix Reconstruction mode's clustering default so it stops padding real dead time as billable work
on days where commits are sparse but spread across many hours.

## Context

`skills/clockify-reconciliator/modes.md`'s "Reconstruction mode" clustering defaults say: "session
break at a 3h commit gap ... split sessions over 3h into ~2-2.25h sub-chunks" - any two commits
less than 3h apart get bridged into one continuous session with zero deduction for the dead time in
between. This default is documented as "proven 2026-07-21, 46 entries" but a 2026-08-27 zng-app
run (Mon-Wed reconstruction) found it produces real overcounting on a low-density day.

A dedicated "argue the plan overcounts" subagent review (run specifically to stress-test the draft
plan before applying) found ~4-6 hours of unbacked padding across the 3-day window, concentrated on
the one day with the sparsest, most spread-out commits:

- One proposed chunk (Tue 17:30-18:35, 1h05m) contained **zero commits at all** - it was pure
  gap-filler invented to bridge from the end of one meeting to the start of the next, not backed by
  any evidence.
- Three other chunks each carried roughly 1h-1.5h of dead time beyond their actual last-commit+20min
  trail-off, because the chunk boundary was stretched to reach the next scheduled meeting instead of
  stopping where the evidence stopped.
- The day's originally-proposed total (11h20m) dropped to a defensible ~7h00m once these were cut.

This directly contradicts the skill's own hard rule ("never invent hours not backed by a real
commit/PR or an explicitly named real activity") - the current clustering default, applied
literally, produces exactly that invention on sparse days, even though it works fine on the
originally-tuned 46-entry dataset (presumably denser).

## Approach

Tighten `modes.md`'s Reconstruction clustering defaults:

- Stop stretching a chunk's end to the next scheduled meeting/carve-out boundary. Cap every chunk at
  its own last-commit + the stated pad (+20min), never further, even if that leaves a gap before the
  next existing entry.
- Never manufacture a chunk in a "leftover" window between two carve-outs (meetings) unless a commit
  actually falls inside that window. A zero-commit gap between two meetings is not evidence of work.
- Consider whether the "any gap under 3h bridges with zero deduction" rule needs a secondary
  threshold - e.g. still treat the whole span as one loosely continuous session for chunk-boundary
  purposes, but only render blocks that have real lead-in/trail-off padding around actual commit
  clusters, leaving real 1h+ commit-free stretches unlogged instead of solid-filled.
- Re-validate against the original 46-entry dataset this default was tuned on, to make sure the fix
  doesn't regress the case it was originally solving (that dataset may have been dense enough that
  this failure mode never triggered).

## Acceptance

- Given a sparse/spread-out commit day, Reconstruction mode no longer produces a chunk with zero
  backing commits.
- Given the same day, no chunk's rendered duration exceeds its actual commit-cluster span by more
  than the stated pad on either end.
- The original 46-entry validation case (2026-07-21) still produces materially the same plan it did
  before this fix.

## Notes

The finding came from an ad hoc "run one subagent arguing bigger, one arguing smaller, then
reconcile" review pattern the dev asked to try live (not yet part of the skill itself - the dev
separately rated formalizing that pattern as a standing step at 3/10, preferring a deterministic
threshold flag instead; see the session's /rate-it verdict if this todo is picked up together with
that angle). This todo is specifically about fixing the clustering math itself, independent of
whether an adversarial-review step is ever added.
