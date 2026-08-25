<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `/cleanup-todos` Step 5 calls `update-markers.ps1`, which does not exist

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/cleanup-todos`'s marker-refresh step executable as written, or stop the skill from
describing a tool it does not ship.

## Context

Hit 2026-08-21 during an `/auto-do-todos` run in `hubbub` (that run nests `/cleanup-todos` as its
Step 2).

`skills/cleanup-todos/SKILL.md` Step 5 says the main agent "never retypes a verdict field by hand"
and instead concatenates chunk CSVs "straight into Step 5's DataFile" for `update-markers.ps1`. It
then specifies a **diff gate** built entirely around that script: copy `.claude/todos/` to a scratch
dir, run the script there against the real DataFile, and diff every touched file's FULL content
before touching the real backlog.

`Test-Path C:\Users\tecno\.claude\skills\close\update-markers.ps1` returns **False**. The script is
not in `close/`, and a scan of `skills/cleanup-todos/` found no local copy either.

So the run had to hand-roll the marker rewrite, which is exactly the transcription step Step 5 says
caused the 2026-08-12 corruption. The diff gate, whose whole purpose is catching that corruption,
also could not run as specified, because it gates on the script.

## Approach

Pick one and say why in the commit:

1. Write `skills/close/update-markers.ps1` to the contract Step 5 already specifies: reads a
   DataFile with columns `file,complexity,worth,still_valid`, rewrites or inserts exactly one
   `<!-- cleanup: ... -->` line above each file's first `# ` heading, touches nothing else.
2. Rewrite Step 5 to describe a hand-edit procedure plus a diff gate that does not depend on a
   script, and delete every reference to `update-markers.ps1`.

Option 1 is better: the diff gate is the real value here and it only works against a deterministic
writer. A hand-edit procedure cannot be diffed against "what the tool would have produced".

Whichever is chosen, also check `reconfirm-count` semantics. Step 5 says the count increments when
`still_valid=true` AND the new `content-hash` matches the stored one, but the skill never defines
how `content-hash` is computed, so two runs using different hash methods will reset the count
forever and the staleness signal silently dies. Pin the algorithm in the skill.

## Acceptance

- `/cleanup-todos` Step 5 runs end to end with no hand-rolled file writing.
- The diff gate actually executes and rejects a deliberately corrupted DataFile.
- `content-hash` has one defined algorithm, stated in the skill.
- `python ci/run_all.py` passes.

## Notes

- Found alongside [[474-commit-step-8s-overlap-check-should-be-a-script]]; both are the same class
  of defect, a skill specifying a procedure precise enough to be code but shipped as prose.
