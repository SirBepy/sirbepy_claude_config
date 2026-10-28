<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1160 (orphan sweep) and 1163 (server-backed e2e) are other testing-floor defects; neither covers out-of-repo scratch files or the exit-0 false fail -->
# testing-floor-guard blocks a turn over a scratch .js outside any repo, then false-fails a green suite

**Type:** hook-bug
**Origin:** ai
**Summary:** A scratch file outside any repo no longer triggers the testing check, and a passing Flutter suite is no longer reported as failed.

## Why

On 2026-10-13, in two sessions, the only edits were scratch files outside any git repo, yet the turn was blocked with "flutter check failed (exit 0)" on a suite that passes.

## Goal

Stop `testing-floor-guard.py` from gating a turn whose only "source" edit was a throwaway file outside every repo, and stop it reporting `flutter check failed (exit 0)` on a suite that passes.

## Context

2026-10-13, zng-admin session fb06a166 (sc-55910 planning). The only Write this session made was `C:\tmp\sc_read.js`, a read-only Shortcut dump helper (needed because `outbound-verify-guard.py` blocked a GET whose token came from a variable). `testing-floor-flag.py` still marked the session dirty and recorded `root: C:\Users\tecno\Desktop\Projects\zng-admin-followup`, apparently the shell cwd at the time, not the edited file's repo (it has none).

The Stop hook then blocked with `[testing-floor-guard] Fast checks still failing (attempt 1/3): flutter check failed (exit 0): ...`. Running `fvm flutter test` by hand in that same root through PowerShell ended `00:02 +93: All tests passed!`. `fvm flutter analyze` in zng-admin and zng-app both printed `No issues found!`.

So there are two defects:
1. A path outside every git repo should not activate the gate, and it certainly shouldn't take its root from cwd.
2. The flutter row reports a failure on exit 0 even though the suite passes. The likely causes are the verdict-line parse (`_testing_floor_lib.py` around 463-517) or fvm not resolving on the hook's PATH. This is UNVERIFIED: the summary was truncated to `...`.

**Second occurrence, same day (revaire-mobile session 0f834423).** The only "source" edits were two
`.mjs` files in `C:\Users\tecno\Documents\revaire-scoped-install\`, which is outside any git repo. The
flag recorded `root: revaire-mobile`, and the guard blocked with the identical
`flutter check failed (exit 0): ...`. Both defects reproduced, in a second project.

## Approach

1. In `testing-floor-flag.py`, skip paths whose `git rev-parse --show-toplevel` fails, and derive `root` from the edited file, not cwd.
2. Reproduce the flutter row from Python against zng-admin-followup and print the full captured output, then fix the parse or the PATH issue.
3. Add a regression case to `test_testing_floor_flag.py` / `test_testing_floor_guard.py` for each.

## Acceptance

- Writing a file under `C:\tmp` never sets the session flag.
- The flutter row passes on a repo where `fvm flutter test` prints `All tests passed!`.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
