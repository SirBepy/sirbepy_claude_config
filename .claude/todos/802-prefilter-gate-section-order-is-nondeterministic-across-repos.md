<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=3, reconfirm-count=2, content-hash=1e88f260 -->
<!-- duplicate-checked -->
# prefilter-gate.sh's section order is nondeterministic once two repos are involved

**Type:** task
**Origin:** ai

## Goal

Make `prefilter-gate.sh`'s multi-repo output order stable, so two runs over the same paths print
the same thing.

## Context

Found 2026-08-26 by reading todo 412's fix (`skills/commit/prefilter-gate.sh:47`, commit `e61d305`).

The fix groups path arguments into a bash associative array keyed by resolved repo root, then
iterates `for repo_key in "${!group_paths[@]}"`. Bash associative-array key order is hash-based,
not insertion order, so with two or more repos in one invocation the `=== script.sh (repo) ===`
sections can come out in either order between runs.

**Deliberately filed as low priority.** The single-repo case, which is every ordinary commit, has
exactly one key and is unaffected, so this cannot reach the hot path. Exit codes are unaffected
either way. The cost is only that a mixed parent-plus-submodule report is not diffable run to run,
which matters for a human comparing two runs and for any future test that asserts on full output.

UNVERIFIED: I did not observe an actual order flip, only read the iteration construct. Bash may
happen to be stable for two keys in practice. Confirm the flip is real before spending effort here;
if it cannot be reproduced across, say, 20 runs with three repos, close this as not-a-problem rather
than hardening against a hypothetical.

## Approach

1. Try to reproduce: build a parent with two submodules, plant a violation in each plus one in the
   parent, and run the gate 20 times over all three paths, comparing full stdout each time. If the
   order never varies, close this todo with that evidence recorded.
2. If it does vary: keep a parallel ordered list of repo keys in first-seen order (a plain array
   appended to only when a key is new) and iterate THAT instead of `"${!group_paths[@]}"`. Put the
   cwd repo first unconditionally, since its plain-header output is the byte-identical hot path and
   readers expect it at the top.
3. Do not switch away from the associative array itself. It is the right structure and the ordering
   fix is additive.

## Acceptance

- Twenty consecutive runs over a three-repo path set produce byte-identical stdout.
- The cwd repo's section is first, with its plain `=== script.sh ===` header unchanged.
- Every non-submodule shape stays byte-identical (see `801`'s acceptance list for the seven shapes
  and the `git show HEAD:` capture trick).
- `python ci/run_all.py` passes. Note in the report that CI does not cover this script, so a green
  run is not evidence either way.

## Notes

- There is no test file for any script under `skills/commit/`, so the fixture is the only check.
  That absence is `501`'s territory.
