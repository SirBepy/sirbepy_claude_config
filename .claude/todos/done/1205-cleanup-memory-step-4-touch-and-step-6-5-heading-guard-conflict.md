<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/1014 introduced the heading guard this item amends; 101, 1184, 1092, 1103 are different surfaces that only share vocabulary -->
# /cleanup-memory: Step 4's rotation touch and Step 6.5's heading guard contradict the rest of the skill

**Type:** skill-improvement
**Origin:** ai

## Goal

A `/cleanup-memory` run can follow every step as written without one step undoing or blocking another.

## Context

Found on the zng-app run of 2026-10-20 (memory dir `C:\Users\tecno\.claude-personal\projects\c--Users-tecno-Desktop-Projects-zng-app\memory`, 341 files). Two conflicts in `skills/cleanup-memory/SKILL.md`:

1. **Step 4 rotation vs Step 6.5 ordering.** Step 4 says to touch each deep-checked file (no-op edit or a `<!-- last-deep-checked -->` comment) so it rotates to the back of the mtime queue. Step 6.5 then sorts the index into Axioms / Recent (mtime within 7 days) / Rest by file mtime. Touching 60 files makes all 60 "Recent" and puts them at the top of the index, regardless of relevance, and pushes truly recent entries down. The run skipped the touch on purpose to keep the index order meaningful, so the next run will re-check the same 60 oldest files.
2. **Step 6.5's section-heading guard trips on the canonical shape.** The guard skips the reorder when `MEMORY.md` has two or more `## ` headings, which it reads as hand-made topic sections (from done/1014). But the canonical Axioms/Recent/Rest blocks in `refs/memory-rubric.md` ("Index ordering") are themselves written as `## Axioms`, `## Recent`, `## Rest` in the zng-app index. Read literally, the guard blocks every reorder of a correctly shaped index. The run treated exactly those three headings as canonical and went ahead.

## Approach

- Step 4: record the rotation somewhere other than mtime, e.g. a `last-deep-checked:` frontmatter field or a small `<memory-dir>/.deep-check-log` that orders the candidate queue. Then Step 6.5's mtime ordering stays a true "recently written" signal. If mtime has to stay the signal, restore each file's mtime after appending the marker and sort the Step 4 queue by the marker date instead.
- Step 6.5: exempt a heading set that is exactly `Axioms`, `Recent`, `Rest` (any subset) from the hand-sectioned guard, and only skip on any other `## ` heading.
- Update `reachability.mjs` only if the chosen Step 4 mechanism adds a file to the memory dir that it would count as a memory.

## Acceptance

- Running `/cleanup-memory` twice in a row on the zng-app dir deep-checks two different sets of 60 files, and the index's Recent block after each run contains only files actually written in the last 7 days.
- An index whose only `## ` headings are Axioms/Recent/Rest gets reordered, and one with a topic heading like `## Playwright` is still skipped.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): Step 4 rotation uses a .deep-check-log sidecar written in Step 6, no mtime touch; Step 6.5 exempts Axioms/Recent/Rest headings. reachability.mjs ignores the sidecar (scratch run: orphan-file 0).
