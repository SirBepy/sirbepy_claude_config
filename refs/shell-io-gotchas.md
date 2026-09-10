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
