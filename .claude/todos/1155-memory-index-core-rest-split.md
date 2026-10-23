<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Memory retrieval: split each MEMORY.md into an 8 KB core and a searchable rest

**Type:** task
**Origin:** dev

## Goal

No project's memory index overflows the 24.4 KB load cut again, and memories outside the
always-loaded core are still findable on demand across every project.

## Context

Designed in `refs/permanent-memory.md` ("Retrieval quality"), picked by Joe on 2026-10-08 in todo
95's brainstorm. On that date zng-app's `MEMORY.md` was 24,853 bytes, past the cut, so its bottom
entries never loaded; claude-usage-in-taskbar's was 23,050. The design review (same date) required
a core budget and a demotion rule so the overflow does not grow back one level up.

## Approach

- Core: the entries passing `skills/cleanup-memory/SKILL.md` Step 1.5's axiom test, capped at
  8 KB. Everything else stays as a memory file but leaves the always-loaded index.
- `recall.py memory <terms>`: search every project's memory files (frontmatter + body), with
  citations, same fence as session search.
- `/cleanup-memory` enforces the cap and demotes entries that stop passing the axiom test.
- Memories with `triggers:` (todo 1153) still load at the point of use regardless of core status.

## Acceptance

- zng-app's index is under 8 KB after the split, and every demoted memory is still returned by
  `recall.py memory` for a keyword from its title.
- No memory file is deleted by the split; the index-line/file pairing rule in `CLAUDE.md`'s Memory
  Discipline section holds (a demoted file stays reachable through search, which the rule must be
  updated to recognise, or the file moves to a `rest/` subfolder that reachability checks know).

## Decided

Decided by /auto-do-todos on 2026-10-23.

- [x] [ARCH] Where a demoted memory lives - decided **a demotion-tier subfolder** (the existing convention: any subfolder of the memory dir except `archive/`, e.g. claude-usage-in-taskbar's `cold/`; `rest/` when a dir has none), because reachability.mjs already treated such subfolders as deliberately unindexed, so this reuses one mechanism instead of adding a second.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Needs an attended session: approve this CLAUDE.md Memory Discipline clause (CLAUDE.md has about 0 tokens of headroom, so `ci/check_instruction_budget.py` needs a trade elsewhere): "Tier exception: a memory file inside a demotion-tier subfolder of its memory dir (any subfolder except `archive/`, e.g. `cold/`, `rest/`) needs no index line and is not an orphan; `/cleanup-memory` moves a file there and deletes its index line in one pass, and `recall.py memory` still finds it."
- [ ] [DATA] After the clause lands, run `/cleanup-memory` Step 1.7 on the real indexes, attended, since it moves entries out of what every session in that project loads. Dry run 2026-10-23: claude-usage-in-taskbar 29,030 bytes (past the 24.4 KB cut, truncating today), zng-app 22,929, mc-plugins-tag 20,705, all against the 8,192-byte core cap.

## Notes

- /loop-todos cycle 2, 2026-10-23: tooling half built. `recall.py memory` searches every demotion tier (hits tagged `[cold]`/`[rest]`) and gains `--all-projects`; `reachability.mjs` resolves links into tiers and prints `core index: <bytes> / 8192 bytes [OVER by n]`; `cleanup-memory` SKILL.md gains Step 1.7 (core cap, axiom test, demote into the dir's tier). Tests in test_recall.py and test_reachability.cjs. Not applied to any real memory dir.
