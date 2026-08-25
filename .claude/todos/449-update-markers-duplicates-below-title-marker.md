<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# update-markers.ps1 duplicates a marker instead of replacing one that sits below the title

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/cleanup-todos` Step 5 replace an existing `<!-- cleanup: ... -->` marker even when it sits
*below* the `# ` title, instead of silently adding a second one and resetting `reconfirm-count`.

## Context

Hit for real on 2026-08-20 in `claude_usage_in_taskbar` during a `/mega-todos` run (its todo 671).
The backfill wrote 50 markers and reported `written=50 skipped=0`, looking clean. It had actually
left **17 of those files carrying two markers each**.

`Get-HeaderMarker` (`~/.claude/skills/cleanup-todos/update-markers.ps1:27-34`) only accepts a marker
whose index is **before** the first `^#[ \t]` match. That anchoring is deliberate and correct - it
exists because an unanchored search once overwrote todo 99's evidence block, which quoted the marker
format in prose (noted in the script's own comment, 2026-08-12).

But the anchoring has an unhandled case: a *legitimate* older marker placed just below the title, or
below `**Type:** task`. `Get-HeaderMarker` returns `$null`, the script takes the "no existing marker"
branch (`:85-92`), inserts a fresh one at the top, and the old one stays. Two consequences:

1. Two markers in the file. The stale one is dead weight and misleads a human reader.
2. `reconfirm-count` and `content-hash` reset to 1, because the old baseline was invisible - so a
   todo that had genuinely been reconfirmed loses that history. Confirmed on one file (`45-`) whose
   old and new `content-hash` were identical (`e3b0c442`), meaning the count should have gone to 2.

**The Step 5 diff gate does not catch this.** Its rule is "one marker line added or replaced, above
the first `# ` heading", which this change satisfies exactly while still producing a wrong file.

## Approach

Two independent fixes; do both.

1. **`Get-HeaderMarker`:** widen it to also match a marker below the title, but only within the
   header region - up to the first `^## ` section heading. That keeps the todo-99 protection (prose
   quoting the format lives inside a `##` section, never above the first one) while catching the real
   case. When both an above-title and a below-title marker exist, replace the above-title one and
   delete the other, carrying the older `reconfirm-count`/`content-hash` forward as the baseline.
2. **The Step 5 diff gate in `SKILL.md`:** add a post-condition that each touched file ends with
   **exactly one** marker, positioned above the first `# ` heading. The current gate only constrains
   the *diff*, not the resulting *state*, which is why a passing gate still produced 17 broken files.

## Acceptance

- A fixture with a marker below the title gets that marker replaced, not duplicated, and ends with
  exactly one marker.
- A fixture that quotes the marker format inside a `## ` section is left untouched (todo 99's case).
- `reconfirm-count` increments across a run when `content-hash` is unchanged, even if the previous
  marker was below the title.
- The gate fails loudly on a file that ends up with two markers.

## Notes

- The 17 affected files in `claude_usage_in_taskbar` were repaired by hand on 2026-08-20 by splicing
  the raw string by index. Worth copying that detail: those files have **mixed line endings**,
  because `update-markers.ps1:89` inserts its marker with a hardcoded `` `r`n `` into files that are
  otherwise LF. Any repair that re-joins lines with one ending normalises the whole file and turns a
  one-line fix into a whole-file diff. Two attempts failed that way before the index-splice worked.
- That hardcoded `` `r`n `` is arguably a third bug in the same script - it is what makes these files
  mixed-ending in the first place. Consider deriving the ending from the file, as `:83` already does
  for the replace branch via `$trailer`.
