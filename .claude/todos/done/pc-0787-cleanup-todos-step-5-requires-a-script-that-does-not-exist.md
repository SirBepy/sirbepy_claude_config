<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /cleanup-todos Step 5 mandates a diff gate around a script that isn't on disk

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/cleanup-todos` Step 5 executable as written: either ship `update-markers.ps1`, or rewrite the
step to describe the marker update without naming a tool that does not exist.

## Context

Hit 2026-08-26 running `/cleanup-todos` on `claude_usage_in_taskbar` (33 todos).

`~/.claude/skills/cleanup-todos/SKILL.md` Step 5 is written around a script it names four times:

> "Copy `.claude/todos/` to a scratch temp dir, run `update-markers.ps1` there with the real
> DataFile, then diff every touched file's FULL content against the original"

and it describes the DataFile's CSV columns as "the first four columns exactly match
`update-markers.ps1`'s columns". **That script does not exist.** `ls ~/.claude/skills/close/` shows
only `complete-todo.ps1` and `reserve-todo-id.ps1`; a wider search finds no `update-markers.ps1`
anywhere under `~/.claude`.

The step is not optional decoration - it is the safety gate. Its own text says the gate exists
because a 2026-08-12 corruption was hidden by a marker-pattern-filtered diff, so the gate must diff
FULL file content. A step whose enforcement mechanism is missing silently degrades to "the agent
improvises", which is exactly the condition that produced the corruption it guards against.

What actually happened: the run hand-wrote an equivalent Node script, copied the backlog to a scratch
dir, ran it there, diffed all 33 files in full, confirmed only marker lines changed, then re-ran
against the real backlog. The gate's INTENT was satisfied, but by a one-off script that was deleted
afterwards, so the next run will re-improvise from scratch with no guarantee it reproduces the same
checks.

Second-order damage from the same gap: because the improvised script computed `content-hash` with its
own hash function, every `reconfirm-count` in that backlog reset to 1. The pre-existing hashes (from a
2026-08-20 run) were produced by some other unknown implementation and cannot be reproduced. The
"has this todo changed since last check" streak is therefore meaningless across implementations - it
only works if ONE canonical hasher owns it.

## Approach

Pick one, do not leave both:

1. **Ship the script** at `~/.claude/skills/cleanup-todos/update-markers.ps1`, taking `-DataFile`
   (the CSV) and `-TodosDir`. It owns the marker format AND the `content-hash` function, so
   `reconfirm-count` becomes comparable across runs. Update Step 5's path reference to point at it.
2. **Rewrite Step 5** to specify the marker update declaratively (exact comment format, exact hash
   algorithm and which sections feed it, the full-content diff gate) with no named script, so any
   implementation is reproducible from the spec alone.

Option 1 is preferred: the hash only means something if a single implementation owns it, and a spec
in prose will drift from whatever each session writes.

Either way, state in the step that a `content-hash` written by a different implementation invalidates
`reconfirm-count`, so a hasher change is a breaking change.

## Acceptance

- Step 5 can be followed end-to-end without inventing a tool.
- Two consecutive `/cleanup-todos` runs over an unchanged backlog produce identical `content-hash`
  values, so `reconfirm-count` increments instead of resetting.

## Notes

Filed by `/close` 2026-08-26. Sibling gap in the same family filed as `788` (`/cleanup-memory` has no
reachability tooling). Both are the same shape: a cleanup skill that specifies analysis it provides no
means to perform reproducibly.
- Dropped via /cleanup-todos 2026-08-27: premise dead. update-markers.ps1 DOES exist, at skills/cleanup-todos/update-markers.ps1 (6738 bytes), and this run executed it to write 49 markers with the Step 5 diff gate passing 49/49. The todo searched skills/close/ instead of the skill dir the SKILL.md actually points at; git log shows the script committed and fixed twice (da7ead7, 01b8e41). Origin ai, archived without a confirm gate per the skill origin rule.
