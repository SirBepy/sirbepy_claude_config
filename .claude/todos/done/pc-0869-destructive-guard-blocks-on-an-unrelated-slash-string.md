<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The destructive guard blocks a Remove-Item when an unrelated slash-string sits elsewhere in the same command

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/destructive-command-guard.py` refusing a legitimate `Remove-Item` because some other,
unrelated part of the same command string happens to start with a slash.

## Context

Reproduced 2026-09-01 in the `/mega-todos` orchestrator's own session, minutes after todo 462
refactored this guard onto the shared hooklib `ask` helper (commit `c00dd70`). The refactor is
behaviour-preserving and its own suite passed, so this is a pre-existing false positive that 462
carried forward, not a regression 462 introduced. Verify that framing before blaming `c00dd70`.

The blocked command was one PowerShell call that did two things: iterate a hashtable of todo
archival notes, and then delete two claim files. The note strings contained the literal text
`/mega-todos` (a slash command name, in prose). The guard rejected the whole call with:

    Remove-Item on system path '/mega-todos' is blocked. This path is protected from removal.

Nothing in the command asked to remove `/mega-todos`. The actual `Remove-Item` targets were two
absolute `.claim` paths under `C:\Users\tecno\.claude\.claude\todos\.claims\`. The guard appears to
scan the command string for slash-prefixed tokens rather than parsing the arguments actually bound
to `-Path`/`-LiteralPath`, so any prose in the same call can be mistaken for a target.

Workaround used at the time: split the command in two so the deletion ran in a call containing no
prose. That is a workaround, not a fix, and it only worked because the operator noticed why.

This is the failure shape the repo's own hook doctrine warns about, and it argues the same thing
three killed heuristic hooks did: measure against the real command corpus, then hand-probe.

## Approach

1. Read `hooks/destructive-command-guard.py` and find where it extracts candidate paths from the
   command string. Confirm by probe, not by reading, that a slash-prefixed token anywhere in the
   string is enough to trip it.
2. Bind the check to arguments actually passed as a removal target: for PowerShell, the values of
   `-Path` / `-LiteralPath` and the positional first argument; for `rm`, the non-flag operands.
   A token inside a quoted string that is not one of those is not a target.
3. Measure the change against the transcript corpus at `C:\tmp\p2-corpus\commands.jsonl` before
   wiring it, then hand-probe the built thing. The corpus proves only that no PAST command tripped
   it, so both steps are required and neither substitutes for the other.
4. Keep every genuine block. This narrows a destructive-operation guard, so the bar is the same as
   for a security guard: prove the real cases still fail.

## Acceptance

- The exact reproduction above (a `Remove-Item` of two absolute `.claim` paths, in a command whose
  other arguments contain the literal string `/mega-todos`) is allowed, pinned as a test case.
- Every existing case in `hooks/test_destructive_command_guard.py` still passes, unmodified.
- A real system-path removal (`Remove-Item /`, `Remove-Item C:\Windows`, `rm -rf /`) is still
  blocked, pinned as test cases.
- `python ci/run_all.py` exits 0.

## Notes

- Completed in /mega-todos wave 1, commit ca2178f: match_remove_item now binds path extraction to real -Path/-LiteralPath/positional arguments instead of scanning the command string for any slash-prefixed token. The original false-positive repro is a regression case.
