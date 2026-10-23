<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 03, 04, 1100 are done/ todos on scan scope, delete verification and card contents; none cover a pre-decision chart, in-use area offers, or the C:\tmp guard block -->
# disk-doctor: show a breakdown chart before delete cards, and check in-use/guard limits earlier

**Type:** skill-improvement
**Origin:** ai

## Goal

`/disk-doctor` on Windows lets Joe see where the space goes BEFORE any delete card appears, and stops
offering or planning things that the session later has to retract (an in-use model store, a path the
removal guard will not touch).

## Context

2026-10-21 deep scan session (C: 183.5 to 281.3 GB). Three gaps showed up:

1. **No chart step.** After the scan Claude sent a text summary and a coarse "which areas" card. Joe
   answered "I wanna kinda see a graph of where all of my storage is going before i decide anything".
   Claude then built an HTML bar chart (grouped by regenerable / re-downloadable / personal / system,
   hover tooltips, table toggle) via `show_preview` and Joe decided from that. `windows.md` and
   `gate.md` define scans, output rules and the delete gate but say nothing about a visual breakdown.
2. **Ollama was listed as a delete area while in use.** The first summary named "Models: Ollama +
   HuggingFace + whisper" as a candidate group. Joe asked "are you sure im not using the ollama
   models?". Checking showed `ollama.exe` running (started that day), `mistral-small3.2:24b` loaded, 11
   of 13 manifests written overnight (a bake-off), and sirbepy_assistant scripts calling `qwen3.5:9b` and
   `qwen3:8b` (`scripts/detector-logic.mjs:134`, `scripts/health-check.js:97`). `gate.md` already
   requires a process check for "model-weights/library dirs", but only "before asking about" a delete
   card, so the area-level offer slipped past it. Blob size also grew 78 to 112 GB while the session ran,
   so a one-time scan number was stale.
3. **`C:\tmp` cannot be cleaned by Claude.** `Remove-Item` on `C:\tmp` children was refused by the
   removal guard in all three forms tried (`Get-ChildItem | Remove-Item`, `-LiteralPath` in a loop).
   `refs/builder-preamble.md` already says the drive-root child cannot be reclaimed by Claude, but
   `windows.md` KNOWN SAFE still lists `C:\tmp\pw-*` and `C:\tmp\*-target` as deletable, and the delete
   card for the age-based sweep was approved before the block was discovered.

## Approach

In `skills/disk-doctor/windows.md` (and `macos.md` if it shares the flow):

- Add a "Breakdown chart" step after the scans and before any delete card: group the findings into
  regenerable / re-downloadable / personal / system plus an unattributed remainder, render with the
  `dataviz` skill via `show_preview` (single-hue-per-kind bars, tooltips, a table toggle), and ask which
  groups to turn into cards. The 2026-10-21 chart is the worked example (slug `c-drive-storage-map`).
- Move the in-use process check from "before asking about a model/venv dir" to "before listing the
  area at all": run `Get-Process` for the owning app (ollama, python, java) and `ollama ps` style
  probes during the scan itself, and mark such groups "in use" in the chart instead of offering them.
- In KNOWN SAFE, annotate the `C:\tmp` entries: Claude cannot delete them (guard blocks it), so the
  card should hand Joe the PowerShell command to run himself instead of offering Claude to run it.

## Acceptance

- A fresh `/disk-doctor` run shows the chart before the first delete card.
- A running Ollama (or similar) store is labelled in-use and not offered for deletion.
- No card offers Claude to run a `Remove-Item` on `C:\tmp`.
- `python ci/run_all.py` still passes (frontmatter and token budget unaffected).

## Notes

- Related, already done: 1099 (Temp sizing), 1100 (cards must name origin and last use).
- Removal-guard false positive seen the same session: `Remove-Item` plus a later `/1GB,2` in one command
  was blocked as "system path '/1GB,2'". Looks like todo 1170's shape, so not filed separately.
- Completed 2026-10-23 (loop-todos cycle 1): scan-time in-use probe labels groups 'in use' (windows.md, macos.md), a Breakdown chart step runs before any delete card, and the C:\tmp drive-root KNOWN SAFE entries say Claude cannot delete them and hand Joe the command. gate.md left to its owning session.
