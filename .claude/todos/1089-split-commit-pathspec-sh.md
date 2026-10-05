<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-05; grepped backlog + done/ for "commit-pathspec" split / "session-liveness" / "coverage-check.sh", no hit. -->
# Split commit-pathspec.sh's session-liveness and coverage-check blocks into sibling scripts

**Type:** task
**Origin:** ai

## Goal
`skills/commit/commit-pathspec.sh` stops being one 563-line procedural script by moving its two
self-contained blocks into their own scripts, the way overlap-check.sh and foreign-hunk-check.sh
already are.

## Context
Found by the 2026-10-05 pre-push /code-check over the unpushed range (class 2, structural).
At HEAD, commit-pathspec.sh mixes arg parsing, four sequential gates, a session-marker liveness
computation (roughly lines 304-371: session_marker_dir, marker_shares_this_repo,
session_marker_count / multi_session) and the pathspec coverage check (roughly lines 448-547:
in_pathspec, check_coverage_hit, coverage_move / coverage_other). The script already shells out
to `skills/commit/overlap-check.sh` and `skills/commit/foreign-hunk-check.sh`.

## Approach
- Extract the liveness block to `skills/commit/session-liveness.sh` and the coverage block to
  `skills/commit/coverage-check.sh`, called the same way the two existing siblings are.
- Keep every printed verdict line byte-identical so `test_commit_pathspec.sh`'s assertions hold.

## Acceptance
- `bash skills/commit/test_commit_pathspec.sh` passes with no assertion edits.
- `python ci/run_all.py` passes.
