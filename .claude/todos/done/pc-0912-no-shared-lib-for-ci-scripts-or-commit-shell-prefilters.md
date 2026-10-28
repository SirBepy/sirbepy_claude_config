<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=6, reconfirm-count=1, content-hash=511f2aac -->
<!-- duplicate-checked: todo 910 covers the Python hooks/_hooklib.py regressions. This is a different tree with no shared-lib convention at all, which is why the duplication has nowhere to go. -->
# CI scripts and commit shell prefilters have no shared lib, so both duplicated

**Type:** task
**Origin:** ai

## Goal

Decide whether `ci/` and `skills/commit/`'s shell scripts get a shared library the way
`hooks/_hooklib.py` already serves the Python hooks, then collapse the two confirmed duplications
onto it.

## Context

Found 2026-09-04 by `/code-check` over the `/mega-todos` run diff. Two independent duplications,
both with the same root cause: there is nowhere obvious to put a shared helper, so each script grew
its own copy.

1. **`ci/run_all.py:80-96` (`check_prefilter_suites`) and `ci/run_hook_tests.py:24-38`
   (`_tracked_hook_files`)** both run `git -C <root> ls-files <dir>`, build a set of tracked
   relative posix paths, and filter test candidates against it. `check_prefilter_suites`'s own
   docstring says it does the "same as run_hook_tests.py's todo-805 fix" - and then reimplements it.
   Both landed the same day, from different agents.
2. **`skills/commit/overlap-check.sh` and `skills/commit/foreign-hunk-check.sh`** now both define a
   byte-identical `git_c()` wrapper and the same `-C|--repo` argument-parsing shape.
   `skills/commit/_prefilter-lib.sh` exists and is sourced by `comment-noise.sh`,
   `comment-tense.sh`, `em-dash.sh` and `secret-scan.sh` - but not by these two, which is the same
   gap todo 885 already names for `overlap-check.sh` alone. `foreign-hunk-check.sh` makes it two.

The decision is worth making now rather than after a third script repeats it, which is exactly how
both of these happened.

## Approach

1. For the shell half, prefer folding `-C`/`--repo` support into `_prefilter-lib.sh`'s existing
   `parse_repo_arg`, and point both scripts at it. That closes todo 885 too - check whether 885 is
   still open and fold it in rather than filing over it.
2. For the Python half, extract one `tracked_files(root, subdir)` into a small `ci/_cilib.py` and
   import it from both. Keep it tiny; two callers do not justify a framework.
3. `skills/commit/test_prefilters.sh` and `skills/commit/test_comment_noise.sh` both run under
   `python ci/run_all.py` now, so the shell half has a real verification floor for the first time -
   use it.

## Acceptance

- `git_c()` and the repo-arg parsing are defined once for the commit shell scripts, and
  `python ci/run_all.py` exits 0 with its prefilter suites green.
- The tracked-files filter is defined once across `ci/`.
- Todo 885 is either closed by this work or explicitly left open with a reason.

## Notes

- Filed by /mega-todos on 2026-09-04 from the run's own `/code-check` pass.
- DONE 2026-09-10 via /loop-todos cycle 3, and it closed todo 885 as a byproduct. Python half: ci/run_all.py and ci/run_hook_tests.py each ran their own git ls-files filter; both now import tracked_files from the new ci/_cilib.py. Shell half: overlap-check.sh and foreign-hunk-check.sh each defined a byte-identical git_c and their own repo-arg parsing instead of using _prefilter-lib.sh, whose own header already claimed to be shared by skills/commit/*.sh; both now source it and call parse_repo_arg, which was extended to accept -C alongside --repo. That extension is additive, since all four existing callers only ever passed --repo, and it was needed because the new commit-pathspec.sh calls both scripts with -C. The refactoring method was followed properly, including the honest part: the exercise test skills/commit/test_prefilters.sh covers only the no--C path of overlap-check.sh, so the builder said plainly that foreign-hunk-check.sh and the -C and --own paths have no tracked coverage, and hand-verified both against a scratch repo across full-own, partial-own and no-own cases, matching pre-refactor exit codes exactly. python ci/run_all.py exits 0 with 2 of 2 prefilter suites passing.
