<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=9, reconfirm-count=1, content-hash=071fe8ff -->
<!-- duplicate-checked -->
<!-- Searched backlog + done/ for "fvm", "flutter", "bash path", "pipe". 780 is the closest and is
     deliberately NOT folded into: it targets `cargo test` HANGING on a pipe (child inherits the
     write end, never EOF). This is `fvm` MISSING from Bash's PATH and the pipe masking exit 127 as
     0. Different mechanism, different failure, overlapping fix surface. Cross-referenced both ways. -->
# PreToolUse guard: reject `fvm`/`flutter`/`dart` invoked through the Bash tool

**Type:** skill-improvement
**Origin:** ai

## Goal

Block a Bash-tool command whose first word resolves to `fvm`, `flutter`, or `dart`, with a message
naming the fix (re-run through the PowerShell tool). Optionally also flag piping such a command
into `tail`/`head`/`grep`, which is what upgrades this from a skipped check to a false green.

## Context

Second occurrence in zng-app, by two different sessions, in a project that already carries a
detailed memory of it (`reference_bash_tool_fvm_missing_exits_zero`). A memory alone has now failed
to prevent it twice, which is the same argument todo 780 makes for its own guard.

- **2026-08-25:** `fvm flutter analyze` through the Bash tool printed
  `bash: fvm: command not found` and **exited 0**. The verification floor in CLAUDE.md read as
  satisfied while nothing had been analyzed.
- **2026-08-26 (this session), and it escalated:** the command was chained,
  `fvm flutter build web ... | tail -5 && cd e2e && node run-all.js --target=local borrower`.
  The pipe makes the exit status `tail`'s, so `&&` proceeded past a build that never ran. The e2e
  suite then executed against a **stale `build/web` left by an earlier session** and reported
  `PASS 1/1`. That green was reported to Joe before the staleness was caught.

The escalation is the point: occurrence one skipped a check, occurrence two **manufactured a
passing end-to-end verification of code that was never compiled**. `build/web` persists across
sessions and is indistinguishable by eye from a fresh one, so nothing downstream can catch it.

Global CLAUDE.md's Shell Commands section already says to default to PowerShell for Joe's fvm
tooling. This is the enforcement half, absent today.

`hooks/flutter-workdir-guard.py` is the natural home: it already matches `Bash|PowerShell` and
already parses Flutter/Dart invocations to pin the working directory, so the command detection it
needs mostly exists. Adding a tool-name check there beats a new hook file.

## Approach

In `hooks/flutter-workdir-guard.py`, read the payload's `tool_name`. When it is `Bash` and the
parsed command's leading executable is `fvm`, `flutter`, or `dart`, `deny` with a message naming
the PowerShell tool as the fix and citing the false-green failure mode.

Confirm the deny direction is right before building: unlike `sensitive-file-guard.py`'s deliberate
all-`ask` stance (done/420 measured legitimate writes a hard block would have eaten), there is no
legitimate reason to run `fvm` through Bash on this machine, since the binary is not on that PATH
at all. Verify that claim still holds at build time rather than assuming it.

Second, smaller piece, and check it against todo 780 first so the two guards do not each grow their
own half-overlapping pipe regex: flag `fvm|flutter|dart ... | (tail|head|grep)`. Consider whether
780's guard and this one should share one pipe-detection helper in `_hooklib.py`, the way
done/380 consolidated the duplicated marker constants.

## Acceptance

- `fvm flutter analyze` via the Bash tool is rejected with an actionable message.
- The same command via the PowerShell tool passes untouched.
- A Bash command merely *mentioning* the words (`grep flutter README.md`, `echo "run fvm"`) is not
  rejected. Cover this explicitly; a naive substring match trips on it.
- New `hooks/test_flutter_workdir_guard.py` cases for each of the above, and
  `python ci/run_all.py` green.

## Notes

- Related: todo 780 (pipe guard for `cargo test`), memory
  `reference_bash_tool_fvm_missing_exits_zero`, done/380 (guards duplicating constants).
- Worth considering as a follow-up, not in scope here: `e2e/lib/server.js` already asserts the
  served bundle's API host before a run (see the same memory, section 5). An equivalent freshness
  assertion, for example refusing to serve a `build/web` older than the newest `lib/**/*.dart`
  mtime, would have caught the 2026-08-26 stale-bundle pass independently of any hook.
- Done via /mega-todos batch 2, commit 4a907d1: flutter-workdir-guard.py now branches on tool_name and denies fvm/flutter/dart invoked through the Bash tool, citing the false-green failure mode. PowerShell passes through untouched. New hooks/test_flutter_workdir_guard.py covers all four required cases plus bare flutter and bare dart; ci/run_all.py now discovers 16 hook suites. The builder committed this then hit the session limit before reporting, so acceptance was verified from the tree by the orchestrator rather than from a builder report.
