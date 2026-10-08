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
