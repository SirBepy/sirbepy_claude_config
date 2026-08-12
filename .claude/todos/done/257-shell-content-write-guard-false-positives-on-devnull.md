<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=9, reconfirm-count=2, content-hash=8fd7eb6f -->
# The shell-content-write-guard hook false-positives on 2>/dev/null

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the global shell-write guard from blocking stderr suppression, without weakening the thing it
actually exists to prevent.

## Context

Hit twice on 2026-08-11. The hook's real job is to stop file CONTENT being written through the
shell, which is load-bearing and must stay: PowerShell 5.1 prepends a UTF-8 BOM and that has caused
at least two real incidents (`gh secret set` in 2026-07, and the taskbar-widgets `settings.json` in
2026-08 that silently reverted to `Settings::default()`).

But it also fires on stderr suppression. The exact blocked command was:

`git add <paths> 2>/dev/null; git status --porcelain`

and the hook reported: "`>` redirect writes file content to `/dev/null;` through the shell. Use the
Write tool instead."

Two separate bugs are visible in that one message:

1. `2>` is a **file-descriptor** redirect, not a content write. No file content is produced by it.
2. The captured target is `/dev/null;` **including the trailing semicolon**, so the token split is
   not respecting shell separators either. That means the reported target is wrong even in cases
   where the guard is right to fire.

Neither is a reason to loosen the guard generally. Writing to the null device cannot produce a
corrupt file, which is precisely what the guard protects against.

## Approach

File: `C:\Users\tecno\.claude\hooks\shell-content-write-guard.py`.

1. Treat a leading file-descriptor number (`2>`, `1>`, `2>&1`) as not-a-content-write.
2. Exempt `/dev/null` and `$null` as redirect targets outright.
3. Strip shell separators (`;`, `&`, `|`) and surrounding quotes from the captured target token
   before both the decision and the error message, so the reported path is the real one.

## Acceptance

- `git add x 2>/dev/null` passes.
- `cmd 2>&1` passes.
- `echo hi > real-file.json` is still blocked, and the error message names `real-file.json` with no
  trailing separator.

## Notes

- **Reproduced live 2026-08-12** in a `/close` run on `~/.claude`. The blocked command was
  `grep -ln "function Write-Info" skills/**/*.ps1 scripts/*.ps1 2>/dev/null`, a read-only grep. The
  guard's message named the target as `/dev/null;` with the trailing semicolon, confirming both
  defects in one shot: the fd-redirect misclassification AND the separator not being stripped. Cost
  one wasted tool call and forced the check to be re-run a different way.
- completed 2026-08-12, NOT COMMITTED: the fix is live on disk in hooks/shell-content-write-guard.py, but the hooks/ directory is gitignored in this repo so it carries no version history. Verified with a 5-case stdin test - 2>/dev/null and the trailing-semicolon form now pass, echo > file and cat >> file still block.
