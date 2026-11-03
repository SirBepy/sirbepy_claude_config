<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no live todo mentions a 200-line cap or line cap for MEMORY.md -->
# 1263 - cleanup-memory: the harness also cuts MEMORY.md at 200 lines, not only at the byte cap

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-28
**Summary:** /cleanup-memory and its reachability script check both the line limit and the byte limit of MEMORY.md, so neither reports clean while lines are dropped.

## Why

On 2026-10-27 the harness warned that a 201-line, under-byte-cap index lost its last line, while reachability.mjs reported no problem.

## Goal

Make `/cleanup-memory` and `reachability.mjs` check both MEMORY.md limits, so neither the skill nor the script reports "clean" while the harness is dropping lines.

## Context

`skills/cleanup-memory/SKILL.md` Step 1.5 and `refs/memory-rubric.md` "Index ordering" say the old "200 lines" rule was wrong and that the only cut is the 24.4KB byte cap. On 2026-10-27, the zng-app session 9dee5a6f started with this harness warning: "MEMORY.md is 201 lines (limit: 200). Only part of it was loaded: 1 of 201 lines were cut off, starting at line 201". The index was 23,344 bytes, under the byte cap, and `reachability.mjs` printed `line cap: 202 (derived from --byte-cap=24985)`, so it missed the real cut at line 201. Both limits apply, and whichever is hit first wins.

## Approach

1. In `reachability.mjs`, use the effective cap `min(200 lines, the line where 24.4KB lands)` and print which limit set it.
2. In SKILL.md Step 1.5 and memory-rubric.md "Index ordering", state both limits and cite this warning as the receipt.

## Acceptance

- On a 201-line index under 24KB, `reachability.mjs` reports the cut at line 201 and flags the file linked on that line as an orphan.

## Notes

- Fixed in 92fa3be.
