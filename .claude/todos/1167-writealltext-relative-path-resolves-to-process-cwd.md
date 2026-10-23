<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 277 is sv.ps1's -Root default, 812 is em-dash path args; neither covers .NET file APIs vs Set-Location -->
# Warn that [System.IO.File] with a relative path ignores Set-Location

**Type:** skill-improvement
**Origin:** ai

## Goal

Add one gotcha to `C:\Users\tecno\.claude\refs\shell-io-gotchas.md` (and a short clause next to the
`[System.IO.File]::WriteAllText($path, $text)` recommendation in global `CLAUDE.md`'s Shell Commands
section): pass an ABSOLUTE path to `[System.IO.File]::ReadAllText/WriteAllText`, because .NET
resolves a relative path against the process current directory, not PowerShell's `Set-Location`.

## Context

2026-10-09, mc_plugins_tag session f348. A mutation test meant for a scratch worktree ran
`Set-Location C:\cargo-target\mc-f348; $f='tweaks\src\...\TownyAdminOffListener.java';
[System.IO.File]::WriteAllText($f, ...)`. The PowerShell tool's process cwd was still the main
checkout (`C:\Users\tecno\Desktop\Projects\mc_plugins_tag`), so the read and the write hit the MAIN
checkout's file, a shared checkout with 4 live peer sessions. It was only noticed because the
"mutated" tests all still passed; the script's final write restored the original, so nothing was
lost. Rerunning with absolute paths made the mutations bite (3 tests failed as expected).

The same class of trap is already documented in `skills/commit/SKILL.md` step 6
(`[System.IO.Directory]::SetCurrentDirectory` vs `Set-Location` for worktree removal), but the
file-write recommendation in `CLAUDE.md` carries no such warning, and it is the one the
shell-content-write guard steers Claude toward.

## Approach

- `refs/shell-io-gotchas.md`: new short section, the incident above as evidence, rule "absolute
  paths only, or `[System.IO.Directory]::SetCurrentDirectory` first".
- `CLAUDE.md` Shell Commands bullet: append "(absolute path: .NET ignores Set-Location)" after the
  WriteAllText mention. Keep the always-loaded token budget in mind (`ci/run_all.py` checks it).
- Folded in from 1170 (archived 2026-10-23): the "Remove-Item on system path '...' is blocked"
  denial is a Claude Code harness built-in (the string lives in `claude.exe`, no hook emits it), so
  it can only be documented, not fixed here. Add one line to the same `refs/shell-io-gotchas.md`
  section: keep a `Remove-Item` in its own PowerShell call, never in the same call as text carrying
  a slash-word, since the built-in reads targets from the whole command (four hits, lost writes).

## Done when

Both edits landed and `python ci/run_all.py` passes.
