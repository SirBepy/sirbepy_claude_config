<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=96b2f06b -->
<!-- duplicate-checked -->
# Six live guards have no test file, so CI cannot see them break

**Type:** task
**Origin:** ai

## Goal

Give the six PreToolUse/Stop guards that currently have no `hooks/test_*.py` suite one each, so
`python ci/run_all.py` can actually detect a regression in them.

## Context

Found 2026-08-22 while writing `/code-check`'s Step 4a class policy (todo 451), and the discovery
is what shaped that policy.

`ci/run_hook_tests.py:15` discovers exactly `hooks/test_*.py`. Fourteen suites exist. These six
guards have none:

- `hooks/commit-guard.py`
- `hooks/flutter-workdir-guard.py`
- `hooks/package-manager-guard.py`
- `hooks/pr-guard.py`
- `hooks/schedulewakeup-guard.py`
- `hooks/status-marker-guard.py`

The concrete hazard, measured rather than imagined. A mechanical dead-symbol scan flagged
`hooks/_hooklib.py:63`'s `strip_quotes` as having zero references. It is not dead:
`hooks/package-manager-guard.py:28` and `hooks/flutter-workdir-guard.py:37` both import it as
`strip_quotes as _lib_strip_quotes`, which is why a name-keyed scan missed it. Deleting it would
have tripped each guard's fail-closed `except` block (`package-manager-guard.py:29-31`), blocking
every `npm`/`yarn`/`pnpm` and every flutter command for every session, **and `ci/run_all.py` would
still have reported 4/4 green**, because neither guard is discovered.

So the gap is not "these guards are untested" as a tidiness point. It is that `_hooklib.py` is
shared by nine hooks, and CI currently cannot tell you when a change to it breaks two of them.

Todo 382 already did exactly this work for `shortcut-mutation-guard.py`; that file is the pattern
to copy, and its Notes record the one real constraint (test the pure helpers, never let the test
reach a live API).

## Approach

1. Start with `flutter-workdir-guard.py` and `package-manager-guard.py`. They share `_hooklib`'s
   `strip_quotes` and are the two the incident above would have broken, so they buy the most.
2. Copy the shape of `hooks/test_shortcut_mutation_guard.py`: `_testlib.load_module` +
   `run_cases`, pure helpers only, no network and no real tool invocation.
3. Pin the aliased import itself as a case, so a future dead-code sweep that deletes
   `strip_quotes` fails loudly instead of silently disarming both guards.
4. `commit-guard.py` and `pr-guard.py` consume session markers; check `done/335`'s notes first,
   the marker-consume path is shared and already centralised in `_hooklib.consume_fresh_marker`.
5. `schedulewakeup-guard.py` was explicitly left out of scope by todo 250; confirm it is still
   live before writing a suite for it.

## Acceptance

- `python ci/run_all.py` reports more than 14 hook suites, all passing.
- Deleting `strip_quotes` from `hooks/_hooklib.py` makes the run FAIL. Demonstrate it, paste the
  failing output, and restore.
- No test reaches a live API or a real `git`/`npm` invocation.

## Notes

Do not edit a guard while it is policing this session. Copy to scratch, test there, install last.
`hooks/` is tracked as of `bcaa730`, so a mistake is recoverable, but a broken guard is silent.

Related: [[382-shortcut-mutation-guard-has-no-test-file]] is the same finding for a seventh guard
and is already done. [[402-oldest-fresh-marker-import-reads-as-dead-in-three-guards]] is the same
aliasing/re-export confusion in the other direction.
