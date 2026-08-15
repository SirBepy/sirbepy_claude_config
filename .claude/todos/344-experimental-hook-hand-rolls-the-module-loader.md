<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# EXPERIMENTAL-command-chaining-detector.py still hand-rolls the module loader _testlib now owns

**Type:** task
**Origin:** ai

## Goal

Finish the loader dedupe that todo 316 started, so `grep -rn spec_from_file_location hooks/` returns
exactly one definition.

## Context

Todo 316 landed 2026-08-15: `hooks/_testlib.py` now owns `load_module`, `run_cases`, `report` and
`summarize`, and all six `hooks/test_*.py` suites import it instead of each carrying its own copy.

Its builder reported one remaining hit it deliberately did not touch:
`hooks/EXPERIMENTAL-command-chaining-detector.py:39-43` also hand-rolls
`spec_from_file_location` plus `exec_module`, to load `shell-content-write-guard.py` as a library.
It was out of scope because 316 was scoped to test files and this is a production spike hook, not a
test.

Worth noting before anyone reaches for this: the three `hooks/EXPERIMENTAL-*.py` files are kept
deliberately unpromoted, with their false-positive measurements recorded, per the hook doctrine in
`.claude/todos/PLAN.md` (the command-chaining detector flagged 55 percent of 30047 real commands).
So the value here is tidiness in a file that may never ship, which is why this is filed rather than
done.

## Approach

Import `load_module` from `_testlib` and delete the local copy. The same standalone-import property
316 established applies: CPython prepends the script's own directory to `sys.path[0]`, and both
files live in `hooks/`, so a bare `import _testlib` resolves with no path fiddling.

If it feels wrong for a production hook to depend on a file named `_testlib`, that is a legitimate
objection and the honest alternative is moving `load_module` into `hooks/_hooklib.py` (the
production shared library) and having `_testlib` re-export it. Pick one and say which.

Do not promote or otherwise change the detector's behaviour. This is a loader swap only.

## Acceptance

- `grep -rn spec_from_file_location hooks/` returns one definition.
- All six hook test suites still pass.
- The detector's own behaviour is unchanged, and it stays unpromoted.
