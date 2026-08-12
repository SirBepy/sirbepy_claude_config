<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=5, reconfirm-count=1, content-hash=7d86d018 -->
# Compact this project's memory index below the read limit

**Type:** task
**Origin:** ai

## Goal

Get `MEMORY.md` for this project under 140 lines so it stops crowding every session's opening
context, without losing anything that's still true.

## Context

Filed at session close 2026-07-29. A `PostToolUse` hook fires on every edit to the index. As of
2026-08-03 it reads: "The memory index at MEMORY.md is 161 lines, approaching the 200-line read
limit. Compact it to under 140 lines now: keep one line per entry, move detail into topic files,
and merge or drop stale entries." (The threshold is now stated in LINES, not KB as when this todo
was filed.)

Path: `C:\Users\tecno\.claude-personal\projects\C--Users-tecno-Desktop-Projects-fibo\memory\MEMORY.md`
(note: `.claude-personal`, not the `.claude-fibo` path this todo originally recorded). As of
2026-08-03 it is 161 lines: 136 entries at one line each, 8 section headers, 16 blanks, 1 title.
It is loaded into context every session, so the size is a per-session tax.

Because it is already one line per entry, hitting 140 requires genuinely merging or dropping
roughly 20 entries. Trimming hook text alone will not get there anymore.

Deliberately NOT done inline when the hook first fired: compaction means merging or dropping
entries, and `/cleanup-memory` gates that behind Joe's confirmation for good reason. Rewriting 87
lines of his memory unattended at session close is not the same job as trimming a file.

Known compaction material spotted along the way:
- Several one-line hooks run 150+ characters where 100 would do; trimming hook text alone recovers
  a couple of KB without touching a single entry.
- `pr-base-is-backend1.md` is already marked SUPERSEDED by `develop-means-main.md`.
- `project-fibo-v2-frontend-shell.md` says "SUPERSEDED direction: see frontend2/ plan".
- `fibo-main-padding-vh-calc-bug.md` and `fibo-frontend-main-is-scroll-container.md` are both about
  the same `<main>` element and may merge.

## Approach

1. Run `/cleanup-memory` - it audits for staleness, dead references and duplication, and
   confirm-gates every move.
2. Prefer shortening hook text over dropping entries; drop only what the audit proves stale.
3. Re-check the size after: the hook should stop firing.

## Acceptance

- `MEMORY.md` under 17.1KB and the edit hook no longer warns.
- No entry deleted without Joe confirming it in the `/cleanup-memory` pass.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 176; renumbered to 32 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise holds; the fibo `MEMORY.md` is now 156 lines, down from the 161
  recorded on 2026-08-03, still above the 140 target. Warn that the todo's own compaction-material
  list (the SUPERSEDED entries and the mergeable padding-bug pair) was derived from the stale 161-line
  snapshot and must be re-derived against current content before executing.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: run `/cleanup-memory` against the fibo `MEMORY.md`, following its own confirm gate,
  applying the merges the todo already identifies until the file is under 140 lines. The skill's
  confirm gate is execution machinery, not a decision blocking the start. This was produced by a
  strict second-pass re-triage that specifically asked whether a defensible answer exists without
  the dev; it concluded yes. Not executed only because the session ended.
- Dropped via /cleanup-todos 2026-08-12: worth 4/10. Routine housekeeping (fibo MEMORY.md at 156 lines vs a 140 target), largely self-triggering via the existing hook, low leverage as a standalone todo.
