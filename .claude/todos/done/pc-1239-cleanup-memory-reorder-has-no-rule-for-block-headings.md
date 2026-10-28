<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1155 is the core cap; no backlog file covers Step 6.5's heading guard -->
# cleanup-memory Step 6.5 lets block headings through but never says where they go in the reorder

**Type:** bug
**Origin:** ai

## Goal

`/cleanup-memory` Step 6.5's mtime reorder keeps an index's `## Axioms` / `## Recent` / `## Rest`
headings as block separators, or refuses to reorder an index that has them, instead of having no
rule for them.

## Context

Found by the 2026-10-23 loop-todos per-commit review (slice C) of commit 34a4e67, low-medium
confidence. `skills/cleanup-memory/SKILL.md` Step 6.5 item 2 (around line 273 at that commit) now
lets `## Axioms`, `## Recent` and `## Rest` through its heading guard, calling them the output
shape from `refs/memory-rubric.md`. That rubric (`refs/memory-rubric.md:84-90`) defines the three
blocks only as bold list items and never prescribes `## ` headings, and Step 6.5 never says where a
heading line goes during an mtime sort, so an index with those headings reaches the reorder with
no rule and the headings can be scrambled or flattened, the failure the guard existed to stop.

## Approach

State in Step 6.5 that each heading stays put and the sort runs within each block, or restore the
strict guard; and make the rubric and the step agree on headings vs bold items.

## Acceptance

A dry read of Step 6.5 on an index with the three headings gives one unambiguous result, and the
rubric names the same block markers the step accepts.

## Notes

- Step 6.5 now treats the three canonical headings as block separators: dropped before sorting and from the line-set checks, block membership comes from the Axioms/Recent/Rest rule only, and the headings are rewritten above each non-empty block only when the index already had them. memory-rubric.md says blocks may be marked with exactly those headings or left unmarked. Prose-only step, no script to test.
