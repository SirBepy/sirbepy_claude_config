<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1065/1180/1187/1038/1059 are about the push gate, duplicate guard and code-check's own rules; this is a list of concrete findings in specific files -->
# Structural and test-gap findings from the 2026-10-28 push code-check (release.py errors, splits, comment tense, small gaps)

**Type:** task
**Origin:** ai

## Goal
Work through the filed (not applied) code-check findings below; decline any that are churn with a reason in Notes.

## Context
From the 2026-10-28 pre-push `/code-check` over the 96-commit range (release session). Each is independent.
1. `skills/release/release.py:552-583` (main) catches only `Fail`; an OSError from `write_bytes` (read-only file) or a RecursionError from `parse_json_spans` exits with a traceback, though the docstring promises `{"error": ...}` on every non-zero exit. Add a read-only package.json test.
2. `skills/release/ship-config.py:197` `cmd_set` detects the missing-client-list case by `"client list" in why`, coupling it to prose; return a distinct reason code from `classify()`. Also its module docstring (`:9-11`) does not list the missing/empty client list as an `unknown` cause.
3. `Fail` class and the argparse-to-JSON main pattern are duplicated in `ship-config.py:47` and `release.py:35`.
4. Split candidates (class 2): `skills/commit/commit-pathspec.sh` (1255 lines: check chain vs path toolkit, seam like `_argv-budget.sh`), `skills/commit/test_commit_pathspec.sh` (1796 lines; it is also the suite that times out under concurrent CI), `skills/release/release.py` (JSON span parser vs commands; mind `python -I` loading as `ship-config.py` does).
5. Test gap: `commit-pathspec.sh:311,746-754` `prime_head_blob_cache` (16+ untracked files with 2 markers or `--own-since`) never runs in CI, yet it decides trusted vs UNVERIFIED own-ranges.
6. Comments narrating the old bug instead of what is (global CLAUDE.md Code Style): `commit-pathspec.sh:211`, `test_commit_pathspec.sh:1580,1625`, `test_split_hunks.sh:158`, `ci/run_all.py:156`.
7. `skills/mockup/verify-board.cjs:174`: a plan with no `steps` key throws a TypeError (exit 3 with a stack trace); guard with `plan.steps ?? []`.
8. `skills/close/rename-session.sh:165-175`: the `--close` host-managed refusal has no test (`test_rename_session_close.py` drives only the .ps1).
9. `skills/cleanup-memory/reachability.mjs:62-71`: the CORE_CAP const landed between `collectFiles`' doc comment and the function; move it (exercise test: `node skills/cleanup-memory/test_reachability.cjs`).

## Approach
One commit per item; each behaviour change gets its failing-first test.

## Acceptance
Every item is fixed or declined in Notes; `python ci/run_all.py` passes.
