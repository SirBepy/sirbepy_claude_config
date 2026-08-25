<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Four more dispatch templates still miss the guard markers

**Type:** skill-improvement
**Origin:** ai

## Goal

Finish what todo `392` started: point the remaining Agent-dispatch templates at
`refs/builder-preamble.md` so `hooks/dispatch-preamble-guard.py` stops rejecting them on first use.

## Context

Filed 2026-08-25 as an out-of-scope finding from `392`'s builder. `392` fixed 11 files, but it was
given a candidate list built from one loose grep by the orchestrator. The builder then ran its own
wider sweep and surfaced these, outside its assigned scope:

- `skills/cleanup-memory/SKILL.md` - two genuine templates ("dispatch exactly ONE subagent... full
  text of each memory in one prompt" and "Dispatch 2 subagents... the full apply set in each
  prompt"). Same shape as `cleanup-todos`, which `392` did fix. No markers, no pointer.
- `skills/figma-tiles/SKILL.md` - "Fan subagents out over the tile files for screen-by-screen
  review, one subagent per tile". No markers or pointer anywhere in the file.
- `skills/create-logo/SKILL.md` - "Fan out subagents only for a big batch request (5+ new
  directions at once)... model: 'sonnet', full conventions + brief in every prompt, no commits".
  A real but terse dispatch description; **lower confidence than the two above**, so confirm it is a
  template before editing.
- `skills/clockify-reconciliator/modes.md` - real dispatch language ("Give every subagent the live
  API key... tell it explicitly whether it has write access"). `392`'s builder skipped it believing
  the file was another agent's uncommitted work. That was stale: the clockify files were committed
  in `8670a30` earlier the same session, so the file was free and simply did not get checked.

The three markers, from `hooks/dispatch-preamble-guard.py`:

1. `Stage your changes but do NOT commit` OR `Leave all changes unstaged`
2. both `run_in_background` and `FORBIDDEN`
3. `.for_bepy/screenshots/` OR the literal line `READ-ONLY DISPATCH`

## Approach

1. Confirm each of the four is a REAL dispatch template, not incidental prose. `392` correctly
   rejected 6 of 16 candidates on exactly this basis, so the check matters.
2. Fix by POINTING at `refs/builder-preamble.md`, never by retyping the block. `skills/rate-it/panel.md`
   is the reference for what a correct pointer looks like.
3. Do NOT modify `hooks/dispatch-preamble-guard.py`. Settled by todos 364, 373 and 392.
4. Run BOTH `python ci/run_all.py` AND `bash skills/commit/prefilter-gate.sh <files>` before
   reporting. CI does not check for em dashes, and `392`'s builder left three because it was told to
   run only the former.

## Acceptance

- Each of the four is either fixed or recorded as not-a-template with a reason.
- A repo-wide grep shows no remaining dispatch template missing a marker or a pointer.
- `python ci/run_all.py` passes and the prefilter gate exits 0.

## Notes

`392`'s own list of six rejected false positives is in `done/392-*.md` - read it before re-deriving
which files are templates.
