<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=1, content-hash=ee8cee1c -->
# /cleanup-todos writes a "never" placeholder marker on shallow-tier todos, which its own Step 5 forbids

**Type:** skill-improvement

## Goal

Stop `/cleanup-todos` from stamping a content-free marker onto todos it never actually checked.

## Context

`~/.claude/skills/cleanup-todos/SKILL.md` Step 5 is explicit about the shallow tier:

> **Shallow-tier rows** (never actually verified): `last-checked` is left UNCHANGED at its pre-refresh snapshot value - nothing was checked, so nothing should look freshly checked. Only `complexity=unknown (shallow pass)` is written; `reconfirm-count` and `content-hash` are left unchanged.

A previous run did the opposite. Found on 2026-08-11 in `claude_usage_in_taskbar`: 47 todos carry this exact line, byte-identical across all 47:

```
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=0, content-hash=none -->
```

`last-checked never` and `content-hash=none` are not "left unchanged" - they are freshly invented placeholder values written into a file whose content was never read. The spec's own justification ("nothing should look freshly checked") is satisfied only by accident, because the literal string `never` happens to be un-parseable as a date.

Consequences seen in practice:

1. **Marker coverage lies.** 91 of 141 todos matched `cleanup: last-checked`, but only 44 had a parseable date. A coverage count taken the obvious way is off by 47, which is how this was noticed at all - two queries in the same run disagreed.
2. **Every consumer needs a special case.** Any staleness computation must now handle three shapes: a real date, the literal `never`, and no marker at all. Two of those mean the same thing.
3. **It is indistinguishable from a real check that found nothing.** Nothing in the line records that the file was never opened.

The ambiguity is in the spec text itself: Step 5 says to leave `last-checked` unchanged, but also says `complexity=unknown (shallow pass)` "is written". Writing one field of a marker that does not exist yet forces the implementer to invent the others. That is the actual defect - the instruction is unimplementable as written for a todo with no prior marker.

## Approach

Resolve the contradiction in Step 5, in favour of not writing at all:

> For a shallow-tier row with NO existing marker, write nothing. A missing marker already means "never checked"; a placeholder marker saying the same thing adds a second encoding of one state. For a shallow-tier row that DOES have a prior marker, rewrite only `complexity=unknown (shallow pass)` and leave `last-checked`, `reconfirm-count` and `content-hash` byte-identical.

Then add a one-line cleanup note so existing backlogs self-heal: on any run, delete a marker matching `last-checked never` outright rather than carrying it forward.

Consider also making Step 6's marker-coverage figure count files with a *parseable date*, not files matching the marker string, so a shape regression like this surfaces in the report instead of hiding until two queries disagree.

**While in here: there is no marker-writing helper, and that is why the format drifts.** `complete-todo.ps1` exists for archival, but Step 5 has no equivalent, so every run hand-rolls a throwaway script to stamp 40-odd files - which is exactly how one run invented `last-checked never`. A `refresh-marker.ps1 -Id <id> -Complexity <EASY|HARD|unknown> -Hash <8hex> -StillValid <bool>` that owns the format, computes `reconfirm-count` from the stored hash, and refuses to write a shallow-tier marker from scratch would make the rule above unbreakable instead of merely documented. Ship it alongside the spec fix, not as a follow-up.

## Acceptance

- A shallow-tier todo with no prior marker still has no marker after a `/cleanup-todos` run.
- A shallow-tier todo with a prior marker keeps its original `last-checked`, `reconfirm-count` and `content-hash` values exactly.
- The 47 existing `last-checked never` markers in `claude_usage_in_taskbar` are removed by the next run rather than preserved.
- Step 6's coverage number and the staleness nag agree with each other.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise already fixed. cleanup-todos/SKILL.md Step 5 now leaves shallow-tier last-checked unchanged, and the marker helper shipped as skills/cleanup-todos/update-markers.ps1 (bae56bd, hardened in da7ead7).
