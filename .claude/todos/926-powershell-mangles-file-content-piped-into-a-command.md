<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog and done/ for "PowerShell", "BOM", "Set-Content" and "secret". The existing rule covers writing file content OUT through the shell; this is the inbound direction (file content INTO a native command) and is not covered by it. -->
# Extend the Shell Commands rule to cover file content going INTO a native command

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the global rule cover the inbound direction too, so a PEM, cert, or key file piped into a CLI
from PowerShell does not silently arrive corrupted.

## Context

Found 2026-09-04 in the hubbub repo, diagnosing a GitHub Actions failure that had already cost one
wasted deploy run and a day of "there is no working deploy path".

`HUBBUB_APP_PRIVATE_KEY` on `SirBepy/hubbub` had been set from a `.pem` at some point via a shell.
The stored value was not a parseable PEM, and `actions/create-github-app-token@v1` died with:

```
DOMException [DataError]: Invalid keyData
  [cause]: Error: error:0680009B:asn1 encoding routines::too long
```

`asn1 too long` on an RSA import is what a value whose real newlines were flattened, or that got
re-encoded on the way in, produces. Re-setting it by piping the raw file through **Git Bash** fixed
it on the first attempt: deploy run `33877743559`, green in 41s.

Two concrete PowerShell 5.1 properties make the inbound direction unsafe, and neither is obvious:

- **There is no `<` input redirection.** `<` is a reserved token and the line is a parse error, so
  the natural `cmd --flag < file.pem` form simply cannot be written.
- **A native command's stdin via `Get-Content ... | exe` goes through PowerShell's own encoding
  layer**, which is where the reflow happens. It is the same mechanism the existing rule already
  bans in the outbound direction, just pointed the other way.

`CLAUDE.md`'s **Shell Commands** section currently says:

> Never write file CONTENT through the shell - not `Set-Content`, not `Out-File`, not `>`/`>>`.

That is outbound only. Nothing in it tells a session that `Get-Content key.pem | gh secret set ...`
is the same hazard, and the failure is far worse here: an outbound BOM usually breaks the very next
parse loudly, while a mangled secret sits there looking fine until CI fails on a machine you are
not looking at.

## Approach

1. Add one bullet to `CLAUDE.md`'s Shell Commands section, in the same voice as the existing ban:
   file content going INTO a native command (`gh secret set`, `openssl`, `kubectl create secret`,
   `wrangler secret put`, `docker login --password-stdin`) uses the **Bash** tool with `<`
   redirection, never PowerShell. PowerShell 5.1 has no `<` and re-encodes a native-command pipe.
2. Name the verification, since it is cheap and catches the failure before it ships: check the file
   is what you think before handing it over - no BOM (`head -c 3 | od`), no `\r`, no literal
   backslash-n, and for a key, that it actually parses (`node -e "crypto.createPrivateKey(...)"`
   or `openssl rsa -check -noout`).
3. Consider whether `hooks/` should guard it mechanically, the way the package-manager and
   commit guards do. A PreToolUse hook matching a PowerShell command containing both `Get-Content`
   and a pipe into a known secret-setting CLI would catch the exact shape. Decide this deliberately
   - it may be too narrow a pattern to be worth a hook.

## Acceptance

- `CLAUDE.md`'s Shell Commands section names the inbound direction explicitly.
- The always-loaded instruction token budget still passes `python ci/run_all.py` (the addition is
  ~3 lines, so this should be a non-event, but the budget check is what proves it).

## Notes

- Keep this in the Shell Commands section rather than starting a "secrets" section. It is the same
  mechanism and the same ban; splitting it across two sections is how one half gets read and the
  other does not.
- The Bash tool is available in this harness alongside PowerShell, so the fix costs nothing - it is
  a tool choice, not a workaround.
