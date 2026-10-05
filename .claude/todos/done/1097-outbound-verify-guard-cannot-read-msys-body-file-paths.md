<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=8, reconfirm-count=1, content-hash=8b9243bb -->
<!-- duplicate-checked: 1088 only moves functions between files and doesn't touch path handling; the other hits share vocabulary only -->
# outbound-verify-guard cannot read MSYS-style `/c/...` body-file paths from Bash

**Type:** task
**Origin:** ai

## Goal

A Bash `curl -d @/c/tmp/x.json` to Shortcut, whose text already passed the 3-verifier check, posts
instead of being blocked because the guard can't open the body file.

## Context

2026-10-05, zng-app session (sc-55538 comment). The body file was written by the Write tool to
`C:\tmp\sc55538-comment.json`, and the Bash command referenced it as `-d @/c/tmp/sc55538-comment.json`.
That path is valid for Git Bash's curl, but the guard blocked the call with: "cannot read the body
file /c/tmp/sc55538-comment.json, so the 3-verifier check cannot see what is being posted".
Re-running with `-d @c:/tmp/sc55538-comment.json` passed and posted (comment 56233).

Cause, from source: `hooks/outbound-verify-guard.py` `read_file` (around line 171) builds
`Path(os.path.expanduser(path))` and reads it with native Windows Python, which treats `/c/tmp/...`
as `C:\c\tmp\...`. There is no MSYS drive-prefix translation. The failure mode is fail-closed, so
it costs a retry, not safety.

The same root cause hits other native tools: see the zng-app memory
`reference_python_windows_tmp_paths.md` (Python, PowerShell, Read and curl.exe can't read
Bash-written `/tmp/` or `/c/` paths).

## Approach

In `read_file`, when the hook is handling a Bash command on Windows (`os.name == "nt"`), rewrite a
leading `/<letter>/` to `<letter>:/` before building the Path. Leave a bare `/tmp/...` alone: it
maps to the MSYS tmp dir and can't be resolved reliably without `cygpath`. Keep the existing
Unverifiable error for that case. Check whether `hooks/_hooklib.py` already has a path-normalising
helper (other guards hit the same thing, e.g. done todos 812 and 884 on POSIX-style absolute paths)
and reuse it if so.

## Acceptance

- A Bash `curl -X POST ... -d @/c/tmp/<file>.json https://api.app.shortcut.com/...` whose text is
  verified is allowed. The same command with an unverified text is still blocked.
- Add a hook test with an `@/c/...` body file.
- `@c:/...`, `@C:\...` and relative paths keep working.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): read_file maps a leading /<drive>/ to <DRIVE>:/ on Windows; bare /tmp stays Unverifiable per the todo; regression test check_body_file_msys RED then GREEN.
