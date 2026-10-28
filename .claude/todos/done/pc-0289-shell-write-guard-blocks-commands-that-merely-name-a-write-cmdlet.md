<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# shell-content-write-guard blocks any command that merely NAMES a write cmdlet

**Type:** task
**Origin:** ai

## Goal

Make `hooks/shell-content-write-guard.py` distinguish invoking a content-write cmdlet from merely
mentioning its name, so searching for the string `Set-Content` stops being blocked as if it were a
write.

## Context

Reproduced live during `/close` on 2026-08-12. This Bash call was rejected:

    grep -nE 'Set-Content|Out-File|...' skills/android-drive/adb-drive.ps1

with:

    [shell-content-write-guard] PowerShell content-write cmdlet `Set-Content` writes file content
    through the shell. Use the Write tool instead, or [System.IO.File]::WriteAllText(...)

The command writes nothing. `Set-Content` appears only inside a single-quoted grep PATTERN. The
guard scans the raw command string for the cmdlet name with no regard for whether it sits in
command position, so any audit, grep, or documentation-checking command that names the cmdlets it is
looking for gets blocked. The irony is direct: the command was auditing a script for banned write
patterns, which is exactly the rule the guard enforces.

This is the same defect class as todo 257 (`done/257-shell-content-write-guard-false-positives-on-devnull.md`,
fixed earlier the same day), which was a redirect target that captured a trailing `;`. Both are the
guard being too literal about string matching. 257 fixed one instance; this is the general shape,
so the fix should consider whether more instances are lurking rather than patching this one case.

Severity is friction, not danger: the guard fails CLOSED, so nothing unsafe gets through. But it
costs a retry every time it fires, and the workaround (reach for the Grep tool instead) is not
obvious mid-task.

## Approach

Only treat a cmdlet as invoked when it appears in command position: at the start of the command, or
immediately after a `|`, `;`, `&&`, `(`, or a newline. At minimum, skip any occurrence inside a
single- or double-quoted string, which alone would have prevented this case.

The guard already has a `tokenize()` / `strip_quotes` scaffold (now shared via `hooks/_hooklib.py`
after todo 250), so quote-awareness is likely reachable without a rewrite. Check whether
`package-manager-guard.py` and `pr-guard.py` have the same mention-versus-invocation weakness while
in there, they use the same scaffold.

Do NOT weaken the guard: a real `Set-Content -Path x -Value y`, `Out-File`, and a `>` redirect to a
non-null target must all still block.

## Acceptance

- `grep -nE 'Set-Content|Out-File' <file>` PASSES.
- `echo hi | Set-Content notes.txt` and a bare `Set-Content -Path x -Value y` still BLOCK.
- `foo > notes.txt` still blocks, `foo > /dev/null` still passes (todo 257's cases do not regress).
- A test run covering all of the above, with output pasted into the commit or the todo's Notes.

## Notes

- `hooks/` is gitignored in this repo, so any change here has no version history. There is a
  pre-edit backup of the whole directory at `C:\tmp\hooks-backup-2026-08-12\` from the 2026-08-12
  autopilot run; make a fresh one before editing.
- Found by `/code-check` during `/close`, not reported by the dev.
- Done 2026-08-13. Root cause: find_violation() searched the RAW command before mask_quoted() stripped quoted strings, so a cmdlet name inside a grep pattern still matched. Fix runs the search against the masked command and adds is_command_position(), which only counts a match at the start of a command or right after a pipe, semicolon, ampersand, paren, brace or newline. Kept fail-CLOSED. Persisted 13-case test file at hooks/test_shell_content_write_guard.py, all passing, covering both live repros from the todo plus the todo 257 redirect regressions. Checked package-manager-guard.py and pr-guard.py too: both already shlex.split first, no fix needed.
