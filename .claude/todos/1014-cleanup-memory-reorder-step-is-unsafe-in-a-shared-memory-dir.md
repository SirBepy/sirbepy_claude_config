<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=471ed86e -->
<!-- duplicate-checked: searched the live backlog and done/ for cleanup-memory, MEMORY.md and reorder. 1007 is the /cleanup-TODOS merge proposal, a different skill and a different problem. Nothing covers the memory dir's concurrency exposure. -->
# 1014 - /cleanup-memory's reorder step is a whole-file rewrite in a directory several sessions write to

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

Make `/cleanup-memory` Step 6.5 safe to run while other sessions are adding memories, and give the
memory directory a recovery path, so a bad pass is not unrecoverable.

## Context

Found while running `/cleanup-memory` on zng-app, 2026-09-25, with four concurrent sessions live in
that project.

**Problem 1: Step 6.5 is a whole-file rewrite with no concurrency story.** It re-sorts every line of
`MEMORY.md`. The memory directory is keyed on the project path, not the session, so every session in
a project shares one `MEMORY.md` with no locking. A peer adding an index line between this step's
read and its write loses that line silently, last-write-wins. This nearly happened during the run:
after a line-scoped edit the harness reported `the file had been modified on disk since you last
read it`, which is the exact window Step 6.5 sits inside for the whole file.

The step's own text says it verifies "the set of lines before and after must be identical when both
are sorted as sets", which catches a reorder bug but NOT this: a peer's new line was never in the
before-set, so a stale rewrite passes set-equality while dropping it.

**Problem 2: the memory directory has no version control and no backup.** It is not in any git repo
(`~/.claude`'s `.gitignore` covers only an allowlist, and the project memory dirs live under
`~/.claude-personal/projects/` entirely outside it). `hooks/precompact-backup.py` records touched
file PATHS, never content. So a corrupted or half-applied pass has no recovery path at all beyond
re-deriving a memory's content from its index gloss. The run worked around this by copying the
directory to `C:\tmp\memory-backup-<stamp>` by hand before each write, which worked, but nothing in
the skill asks for it.

## Approach

1. **Step 6.5 re-reads and diffs before writing.** Take a hash of `MEMORY.md` at the start of the
   step, re-read immediately before the write, and abort if it changed. That is what the run did by
   hand and it is three lines of script. Stronger alternative: make the reorder line-scoped rather
   than whole-file, computing a minimal sequence of moves.
2. **Strengthen the set-equality check into a superset check.** A line present at write time but
   absent from the before-set means a peer added it mid-run: carry it through rather than dropping
   it, or abort. Set equality alone cannot tell "reorder bug" from "peer wrote a line".
3. **Add a mandatory backup step before Step 6.** Copy the memory dir to a timestamped scratch path
   and print it. Cheap, and it is the only recovery this system has.
4. **Gate on peers like the rest of the toolchain already does.** `/commit` and `/cleanup-todos`
   both call `list_peers` before touching shared state; `/cleanup-memory` does not mention it once,
   despite writing to a file that is shared by construction.

## Acceptance

- A `/cleanup-memory` run whose `MEMORY.md` is modified by another process mid-step aborts or
  merges, never silently drops the other process's line.
- The skill names a backup location before any mutation, and prints it.
- `list_peers` appears in the skill's apply phase.

## Notes

Filed from a zng-app session because that is where it was hit; the fix is entirely in
`~/.claude/skills/cleanup-memory/SKILL.md`, so it belongs here.

Related and already fixed in `2e13e7b`, do not re-file: `reachability.mjs` hardcoded a 200-line cap
while the real limit is a 24.4KB byte cap, so the orphan check reported `orphan-file: 0` on a corpus
dropping 31 files. That is fixed. This todo is only about the concurrency and recovery gaps.

- 2026-10-03 (fibo session e3334a4a): a second reason the reorder is unsafe. Fibo's MEMORY.md is hand-organised into topic sections (How I should work / Asking and answering / Git, PRs and commits / ...). Step 6.5's Axioms/Recent/Rest mtime sort would have flattened those sections, so the step was skipped and the skip reported. The index was 17.1KB, well under the 24.4KB cap, so nothing was at risk of truncation. Suggest: run the reorder only when the index is over (or near) the byte cap, and when it does run, sort within the existing ## sections rather than across them.
