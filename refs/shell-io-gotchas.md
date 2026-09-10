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
