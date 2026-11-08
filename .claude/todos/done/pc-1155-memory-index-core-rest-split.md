<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Memory retrieval: split each MEMORY.md into an 8 KB core and a searchable rest

**Type:** task
**Origin:** dev
**Summary:** No project's memory index overflows the load cut again, and memories outside the always-loaded core are still findable on demand.

## Why

On 2026-10-08 zng-app's MEMORY.md was 24,853 bytes, past the cut, so its bottom entries never loaded; claude-usage-in-taskbar's was already 23,050.

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

## Notes

- 2026-11-08 APPLIED (Joe approved all 9 on a card). Memory root is `~/.claude/projects` (both `.claude-personal\projects` and `.claude-dane\projects` are junctions to it), edited once. Each demoted file moved to the dir's tier (`rest/`, or the existing `cold/` for claude-usage) and its index line(s) deleted in the same pass; nothing deleted from disk; `reachability.mjs` shows `orphan-file: 0`, `orphan-index-entry: 0`, every index under 8,192. Before -> after bytes (files moved): zng-biller 22,468 -> 7,084 (72, 79 lines incl. the multi-line files); global 20,880 -> 8,041 (64); mc-plugins-tag 20,719 -> 8,097 (65); revaire-mobile 20,018 -> 8,164 (51); fibo 17,528 -> 7,980 (63, `fibo-backend2-admin-login` moved intact, content untouched per Joe); zng-admin 17,358 -> 8,058 (45); claude-usage-in-taskbar 13,005 -> 8,045 (45, `cold/` now 429); sirbepy-roblox 8,615 -> 8,089 (3); pomodoro-overlay 8,416 -> 8,060 (2, into `rest/`). Re-run drift vs the dry run: global lost two demote targets since 11-07 (`feedback_for_bepy_scope`, `feedback_blockquote_tilde_dot_escaping` no longer exist, index already clean) and missed the cap by 259 bytes, so the next two axiom-failing oldest entries went too (`feedback_lane_boundary_residuals_in_a_wide_run`, `feedback_subagent_token_cost`); claude-usage grew 186 bytes and needed `feedback_quiet_affordances_over_loud_ones` and `project_commit_pathspec_needs_own_range_and_force_coverage_for_inline_rust_tests` demoted too. Glued global line 64 removed whole. revaire-mobile `project_git_auth` (indexed twice) kept as is; its duplicate line is untouched. claude-usage `archive/` duplicate `*.older-cold-copy.md` files and `MEMORY.md.bak-20260825` left alone. sirbepy-roblox `feedback_subagents_never_commit` not demoted (newest mtime, never reached). Tooling used: throwaway scripts in C:\tmp\mem-demote (not committed).
- /loop-todos cycle 2, 2026-10-23: tooling half built. `recall.py memory` searches every demotion tier (hits tagged `[cold]`/`[rest]`) and gains `--all-projects`; `reachability.mjs` resolves links into tiers and prints `core index: <bytes> / 8192 bytes [OVER by n]`; `cleanup-memory` SKILL.md gains Step 1.7 (core cap, axiom test, demote into the dir's tier). Tests in test_recall.py and test_reachability.cjs. Not applied to any real memory dir.
- 2026-11-07: Joe approved the CLAUDE.md Memory Discipline tier-exception clause as written: "Tier exception: a memory file inside a demotion-tier subfolder of its memory dir (any subfolder except `archive/`, e.g. `cold/`, `rest/`) needs no index line and is not an orphan; `/cleanup-memory` moves a file there and deletes its index line in one pass, and `recall.py memory` still finds it." The same clause also covers a memory carrying `superseded_by:` frontmatter (`refs/memory-rubric.md:17-18`). Claude finds the `ci/check_instruction_budget.py` trade elsewhere in CLAUDE.md and shows the cut in the commit.
- 2026-11-07 (/loop-todos, unattended): clause LANDED in `CLAUDE.md` Memory Discipline (Tier exception, plus one sentence
  exempting `superseded_by:` memories). Trade: cut the "A conclusion stored without the conditions..." sentence from the
  gist bullet (moved to `refs/incidents.md`; `refs/memory-rubric.md` carries the same rule), the "Reaffirmed 2026-09-04"
  tail of the English-only rule (moved to `refs/incidents.md`), the "orchestrator controls that, so sonnet doesn't get to
  screw up..." tail of the sonnet bullet, and "ever"; and the desync sentence was tightened. `ci/check_instruction_budget.py`:
  CLAUDE.md 6,756 -> 6,755 tokens (ceiling 6,558, still 197 over, was 198), net -1 together with todos 1296, 1270 and 1272.
- 2026-11-07 DRY RUN of `/cleanup-memory` Step 1.7 done (four read-only scouts, nothing moved, edited or staged). Nine memory
  indexes are over the 8,192-byte core cap; every one can get under it by demoting only axiom-failing entries oldest-first.
  Full per-index move lists, anomalies and byte math: `.claude/todos/notes/1155-dry-run-2026-11-07.md`. Summary:
  zng-biller 22,468 -> 7,084 (72 files); global 20,905 -> 8,191 (64 files, 1 byte spare, glued line 64);
  mc-plugins-tag 20,719 -> 8,097 (65); revaire-mobile 20,018 -> 8,164 (51); fibo 17,528 -> 7,980 (63);
  zng-admin 17,358 -> 8,058 (45); claude-usage-in-taskbar 12,819 -> 8,135 (43, into the existing `cold/`);
  sirbepy-roblox 8,615 -> 8,089 (3); pomodoro-overlay 8,416 -> 8,060 (2, into `rest/`, not its `archive/`).
  The 10-23 figures no longer match: the todo's "zng-app 22,929" has no counterpart (that dir's index is 101 bytes) and
  claude-usage already shrank from 29,030. Flags for the morning card: fibo stores a plaintext admin password
  (`fibo-backend2-admin-login`, secrets review needed regardless of demotion); the global index has several
  Joe-preference memories the strict axiom reading demotes (a human pass on that one is worth it); two dirs have
  multi-line index entries Step 6 must delete whole. Apply needs Joe's card approval; todo left open.
- 2026-11-07: Joe said run `/cleanup-memory` Step 1.7 on the real indexes after the clause lands: dry run first, show the moves per index, apply only after his approval on a card. Dry run 2026-10-23: claude-usage-in-taskbar 29,030 bytes, zng-app 22,929, mc-plugins-tag 20,705, against the 8,192-byte core cap.
