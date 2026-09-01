<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=bc3b1b80 -->
<!-- duplicate-checked -->
# /cleanup-memory has no reachability tooling, so every run reinvents it and gets a different answer

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/cleanup-memory` Step 2 one canonical orphan-detection script, so the same memory directory
yields the same orphan count on every run instead of a number that depends on who wrote the throwaway
script that day.

## Context

Hit 2026-08-26 running `/cleanup-memory` on `claude_usage_in_taskbar` (336 memory files).

Step 2 asks for an index/file cross-check and calls it "mechanical - no subagent needed, no judgment
call". It is not mechanical as specified, for two compounding reasons.

**1. The definition is ambiguous, and the readings differ by 60 files.** Step 2 says a file counts as
reachable if `MEMORY.md` links it "either way" (a `(file.md)` link or a `[[wikilink]]`). Measured on
the same 336-file directory, three defensible readings of that sentence give three answers:

| reading | orphans |
| --- | --- |
| credit a wikilink from ANY file (including from another orphan) | 72 |
| strict BFS outward from `MEMORY.md` only | 88 |
| only what actually LOADS (`MEMORY.md`'s first 200 lines, direct links) | 132 |

The third is the operationally honest one - it is the only figure that answers "does this memory ever
reach a session" - but the skill's wording most naturally reads as the first.

**2. Nothing ships to compute any of them.** This run wrote five throwaway Node scripts in
succession, and the first two were WRONG: they resolved `[[token]]` against frontmatter `name:` only,
with no basename fallback, which under-resolved links and inflated the orphan count. Two different
wrong counts (93, then 107) were reported to the dev before the resolver bug was found. A subagent
auditing the same directory independently produced yet another pair of numbers by yet another method.

That is four different orphan counts for one unchanged directory inside one session. Step 2 explicitly
tells the run to "report the counts of both (`orphan-file: N`, `orphan-index-entry: N`) even when
zero", so a number that swings by 60 depending on implementation is presented to the dev as if it were
a measurement.

The same run also found the skill has no concept of a demotion tier at all: this directory had a
`cold/` folder (74 files, later 111) that Step 6 would have bulk-re-indexed, adding ~74 lines to an
index the harness already truncates at 200.

## Approach

1. Ship `~/.claude/skills/cleanup-memory/reachability.mjs` taking a memory-dir path, emitting all
   three counts plus the file lists. Resolution rules stated once, in code: a `[[token]]` or
   `(file.md)` resolves against frontmatter `name:` OR basename, and the "actually loads" pass
   respects the harness line cap.
2. Rewrite Step 2 to name ONE definition as authoritative for its reported figure - recommend "what
   actually loads", since re-indexing decisions hinge on it - and to report the others only as
   context.
3. Teach the skill that a demotion subfolder may exist: files under it are deliberately unindexed and
   must never be bulk re-indexed by Step 6. See `claude_usage_in_taskbar`'s
   `memory/cold/README.md` for a worked example of the tier's rules.
4. State the line cap explicitly in Step 1.5 alongside the existing KB warning. Measured on this
   directory 2026-08-25: the cut was at 200 LINES (a 24.4KB byte-cut would have landed inside line
   199 and dropped 3 entries; exactly 200 lines loaded). Note that todo `320` recorded a BYTE-based
   limit on a different project, so the unit is not global and must be re-measured per project.

## Acceptance

- Two consecutive `/cleanup-memory` runs on an unchanged memory dir report identical orphan counts.
- The skill's reported orphan figure names which definition produced it.
- A run against a memory dir containing a demotion subfolder does not propose re-indexing it.

## Notes

Filed by `/close` 2026-08-26. Sibling gap filed as `787` (`/cleanup-todos` Step 5 names a script that
does not exist). Related: `786`, which covers index ORDERING (truncation drops newest-first) and
carries the same orphan-definition point as its item (c) - if 786 item (c) is done first, this todo's
step 2 is already satisfied and should be checked off rather than redone.
