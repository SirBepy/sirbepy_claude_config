<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Read in full before filing: done/258 is the todo that ASKED for the moved-line carve-out; this
     reports a side effect of how that carve-out was implemented, so it is the follow-on, not a
     restatement. done/779 is the Rust-deref false positive in the same awk pattern. 399 is the same
     enforcer failing on a construct the pattern never matches at all. 356 and 412 are about when
     the prefilters run, not what they count. None covers a reset-vs-skip defect inside a matched
     block. -->
# A blank JSDoc `*` line resets comment-noise's run counter, so the cap never fires

**Type:** skill-improvement
**Origin:** ai

## Goal

`comment-noise.sh` counts a JSDoc block as one block. Today any paragraph break inside one silently
splits it into sub-blocks that each pass the 4-line cap, so the cap does not apply to the construct
it most needs to.

## Context

`CLAUDE.md` Code Style: *"Comments: 2 lines typical, 4 lines HARD CAP per block"*, *"Enforced at
commit time by `/commit`"*, which delegates to `skills/commit/comment-noise.sh`.

**This is a side effect of `done/258`'s own fix, not a fresh oversight.** 258 asked for a carve-out
so a pure code move would stop reading as newly-authored noise (agents were deleting real
documentation to satisfy the prefilter). The carve-out shipped at `comment-noise.sh:47-53`:

```awk
if (l in head_line_files) {
  n = split(head_line_files[l], parts, "\001")
  for (i = 1; i <= n; i++) if (parts[i] != f) { moved = 1; break }
}
if (moved) run = 0
else { c[f]++; run++; if (run>max[f]) max[f]=run }
```

The intent is right. The defect is that a moved line **resets** `run` instead of being skipped over.
`head_line_files` is keyed on the line's exact TEXT, and a JSDoc separator is the bare string ` *`,
which exists in essentially every `.ts` file in any repo. It therefore always resolves as "moved",
always zeroes the run, and every paragraph break inside a doc comment restarts the count from zero.

**Reproduced against real content, 2026-09-04, in `claude_usage_in_taskbar`.** A new
`src/views/sessions/git-card.ts` was committed carrying a **13-line** file-header block. The
prefilter gate ran against it and exited **0**. Its two ` *` separator lines chopped the header into
runs of 2, 4 and 3 counted lines, all under the `max[k]>=5` threshold at `comment-noise.sh:61`, so
the 13-line block was never over-cap as far as the script could see.

The blank line is the whole trigger: the same 13 lines with no paragraph break would have been
caught. That is backwards, since a long block is exactly the one that gets paragraphs.

## Approach

1. **Confirm the fix does not break what the carve-out is for** before changing it. 258's case (a
   verbatim relocation between files in the same diff) must still pass silently afterwards, or this
   re-opens the incident that produced it.
2. Candidate fix, smallest first: make a moved line **neutral** rather than a reset - skip it
   without incrementing `c[f]`/`run` and without zeroing `run`, so it neither counts against the
   author nor ends the block. Only a genuine non-comment line (the existing `else run=0` branch at
   `:54`) should end a run.
3. Alternative, possibly simpler: gate the carve-out on lines that carry authored text. A bare ` *`,
   `//` or `/**` has no content, so matching it against `head_line_files` is meaningless in either
   direction; treating contentless comment lines as never-moved reaches the same result.
4. Re-run both real cases: a genuinely moved multi-line block (must stay silent) and a new 13-line
   JSDoc header with paragraph breaks (must now flag).

## Acceptance

- A new JSDoc block over 4 counted lines is flagged whether or not it contains ` *` separators.
- A block moved verbatim between two files in the same diff is still NOT flagged (258's case).
- `python ci/run_all.py` green.
- Verified by running `skills/commit/comment-noise.sh` directly on a scratch repo holding both
  cases, with its real output pasted into the completion note - not by reasoning about the awk.

## Notes

Sibling of **399** (the cap is unenforced for Python docstrings and PowerShell `<# #>` help, because
the pattern never matches those at all). Both are holes in the same enforcer; this one sits inside a
construct the pattern DOES match, so it is the more surprising of the two. **403** questions whether
the cap should exist in this shape at all - if 403 lands first and changes the rule, re-read this
before implementing.
