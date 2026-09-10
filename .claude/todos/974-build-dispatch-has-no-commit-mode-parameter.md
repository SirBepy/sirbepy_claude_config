<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/949 and done/938 both changed build-dispatch.ps1 today but neither
     touched COMMIT_MODE - 949 was the context round-trip, 938 was JS-literal escaping; this is a
     third, independent gap in the same script -->
# `build-dispatch.ps1` always emits the per-builder commit block, even in barrier mode

**Type:** bug
**Origin:** ai

## Goal

Make `skills/mega-todos/build-dispatch.ps1` honour `COMMIT_MODE`, so a run whose Step A chose
`barrier` stops handing every builder a per-builder commit procedure it is not supposed to use.

## Context

Filed 2026-09-10 by `/loop-todos` cycle 4, from the out-of-scope findings of the builder that closed
`done/949-build-dispatch-forces-a-write-read-retype-round-trip-per-dispatch.md` and
`done/938-workflow-scripts-cannot-carry-the-builder-preamble.md`.

`skills/mega-todos/SKILL.md` documents two commit modes and has a "Barrier COMMIT_MODE" section
describing the variant where builders do NOT commit and a barrier commits for them. But
`build-dispatch.ps1` has no `COMMIT_MODE` parameter at all: it emits the per-builder commit block
unconditionally, in both the full and the new compact mode.

So a run that sets `COMMIT_MODE = barrier` in Step A still ships every builder a prompt telling it to
commit its own work. Whether that produces a wrong outcome depends entirely on the builder noticing
the contradiction between its prompt and the rest of the run, which is exactly the kind of thing that
holds until it does not.

The builder that found this deliberately did NOT expand scope to fix it, and preserved existing
behaviour in both modes rather than guessing at the barrier variant's shape. That was the right call
and it is why this is a separate todo.

## Approach

1. Read `skills/mega-todos/SKILL.md`'s Barrier COMMIT_MODE section first and establish what a barrier
   builder's prompt is actually supposed to say instead of the commit block. Do not infer it from the
   parameter name.
2. Add a `-CommitMode` parameter to `build-dispatch.ps1` with the per-builder block as the default,
   so every existing caller keeps working untouched.
3. In barrier mode, emit whatever Step 1 established, and make sure the three
   `dispatch-preamble-guard.py` markers still appear verbatim in the output. The staging line is the
   one at risk here: a per-builder-commit prompt cannot truthfully carry the normal "do NOT commit"
   sentence, which is why the skill has an injected commit block in the first place, so check which
   variant a barrier prompt needs.
4. Cover both modes in the script's own exercise, and paste output for each.

## Acceptance

- `build-dispatch.ps1 -CommitMode barrier` emits a prompt with no per-builder commit procedure.
- The default with no flag is byte-identical to today's output, so no existing caller changes.
- All three preamble-guard markers survive in both modes, proven by grep.
- `python ci/run_all.py` exits 0.

## Notes

- Both other `build-dispatch.ps1` todos closed on 2026-09-10 without touching this, so read their
  `done/` entries before starting: the script now also has `-Compact` and `-AsJsLiteral` modes, and a
  barrier variant has to work with both.
