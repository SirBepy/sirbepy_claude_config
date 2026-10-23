<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1109 fixed repeated -m for commit-pathspec.sh only; 1046/1068/1161 are other split-hunks/commit-pathspec defects, none covers split-hunks' -m handling -->
# split-hunks.py commit keeps only the last -m, silently dropping the subject

**Type:** skill-improvement
**Origin:** ai

## Goal
`python skills/commit/split-hunks.py commit -m A -m B ...` stores A as the subject and B as a body
paragraph, exactly like `git commit -m A -m B` and `commit-pathspec.sh` (todo 1109).

## Context
- `skills/commit/split-hunks.py:316` declares `p_commit.add_argument("-m", "--message", required=True)`
  with no `action="append"`, so argparse keeps only the last value.
- mc_plugins_tag session 726c, 2026-10-08: a split commit passed a FEAT subject as the first `-m`
  and a "Tests: ..." paragraph as the second; the commit landed with "Tests: ..." as its whole
  message. Fixed by hand with `commit-tree` + CAS `update-ref` (same tree, reworded).

- Same session, second defect: two `--hunk <file>:<substring>` filters whose substrings both
  matched ONE `@@` hunk (two adjacent import lines, `java.io.IOException` and
  `java.util.logging.Level`) applied that hunk twice and failed with
  `git apply --cached --recount - failed (1): patch failed: ...DragonBallsPlugin.java:30`.
  Dropping the second `--hunk` fixed it. Selected hunks should be deduplicated.

## Done when
- A hunk matched by several `--hunk` filters is applied once.
- `-m` is `action="append"` and the values join with blank lines.
- `test_split_hunks.sh` covers a two-`-m` commit and checks the subject line.


## Notes

- Completed 2026-10-23 (loop-todos cycle 1): repeated -m accumulates like git commit -m A -m B; a hunk matched by several --hunk filters is kept once (one patch per path). Tests RED then GREEN, 33/33 pass.