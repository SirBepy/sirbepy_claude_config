<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforce the "never write file content through the shell" rule with a hook, not text alone

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the recurring failure where Claude edits a tracked file's *content* via `Get-Content`/`Set-Content`
(or `Out-File`/`>`/`>>`) despite the global CLAUDE.md rule banning it, corrupting non-ASCII characters
(em dashes, middle dots) into mojibake or adding a BOM that breaks downstream parsers.

## Context

Global CLAUDE.md (`~/.claude-personal/CLAUDE.md`, "Shell Commands" section) already states this as a
hard ban, with two prior incidents on record: `gh secret set` (2026-07) and
`%APPDATA%\com.sirbepy.taskbar-widgets\settings.json` (2026-08-05). A third incident happened
2026-08-09 in `windows_taskbar_widgets`: a PowerShell `(Get-Content -Raw) -replace ... | Set-Content
-Encoding utf8` one-liner, used to bulk-replace an icon-class string in a mockup HTML file, silently
mangled every em dash (`â€”` â†’ `Ă˘â‚¬"`) and middle dot (`Â·` â†’ `Ă‚Â·`) in the file. Caught only because the
next screenshot-based verification step visually surfaced the mojibake text; required a full
Write-tool rewrite of the file to fix.

This is the third occurrence of the same failure mode despite the rule being explicit, both times
previously and this time, in CLAUDE.md - text-only enforcement is not sticking. Compare
`59-enforce-no-em-dash-rule-with-hook.md`, an analogous case where a different text-only style rule
(no em dashes) got a hook-enforcement todo for the same reason: the rule is easy to violate
mid-task without noticing, because nothing blocks the tool call itself.

## Approach

Add a `PreToolUse` hook (alongside the existing `~/.claude/hooks/gh-account-switch.sh` and the
commit-marker hook) that intercepts Bash/PowerShell tool calls and blocks (or at minimum warns
loudly on) command strings matching content-writing patterns against a file path, e.g.:
- PowerShell: `Set-Content`, `Out-File`, `Add-Content` (without `-WhatIf`), `>`/`>>` redirects into a
  path, `| Set-Content`, `ConvertTo-Json | Out-File`, etc.
- Bash: `>`/`>>` redirects, `tee`, `sed -i` writing back to a tracked file.

Exact matcher needs care - false positives are likely (e.g. `Set-Content` on a throwaway temp file
used only for tool plumbing, like this session's own `preview-body.json` staging file, is fine per
the rule's own carve-out). Consider scoping the block to paths inside a git-tracked working tree, or
requiring an explicit override flag/confirmation rather than a hard block, to avoid blocking
legitimate scratch-file writes the rule doesn't intend to cover.

## Acceptance

- A `Set-Content`/`Out-File`/shell-redirect call targeting a tracked source file is blocked or
  flagged before it runs, not caught after the fact by a downstream symptom (garbled text, BOM).
- Legitimate temp-file/plumbing writes (JSON bodies for curl, etc.) are not blocked.

## Notes

Filed globally per CLAUDE.md's own rule ("a finding about the global `~/.claude` tree... goes in
`~/.claude/todos/`, NEVER in a project's `.claude/todos/`") even though it surfaced while working in
`windows_taskbar_widgets` - this is a global tooling gap, not project-local.
- Shipped 2026-08-11, wired in commit f9055ac. hooks/shell-content-write-guard.py blocks Set-Content/Out-File/Add-Content, > and >> redirects, heredocs and tee-to-file, with quote masking so a > inside a string literal is not mistaken for a redirect. Allowlists .commit-marker and .pr-marker so /commit and /create-pr can still write their own guard markers. 8/8 on the false-positive table.
