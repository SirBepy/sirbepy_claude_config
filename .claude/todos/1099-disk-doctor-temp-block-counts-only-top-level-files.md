<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are done todos on scan scope (03, Program Files), subagent delegation (217), and a past cleanup resume (838); none covers the Temp block's non-recursive sizing -->
# disk-doctor's Temp scan block counts only top-level files, under-reporting Temp by ~35x

**Type:** skill-improvement
**Origin:** ai

## Goal

The Windows scan reports the real size of `LocalAppData\Temp`, so that a multi-GB Temp folder shows up as a candidate without someone thinking to size it by hand.

## Context

`skills/disk-doctor/windows.md`, the "Temp + Recycle Bin" block, sizes Temp with `Get-ChildItem $env:TEMP -File -Force | Measure-Object Length -Sum`. That counts only files directly in `$env:TEMP` and skips every subfolder. On 2026-10-05 it reported Temp=0.4GB, while `Get-DirGB "$env:LOCALAPPDATA\Temp"` (recursive robocopy) measured 14.54GB. Most of that sat in subfolders: a 6.04GB `cueline-e2e-target` Rust build, `flutter_tools.*` dirs, and browser profiles. The scan only found it because the orchestrator asked the subagent for the extra measurement. The 2026-10-05 SCAN LOG entry in windows.md records the same numbers.

## Approach

- Replace the TempGB expression in that block with `Get-DirGB $env:TEMP`, embedding the `Get-DirGB` helper the way every other block does, since functions don't persist between calls.
- Optionally also report the size of Temp items older than 2 days. That is the deletable portion the 2026-10-05 run actually cleared, using `Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-2) }` on the top-level items.
- Update the KNOWN-SAFE Temp line's delete command to the age-filtered form, so items in use by running apps are skipped by design rather than by `-ErrorAction SilentlyContinue`.

## Acceptance

- Run the edited block: its TempGB is within a rounding difference of `Get-DirGB "$env:LOCALAPPDATA\Temp"` run separately.
- The Recycle Bin half of the block still reports the same value as before.
