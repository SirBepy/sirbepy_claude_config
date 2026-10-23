# Shell I/O gotchas beyond the outbound write ban

CLAUDE.md's Shell Commands section already bans writing file CONTENT through PowerShell
(`Set-Content`/`Out-File`/`>`/`>>`) because of the BOM Windows PowerShell 5.1 prepends even with
`-Encoding utf8`. This file covers the inbound mirror of that bug.

## Piping file content INTO a native command

`Get-Content file | exe` (PowerShell has no real `<` redirection) routes the file through the same
PowerShell text-encoding layer as the outbound write path. A prepended BOM or altered line endings
can corrupt a key, cert, or secret silently instead of the command failing loudly.

Confirmed failure: `gh secret set` (2026-07, see `refs/incidents.md`) rejected a value piped
through PowerShell outright.

Also affected: `openssl`, `docker login --password-stdin`, and any other native exe that reads a
credential or cert from stdin.

## Fix

Use the Bash tool with real `<` redirection instead of a PowerShell pipe, and verify the file
parses (e.g. `openssl x509 -in file -noout` for a cert) before handing it to the command that
consumes it.

## .NET file APIs ignore `Set-Location`

`[System.IO.File]::ReadAllText/WriteAllText` resolve a relative path against the PROCESS current
directory, which `Set-Location` does not change (it moves only PowerShell's own location). The
PowerShell tool's process cwd stays wherever the session started.

Confirmed failure, 2026-10-09, mc_plugins_tag session f348: a mutation test meant for a scratch
worktree ran `Set-Location C:\cargo-target\mc-f348` then `WriteAllText` on a relative path. Process
cwd was still the main checkout (shared with 4 live peer sessions), so the read and write hit the
MAIN checkout's file. It surfaced only because the "mutated" tests all still passed; rerun with
absolute paths, the mutations bit (3 tests failed as expected).

Rule: pass absolute paths to .NET file APIs, or call `[System.IO.Directory]::SetCurrentDirectory(<dir>)`
first. The same trap is in `skills/commit/SKILL.md` step 6 (worktree removal).

## `Remove-Item` denied as "system path ... is blocked"

That denial is a Claude Code harness built-in (the string lives in `claude.exe`; no hook here emits
it), so it can only be documented, not fixed. It reads targets from the WHOLE command, so keep a
`Remove-Item` in its own PowerShell call, never in the same call as text carrying a slash-word
(four hits, each lost the writes in that call).

## A separate PowerShell footgun: `-replace` does not escape the replacement string

Found 2026-09-10 while building `build-dispatch.ps1`'s `-AsJsLiteral` mode, which needs to double
every backslash so its output survives inside a JS template literal.

`-replace` is .NET `Regex.Replace`. Its PATTERN side is a regex, so a backslash there has to be
escaped as usual. Its REPLACEMENT side is not: it has `$` substitution semantics and nothing else,
so backslashes in it are taken literally. Writing what looks like a symmetrical escape on both
sides therefore emits twice as many backslashes as intended. Nothing errors. The corruption is
silent and only surfaces when whatever consumes the string tries to parse it.

Use the plain string method `.Replace()` when the intent is a literal substitution, and reserve
`-replace` for when the pattern genuinely needs a regex.

The same class of trap bites a Python heredoc writing this file: `\b` inside a normal (non-raw)
triple-quoted string is a BACKSPACE byte, not two characters, and it lands in the file where no
later Edit can match it. Write literal-backslash content with the Write or Edit tool, or with a raw
string, never through a normal heredoc string.
