<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new guards from the 2026-11-03 /mega-todos run; pc-1297 covers the six sibling splitters, a different hook set -->
# Guard edge cases found by the mega-todos review: pipe guard, flutter guard, shell-write guard, testing-floor root

**Type:** skill-improvement
**Origin:** ai
**Summary:** An independent review of the guards changed on 2026-11-03 reproduced four lower-severity gaps: a quoted separator hides a piped commit-pathspec from the pipe guard, the flutter guard's new splitter ignores backslash and backtick escapes, a PowerShell-tool command starting with git or bash skips the shell-write pwsh pass, and the node orphan sweep could match nearly any command line if its saved root is ".".

## Goal
Each of the four gaps is fixed with a test that fails without the fix, or declined with a stated reason.

## Context
Reviewer findings, all reproduced by running the hooks except the last (reviewer was a sonnet agent; re-run before acting):
- `hooks/cargo-test-pipe-guard.py` `find_commit_pathspec_violation` (about line 218) splits on `;`, `&&` and newline BEFORE building the quote mask, so `bash .../commit-pathspec.sh -m "FIX: a; b" f.txt 2>&1 | tail -6` returns no violation; also missed: `|&`, `(bash ...) | tail`, `{ ...; } | tail`, and piping into tee, cat or sed (not in PIPE_FILTERS).
- `hooks/flutter-workdir-guard.py` (about line 154): the new quote scanner has no backslash or backtick escape handling, so `echo "a\" b"; fvm flutter build` desyncs the mask and the later command is only warned about; `bash -c "cd x; dart run build_runner build ..."` is now allowed where it was denied.
- `hooks/shell-content-write-guard.py` (about line 277): the hook matches Bash and PowerShell but ignores tool_name, so a PowerShell-tool command that starts with git, bash or sh skips the pwsh pass: `git commit -m "a \" ; Set-Content f x ; echo \""` passes. Contrived, low severity.
- `hooks/_testing_floor_lib.py` `sweep_node_orphans`: ownership uses the check root as a substring; UNVERIFIED whether the root can fall back to ".", which would match almost any command line and could kill a peer's new vitest.

## Approach
One guard per commit with a red-first test. For the splitter issues prefer fixing `split_command_segments` in `hooks/_hooklib.py` once (escape handling) if it is shared, then re-run every guard suite.

## Acceptance
- [ ] Each of the four gaps has a failing-first test or a documented decline.
- [ ] `python ci/run_all.py` passes apart from the impeccable description.
