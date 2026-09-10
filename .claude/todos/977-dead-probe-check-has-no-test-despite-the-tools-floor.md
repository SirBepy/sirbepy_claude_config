<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/968 shipped this script and recorded its one-off 143-commit validation;
     what it did not do, and what no other todo covers, is give it a repeatable test under the
     documented tools/ floor -->
# `tools/dead-probe-check.py` ships real parsing logic with no test, against `tools/`'s own floor

**Type:** task
**Origin:** ai

## Goal

Give `tools/dead-probe-check.py` a `tools/test_dead_probe_check.py` so `ci/run_tool_tests.py`
actually covers it, matching the floor that file's own docstring already declares for everything
under `tools/`.

## Context

Found 2026-09-10 by `/close` Phase 2's independent review of that session's own commits.

`ci/run_tool_tests.py`'s docstring states the rule: *"Twin of run_hook_tests.py for the scripts
under tools/. Those scripts are not hooks and never run in-session, but they carry real parsing
logic, so they get the same mechanical floor."*

`tools/dead-probe-check.py` (shipped by `done/968`) is exactly that shape: it parses a git diff,
applies a hand-tuned heuristic that requires a colon inside `title=`/`aria-label=` literals, and a
separate exact-match arm for `id=`/`data-testid=`/`name=`. It has no test file, so
`run_tool_tests.py`'s green "2/2" result never touches it, confirmed live: only `test_patch_file.py`
and `test_skill_eval.py` are discovered under `tools/`.

What the script DOES have is a one-off empirical validation recorded in `done/968`: 143 real commits
scanned, both directions of the actual incident reproduced in scratch worktrees, 1 finding and 0
false positives. That is strong evidence the heuristic was right ON THAT DAY. It is not a regression
test, and the colon requirement is precisely the kind of tuning a later "improvement" would widen
without noticing it had reintroduced the 9-false-positive version that was rejected.

Mitigating, and the reason this is not urgent: the tool is advisory only. It always exits 0 and
never blocks, so a silent regression costs a missed warning rather than a broken flow.

## Approach

1. Read `tools/test_patch_file.py` first and follow its shape; the point is that `run_tool_tests.py`
   discovers this the same way, not a new convention.
2. Cover the three arms that carry the heuristic, using inline fixture diffs rather than a real repo:
   - a removed `title="Label: detail"` line whose `Label:` prefix still appears in a probe directory
     is a finding;
   - a removed `id="foo"` matching exactly is a finding, and a near-miss is not;
   - a literal that was ADDED rather than removed is skipped.
3. Include the rejected shape as an explicit negative: a removed `title="Zoom"` with no colon must
   NOT be a finding. That single case is what separates this heuristic from the version measured at
   9 false positives to 1 true positive, so it is the one most worth pinning.
4. Do not re-run the 143-commit sweep. It is recorded in `done/968` and is not what a test file is
   for.

## Acceptance

- `python ci/run_all.py` reports 3 of 3 tool suites passing, up from 2 of 2.
- The colon-required negative case is present and passes.
- The test uses fixtures only, and touches no real project's history.

## Notes

- `done/968` also records the accepted residual that this script only runs from `/close` Phase 0,
  never per commit. That is a separate decision and not part of this todo.
