<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# CLAUDE.md documents only one direction of the MEMORY.md desync

**Type:** skill-improvement
**Origin:** ai

## Goal

Close the half of the memory index/file desync that global `CLAUDE.md` does not currently cover, and
record fresh evidence that the orphan-file problem recurs across projects rather than being a
zng-app quirk.

## Context

Filed 2026-08-18 from a `claude_usage_in_taskbar` session with three concurrent agents on master.

Todo 320 (done 2026-08-15) added the bolded Memory Discipline rule: **never delete an index line
while its memory file still exists on disk**, citing the reproduced 2026-08-13 three-entry loss.
That rule is correct and is doing its job. It only describes one direction.

**The reverse happened today.** A peer session wrote a near-duplicate memory, then decided mine was
better, `rm`'d its own file, and left the `MEMORY.md` line it had added minutes earlier. Result: an
index entry pointing at a file that does not exist. I removed the line; the peer independently
re-ran the check and confirmed `index lines pointing at missing files: 0` afterwards.

This direction is less destructive than 320's (a dangling line wastes index budget and misleads a
reader, it does not silently unload a real memory), but it is the same class of bug, it is not
mentioned anywhere, and the agent that caused it said plainly it had not considered it.

**Fresh data on the orphan direction, which 320's Notes already flagged via 323.** Swept this
project's store both ways, counting `[[wikilink]]` references as reachable, not just `(file.md)`
links:

```
files on disk:                        230
reachable from MEMORY.md:             172
unreachable (never load):              58   (25%)
index lines pointing at missing files:  0
```

zng-app was 23 of 182 (13%) on 2026-08-13. This project is 58 of 230 (25%). Two projects, same
direction, worse here. So the harness's "compact the index" nag is pushing against an index that is
already missing a quarter of its store - exactly the tension 320's Notes said had to be reconciled,
now with a second data point.

## Approach

1. Extend the Memory Discipline bullet in global `CLAUDE.md` so it covers BOTH directions in one
   sentence rather than naming only the dangerous one: an index line and its memory file are
   created together, and deleted together, in the same edit. Keep 320's existing emphasis on the
   silent-unload direction - that one is still the costlier failure and should stay bolded.
2. Teach `/cleanup-memory` to run the two-way sweep as a reported step, since both this session and
   the zng-app one found their numbers only by hand-rolling the check:
   - index lines whose target file is missing (delete the line)
   - files reachable from neither a `(file.md)` link nor a `[[wikilink]]` in `MEMORY.md`
     (re-index or archive - Joe's call per entry, never automatic)
   The wikilink half matters: a naive `(file.md)`-only sweep over this project reported 62 orphans
   when the real number was 58, because cluster entries legitimately reference members via `[[...]]`.
3. Do NOT re-litigate 320's option 3 (`##` topic headings in the index) here. That remains the most
   likely way to hold "index needs additions" and "index is too long" at once; this todo just adds
   the second data point supporting it.

## Acceptance

- `CLAUDE.md` states the create-together / delete-together rule for index line + memory file, with
  320's silent-unload direction still called out as the worse one.
- `/cleanup-memory` reports both desync directions with counts, and its orphan check treats a
  `[[wikilink]]` as reachable.
- Neither change deletes a memory on its own authority. Pruning stays Joe's call, per 320.

## Notes

- Prior art, read before doing anything here: `done/320-memory-index-hook-demands-destructive-compaction.md`
  (the advisory-warning rule and the reproduced loss event) and `done/323-cleanup-memory-confirm-gate-should-auto-apply.md`.
- This todo does NOT propose acting on the 58 orphans in `claude_usage_in_taskbar`. That is a
  `/cleanup-memory` pass Joe has been told about and has not yet asked for.
