<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep for MSYS/PATHCONV hit only pc-1213 (ticket marker timing), a different surface -->
# split-hunks.py: `--hunk path:substring` gets mangled by Git Bash path conversion

**Type:** skill-improvement
**Origin:** ai
**Summary:** Run from the Bash tool on Windows, `split-hunks.py commit --hunk "e2e/x.spec.ts:...invoke,"` fails with `--hunk expects path:substring, got 'e2e\\x.spec.ts;...invoke,'`, because MSYS treats the `:`-joined arg as a POSIX path list and rewrites it.

## Goal
`split-hunks.py commit --hunk <path>:<substring>` works as documented from the Bash tool on Windows without the caller knowing about MSYS argument conversion.

## Context
Hit 2026-10-29 in claude_usage_in_taskbar while splitting a peer's hunk out of a shared spec file. Setting `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"` fixed the args, but then the `~/.claude/skills/commit/split-hunks.py` script path itself stopped converting (`C:\c\Users\...` not found), so the caller also has to pass the script as `C:/Users/tecno/.claude/skills/commit/split-hunks.py`. Two failed calls before it worked. Usage docs: `skills/commit/edge-cases.md` "Splitting one file across commits", and the script's own docstring.

## Approach
Pick one: (a) document the working invocation in `edge-cases.md` (both env vars plus a Windows-form script path), or (b) make the script accept a separator that MSYS leaves alone (e.g. `--hunk-path <p> --match <s>` pairs, or `path::substring`), keeping `path:substring` for PowerShell callers.

## Acceptance
From the Bash tool on Windows, the documented `split-hunks.py commit ... --hunk <path>:<substring>` invocation commits the selected hunk on the first try.

## Notes

- Fixed in 621e40a (documented plus a diagnostic hint in split-hunks.py).
