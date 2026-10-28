<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=2ba7493c -->
# The five guard hooks each re-implement the same scaffold

**Type:** task
**Origin:** ai

## Goal

Decide whether `~/.claude/hooks/` should have a shared `_hooklib.py`, and if so, move the
duplicated scaffold into it. Five hook scripts currently carry their own copy of the same handful
of helpers.

## Context

Found by `/code-check` on 2026-08-11, right after four new guards shipped in commit `f9055ac`.
Each was written by a separate agent from `commit-guard.py` as a template, so they converged on
near-identical code without sharing any of it.

Concrete duplicates:

- `deny()` - 5 copies: `shell-content-write-guard.py:37`, `package-manager-guard.py:41`,
  `flutter-workdir-guard.py:50`, `pr-guard.py:40`, `commit-guard.py:34`.
- Marker consumption - 2 near-identical copies: `pr-guard.py:76` and `commit-guard.py:66`. Same
  `FRESHNESS_SECONDS = 120`, same oldest-fresh-first glob-and-delete logic, differing only in the
  glob string.
- `tokenize()` - 2 copies: `package-manager-guard.py:52` and `flutter-workdir-guard.py:81`. Both
  agents independently hit and fixed the SAME bug, that `shlex.split(posix=True)` eats Windows
  backslashes so `C:\Users\...` becomes `C:Userstecno...`.
- `strip_quotes` / `_strip_quotes` - 2 copies: `package-manager-guard.py:46`,
  `flutter-workdir-guard.py:59`.
- BOM-safe stdin read - 5 copies, all added by hand on 2026-08-11.

The strongest evidence is that last one. Every hook read stdin with a plain `json.loads`, so a
BOM'd payload raised, the outer handler caught it, and the hook exited 0. **A guard that fails
open silently stops guarding while still looking installed.** That single bug existed in all five
files and had to be fixed five times in a row.

## Approach

This is a genuine tradeoff, not an obvious win, so decide before writing code.

**For extraction:** roughly 100 duplicated lines, and today's BOM bug proves a fix has to be
applied N times instead of once.

**Against extraction:** hooks are standalone scripts the harness invokes by absolute path. A
shared import adds a failure mode where one missing or renamed file breaks every hook at once,
and because they all fail open, the failure is silent. That is exactly the reasoning that got
todo `61` (duplicated `Write-Info`/`Write-Fail`) dropped as not worth fixing.

The difference in scale is the argument for treating this one differently: `61` was two trivial
lines, this is a whole scaffold including logic that has already been fixed wrong twice.

If extracting, at minimum make the shared module's absence loud rather than silent, so a broken
import cannot degrade into "all guards quietly off".

## Acceptance

- Either `hooks/_hooklib.py` exists and the five hooks import the shared helpers from it, or a
  note in the hooks directory records the decision not to extract, with the reason.
- If extracted: every hook's existing test cases still produce the same allow/deny verdicts, and
  a deliberately broken import fails loudly instead of failing open.

## Notes

- completed 2026-08-12, NOT COMMITTED: the hooks/ directory is gitignored. Extracted hooks/_hooklib.py (BOM-safe fail-loud stdin parse, deny, strip_quotes, oldest_fresh_marker) and wired the five guards to it behind a loud import-failure guard. 13/13 test cases pass. Pre-edit backup at C:\tmp\hooks-backup-2026-08-12\. tokenize() was deliberately NOT unified (two hooks differ in real ways) and schedulewakeup-guard.py was left out of scope.
