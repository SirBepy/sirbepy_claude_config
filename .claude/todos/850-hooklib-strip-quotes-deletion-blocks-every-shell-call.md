<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=1, content-hash=74c89853 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for _hooklib / strip_quotes / shell-access canary: only done/501 (the parent), no live match. -->
# Deleting one `_hooklib` symbol hard-blocks every shell call in every session

**Type:** skill-improvement
**Origin:** ai

## Goal

Give this repo a way to notice that a `hooks/_hooklib.py` change has cut off shell access, before the
session discovers it by being unable to run anything.

## Context

Found 2026-08-31 while executing todo `501` in a `/mega-todos` run, and measured first-hand rather
than reasoned about.

`501` predicted that deleting `strip_quotes` from `hooks/_hooklib.py` would silently disarm
`package-manager-guard.py` and `flutter-workdir-guard.py` while `ci/run_all.py` still reported green.
Its builder ran that deletion as the required demonstration. The real blast radius is much larger:

- `hooks/dev-backend-guard.py` ALSO imports `strip_quotes as _lib_strip_quotes`, and it is registered
  in `settings.json` under the PreToolUse matcher `^(Bash|PowerShell)$`, so it fires on **every**
  Bash and **every** PowerShell tool call, in every session on this machine, not only on
  npm-flavoured or flutter-flavoured ones.
- That guard fail-closes at import time. With the symbol gone, every shell call in the session died
  before Python could start, with:

  > `[dev-backend-guard] FATAL: cannot import _hooklib (cannot import name 'strip_quotes' from
  > '_hooklib' ...); blocking to avoid silently disabling this guard.`

- So `ci/run_all.py` never printed FAIL. It never ran at all, because the tool call that would have
  launched it was blocked first. The failure mode is worse and less legible than `501` assumed: not
  a silent green, but a session with no shell.

The builder restored the file immediately and proved it restored with an empty
`git diff HEAD -- hooks/_hooklib.py`. Nothing is broken now.

Fail-closed is the right default for that guard and should NOT be relaxed. The gap is that nothing
warns you before you are locked out, and the recovery path is not written down anywhere.

## Approach

1. Enumerate every importer of `hooks/_hooklib.py` and note which are registered against a broad
   matcher (`^(Bash|PowerShell)$` or similar). Today at least three import `strip_quotes`:
   `package-manager-guard.py`, `flutter-workdir-guard.py`, `dev-backend-guard.py`.
2. Decide the mechanism. Options, roughly in increasing cost:
   - a comment header in `_hooklib.py` naming the broad-matcher importers and warning that removing a
     symbol locks the session out of its own shell;
   - a `ci/` check that imports every hook module and fails if any raises, which would catch it
     before commit rather than at the next tool call;
   - a documented recovery path (edit `settings.json` to unregister the guard, or set its
     `CLAUDE_DEV_BACKEND_BYPASS` env var) written where someone locked out can still reach it.
3. Prefer the CI check plus the recovery note. The comment alone is the option this repo has already
   watched fail twice for sibling problems.
4. Whatever lands, verify it by actually breaking `_hooklib.py` in a scratch copy, never the live one.

## Acceptance

- [ ] A `_hooklib.py` change that breaks any hook's import is caught by `python ci/run_all.py`
- [ ] The recovery path for a locked-out session is written down somewhere reachable without a shell
- [ ] `dev-backend-guard.py`'s broad matcher is named wherever `_hooklib`'s fragility is discussed
- [ ] Verified against a scratch copy, with the failing and passing output pasted
- [ ] `dev-backend-guard.py` still fails closed; this todo does not relax it

## Notes

- Sibling context: `done/501-six-live-guards-have-no-test-suite.md` is the parent, and its new suites
  now pin the `strip_quotes` alias import in both `test_package_manager_guard.py` and
  `test_flutter_workdir_guard.py`, so a dead-code sweep fails loudly there. That covers the
  silent-disarm half. This todo covers the locked-out-session half, which those tests cannot reach
  because the lockout happens before the test runner starts.
- `status-marker-guard.py` and `schedulewakeup-guard.py` do NOT import `_hooklib` at all; confirmed by
  reading both in full on 2026-08-31.
