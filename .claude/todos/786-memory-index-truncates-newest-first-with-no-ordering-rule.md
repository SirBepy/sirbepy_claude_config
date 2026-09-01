<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=2, content-hash=1e2f0cac -->
<!-- duplicate-checked -->
# Memory index truncates newest-first and nothing enforces an ordering

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the Auto Memory index degrade gracefully instead of inverted: the entries the harness drops
should be the least valuable ones, and that ordering should survive the next write rather than
decaying immediately.

## Context

Found 2026-08-25 during a `/cleanup-memory` run on `claude_usage_in_taskbar`. Three separate
findings, all measured, none of them previously written down anywhere.

**1. Truncation is newest-first, which is exactly backwards.** `MEMORY.md` is written in append
order, so the newest memory is the last line. The harness cuts the index at 200 lines. That project's
index was 201 lines, so the single entry being silently dropped was
`project_build_red_may_be_a_peers_wip.md`, written that same day. Receipt: the MEMORY.md content
injected into the session ended at line 200, and line 201 was absent.

**2. The limit is LINES here, not bytes.** Worth pinning because todo `320` recorded the opposite
for a different project ("the memory index at MEMORY.md is 20.2KB, approaching the 24.4KB read
limit"), and the warning text cites both. Measured on this index: a 24.4KB byte-cut would land
inside line 199 and drop three entries, but exactly 200 lines loaded. So the binding constraint
was line count. **Do not assume either unit globally** - the two projects disagree, and whichever
one a fix targets should be re-measured first.

**3. Trimming long index lines is a dead lever under a line cap.** 37 of the 201 lines exceeded 150
chars; trimming all of them to 150 reclaims 1.1KB and *zero lines*. Cheap to re-derive and easy to
propose, so it is recorded here to stop the next session trying it.

Applied in that project already, as a one-off: the index was rebuilt into three blocks - T0 axioms
(the 3-question test in `cleanup-memory/SKILL.md` Step 1.5), then entries whose file mtime is within
7 days, then everything else newest-first. Pure line moves, verified byte-identical when sorted, so
no entry was added, edited, or lost. The sacrificial line past 200 went from that day's memory to
the oldest memory in the dir.

That one-off decays. New memories append to the end of the file, so the next batch of writes puts
fresh entries back in the drop zone. Hence items (a) and (b) below.

## Approach

Three independently-claimable items. They do not depend on each other.

- [ ] **(a) Tier-append convention in `~/.claude/refs/memory-rubric.md`.** Its ADD step currently
      implies appending to the end of the index. Change it to insert at the tail of the entry's own
      block (axiom / recent / rest) so ordering does not decay at the next write. Without this,
      (b)'s reorder is undone within days.
- [ ] **(b) Make ordering a real `/cleanup-memory` step.** The skill has no ordering concept today;
      its Step 6 only adds, archives and fixes links. Add an explicit re-rank step using the tiers
      above, and state plainly that reordering is non-destructive (no entry removed) so it does not
      get swept under the compaction gate that correctly guards deletion.
- [ ] **(c) Fix the skill's orphan definition, which is ambiguous enough to give three answers.**
      Step 2 says a file counts as reachable if `MEMORY.md` links it "either way" (paren link or
      wikilink). Measured against the same 336-file dir, three defensible readings give three very
      different numbers: **72** orphans (credit a wikilink from any file, including from another
      orphan), **88** (strict BFS from `MEMORY.md` only), **132** (only what actually loads - the
      first 200 lines' direct links). The skill should name one, and the operationally honest one is
      the third, since it is the only figure that answers "does this memory reach a session".

## Acceptance

- A session that appends a memory does not push a newer one out of the loaded window.
- `/cleanup-memory` produces the same orphan count twice in a row, and states which definition it used.
- Re-running the reorder on an already-ordered index is a no-op.

## Notes

Duplicate check done against this backlog before filing. Two prior todos are adjacent but neither
covers this:

- `done/320-memory-index-hook-demands-destructive-compaction.md` (dev-origin, completed 2026-08-15)
  established that the size warning is advisory and that an index line is never deleted while its
  file exists. This todo is compatible with it and deliberately proposes **no deletion at all**.
  Note 320 explicitly rejected "merging clusters of memory files" - that was about concatenating
  memory *files* into 45KB blobs, which is a different operation from ordering index *lines*, and
  is not proposed here. 320's own unfinished option 3 (group index lines under `##` headings) is a
  near neighbour of item (b), but headings ADD lines, which under a 200-line cap costs one dropped
  memory per heading; ordering achieves the same "most relevant first" goal at zero line cost.
- `done/32-compact-the-memory-index.md` was dropped 2026-08-12 as low-worth routine housekeeping
  about a different project's index size. This todo is not a re-file of it: it is about ordering and
  measurement correctness, not about getting a byte count down.
