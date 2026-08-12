<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=1, content-hash=02287e05 -->
# /cleanup-todos: deep-pass agents should emit machine-readable rows, and marker runs need a real diff gate

**Type:** skill-improvement
**Origin:** ai

## Goal

Close two gaps in `~/.claude/skills/cleanup-todos/SKILL.md` that made the 2026-08-12 run more manual
and less safe than it looked: the main agent hand-retypes every verdict, and the run's own
verification could not see the corruption it caused.

## Context

**Gap 1 - the verdict table is retyped by hand.** Step 4's chunk agents return a block format
(`ID:` / `WORTH:` / `COMPLEXITY:` / ...) as prose. Step 5's `update-markers.ps1` consumes a CSV. So
the main agent reads ~95 prose blocks and manually transcribes id, complexity, worth and still_valid
into CSV rows. Done three times in one run (90 rows, then 12, then 1). Every row is a chance to
mistype a score onto the wrong todo, and nothing downstream can detect that - a wrong `worth` looks
exactly like a right one.

The dispatch prompt already fixes the output shape rigidly, so it is one step from being parseable.

**Gap 2 - the verification had a hole that hid real corruption.** The run verified
`update-markers.ps1` by copying the backlog, running the script, and diffing - but the diff
*filtered out lines matching the marker pattern*, on the reasoning that those were the lines meant to
change. That is precisely the filter that hides a marker-shaped line being rewritten somewhere it
should not be.

It did hide one. Todo `99` documents the marker format and quotes an example marker inside a fenced
code block. `update-markers.ps1` searched the whole file for the marker, matched that prose line
instead of the header, and `String.Replace` rewrote it. The verification reported "zero non-marker
lines changed" and was technically correct and practically wrong. Caught later by `/code-check`,
restored from an ad-hoc zip.

The script bug itself is fixed (marker search anchored above the title line, splice by index instead
of `String.Replace`). The process gap is not.

## Approach

In `skills/cleanup-todos/SKILL.md`:

1. **Step 4:** require the chunk agents to return their verdicts as CSV rows matching
   `update-markers.ps1`'s header (`file,complexity,worth,still_valid`) IN ADDITION to the prose block
   per todo, or via a `schema` on the dispatch. The evidence and reasons stay prose - only the four
   machine-consumed fields become structured. The main agent then concatenates rather than
   transcribes.
2. **Step 5:** add a verification gate that a marker run must pass before touching real files:
   snapshot the backlog, run against the copy, and diff **full content with no line filtering**. The
   only permitted differences are (a) one added or replaced marker line per file, positioned above
   that file's first `# ` heading. A marker-shaped line changing anywhere below the heading is a
   FAILURE, not an expected change. State plainly that filtering the diff by the marker pattern
   defeats the check.

## Acceptance

- A `/cleanup-todos` run produces its CSV without the main agent retyping any verdict field.
- The Step 5 gate rejects a script that rewrites a marker-shaped line below the title heading.
- `skills/cleanup-todos/update-markers.ps1` still passes the gate.

## Notes

- Filed by `/close` on 2026-08-12, from that session's own failure. See `266` (which asked for the
  script that now exists) and `99` (the todo whose prose was the casualty).
