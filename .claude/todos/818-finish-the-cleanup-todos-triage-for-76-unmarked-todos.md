<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=49129a95 -->
<!-- duplicate-checked -->
# Finish the /cleanup-todos deep triage for the 76 todos that still carry no marker

**Type:** task
**Origin:** dev

## Goal

Complete the `/cleanup-todos` run started 2026-08-27 that only got through 50 of 126 todos. Every
backlog file should carry a `<!-- cleanup: last-checked ... -->` header marker with a real
complexity/worth verdict behind it, and the backlog-wide dedupe step should actually have run once.

## Context

2026-08-27. Joe ran `/cleanup-todos`, then at `/close` Phase 0 explicitly chose "finish it first"
when told the run was partial. It still could not be finished: the fan-out died twice, first on a
session limit (reset 4:30pm) and then, on the retry ten minutes later, on the **weekly** limit
(resets 3am). All four agents of the second attempt returned nothing.

What DID land, and must not be redone:

- Chunks 1 and 2 (ids `95` through `468`, 50 todos) got the full deep pass with real re-verification
  evidence. Their markers are written and committed in `d5195ad`.
- `406` archived to `done/` - premise dead, `/test` no longer routes Flutter e2e to Patrol.
- `787` archived to `done/` - premise dead, `update-markers.ps1` does exist, at
  `skills/cleanup-todos/update-markers.ps1`. Note
  `done/473-cleanup-todos-calls-a-script-that-does-not-exist.md` is its already-completed
  predecessor, so this subject has now been filed twice and resolved twice.
- `459`'s marker is written to disk but deliberately NOT committed: that file carries a concurrent
  session's uncommitted work, so it was dropped from the commit pathspec. Whoever commits `459` next
  takes the marker along with it.

What did NOT run at all:

- Deep triage of the 76 unmarked todos. Find them with: for each `.claude/todos/*.md` except
  `PLAN.md`, `head -5` has no `cleanup: last-checked` line.
- Step 2's backlog-wide dedupe. No dedupe verdict exists for this backlog at all right now. Chunks 1
  and 2 each reported "no duplicates" but only within their own 25-file windows, which is not the
  same thing.

Distinct from `done/284-cleanup-todos-agents-should-emit-machine-readable-rows.md` and
`done/370-cleanup-todos-must-resolve-its-reference-point-first.md`: both shipped and both were
exercised successfully by this run (the CSV handoff, the diff gate, and the printed 64-ahead/0-behind
reference point all worked). This todo is the unfinished data, not a missing mechanism.

## Approach

Re-run `/cleanup-todos` from Step 1. It is idempotent by design: Step 5 re-scores every row it is
given, and the 50 already-marked todos will simply get a fresh `last-checked` and an incremented
`reconfirm-count`. There is no partial-resume mode and building one is not worth it.

Two things to carry in rather than rediscover:

1. **Chunk the fan-out narrower than the default.** `DEEP_CHUNK_SIZE` is 30 and `DEEP_MAX_CHUNKS`
   is 6, which is what produced a 6-wide fan-out the quota could not survive, twice in one day. See
   `[[819-cleanup-todos-step-4-fanout-has-no-session-budget-guard]]` - fixing that first makes this
   safe to run; running this first will probably just reproduce the same death.
2. **The Step 5 diff gate works, use `diff -u` for it.** A PowerShell `Compare-Object` line diff
   misreports files as offenders with empty added/removed sets. `diff -u` over a scratch copy gave a
   clean 49/49 verdict first try.

## Acceptance

- Every `.claude/todos/*.md` except `PLAN.md` has exactly one `cleanup: last-checked` marker in its
  header region, above the first `# ` line.
- A dedupe verdict exists for the whole backlog, even if it is "no duplicates found".
- The Step 5 diff gate passed against a scratch copy before anything was written to the real backlog.
- No file belonging to a concurrent session's uncommitted work is swept into the commit. Check
  `git diff -- <pathspec>` for foreign hunks before committing, the way this run caught `459`.

## Notes

- Weekly limit resets 3am Europe/Warsaw, so 2026-08-28 or later.
- Related: `[[820-commit-overlap-check-needs-an-explicit-timeout]]`, hit during the same run.
