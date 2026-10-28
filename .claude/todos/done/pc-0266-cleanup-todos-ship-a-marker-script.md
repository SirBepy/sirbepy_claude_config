<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=1, content-hash=d2ed4d18 -->
# /cleanup-todos: ship a marker-update script instead of hand-rolling one per run

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `~/.claude/skills/cleanup-todos/` a real script for Step 5's marker refresh, so each run stops re-implementing it and re-introducing the same bugs.

## Context

Step 5 specifies the marker rewrite in prose only: preserve `last-checked` for shallow rows, bump it for deep rows, apply the reconfirm-count increment/reset/hold rules, recompute `content-hash`. Every run therefore writes its own ad-hoc script over N files. Two concrete failures on the 2026-08-12 run in `claude_usage_in_taskbar` (88 todos):

1. **A file got corrupted.** The rewrite used `[regex]::Replace($text, $pattern, $evaluator, 1)` intending "replace the first match only". There is no such static overload; the 4th argument is `RegexOptions`, and `1` is `IgnoreCase`. So it replaced EVERY marker-shaped string in each file. Todo 405 quoted an example marker inside its prose and had that prose silently overwritten with the current run's values. `.claude/todos/` is not git-tracked, so there was no history to restore from.

2. **`reconfirm-count` reset to 1 on all 40 deep rows**, because that run derived `content-hash` differently from the previous run's derivation, so no hash matched and the "hash differs -> reset" branch fired for everything. The counter is meant to measure how many consecutive checks a todo has survived unchanged; it silently measures nothing whenever the hash algorithm drifts between runs.

Both failures come from the same root cause: the hash function and the rewrite are re-invented per run rather than fixed once.

## Approach

Add `~/.claude/skills/cleanup-todos/update-markers.ps1` taking a repo root, the deep-tier id list with their verdicts, and today's date. It owns:

- The content-hash derivation, pinned once so counts stay comparable across runs. Note in the script that changing it invalidates every stored count.
- Anchored replacement of the real marker only. Match the marker at its known position (top-of-file region, after the title or claim line), NOT a bare scan for the marker pattern anywhere in the file. A todo may legitimately quote a marker in its body.
- The reconfirm-count increment / reset / hold rules.
- Shallow rows leaving `last-checked`, `reconfirm-count` and `content-hash` untouched.
- BOM-less UTF8 writes via `[System.IO.File]::WriteAllText`, per the global shell-write rule.

Then point Step 5 at the script, keeping the prose as the spec the script implements.

## Acceptance

- A run with a todo that quotes a marker in its prose leaves that prose untouched.
- Re-running twice with no content change increments `reconfirm-count` rather than resetting it.
- Shallow-tier rows come out byte-identical except for `complexity=`.
- No BOM introduced on any rewritten file.

## Notes

- Dropped via /cleanup-todos 2026-08-12: already implemented. skills/cleanup-todos/update-markers.ps1 satisfies every acceptance criterion (anchored Get-HeaderMarker, index splice, BOM-less write, reconfirm-count increment/reset).
