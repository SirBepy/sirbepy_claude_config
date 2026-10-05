<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no other todo covers claim filename normalization -->
# claim-todo.ps1 and complete-todo.ps1 disagree on leading zeros in claim filenames

**Type:** skill-improvement
**Origin:** ai

## Goal
A todo claimed in a batch is released by `complete-todo.ps1`, whatever leading zeros the id was typed with.

## Context
Seen 2026-10-03 in mc_plugins_tag (session cf279864). `claim-todo.ps1 -Id 16,13,15,01,03,04,02` wrote `1.claim`, `3.claim`, `4.claim` (leading zeros stripped in the batch path). Later `complete-todo.ps1 -Id 01` (and 03, 04) printed "WARNING: todo 01 is being completed with no claim on record" and left `1.claim`/`3.claim`/`4.claim` behind; they had to be deleted by hand. A single-id `claim-todo.ps1 -Id 02` wrote `02.claim` (zero kept) and `complete-todo.ps1 -Id 02` found and removed it. `complete-todo.ps1` matches `"^0*$([regex]::Escape($numericId))\.claim$"`, so with `$numericId = "01"` it accepts `01.claim`/`001.claim` but never `1.claim`.

## Approach
Normalize the numeric id the same way in both scripts (`skills/close/claim-todo.ps1`, `skills/close/complete-todo.ps1`, shared helper in `skills/close/_shared.ps1` if one fits): strip leading zeros before building the claim name AND before building the match regex, so `^0*<id-without-zeros>\.claim$` is used everywhere. Check the slug-suffixed form too.

## Acceptance
- Batch-claim `-Id 01,03`, then `complete-todo.ps1 -Id 01`: no "no claim on record" warning, `1.claim` removed.
- Single-claim `-Id 02`, then complete: still works.
- Any existing test for these scripts updated; `python ci/run_all.py` green.
