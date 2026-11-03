<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 0044/0217/0236/0266/0290 share only generic words (ship, script, disk-doctor, instead); none covers the C:\tmp age sweep -->
# disk-doctor: ship a fast script for the C:\tmp age sweep instead of a slow one-liner

**Type:** skill-improvement
**Origin:** ai
**Summary:** Disk-doctor hands Joe a ready script for clearing old C:\tmp items that finishes in seconds, not half an hour.

## Goal

When disk-doctor offers the C:\tmp "older than N days" sweep (which Joe must run himself, because the harness blocks Claude from deleting drive-root children), it hands him a script in `skills/disk-doctor/` that finishes quickly and honours the keep-list, instead of an inline one-liner composed on the spot.

## Context

- 2026-10-30, session 2369b812: Claude gave Joe this one-liner in a chat message:
  `Get-ChildItem C:\tmp -Force | Where-Object { <keep-list filters> -and -not (Get-ChildItem $_.FullName -Recurse -File -Force ... | Where-Object LastWriteTime -gt (Get-Date).AddDays(-21) | Select-Object -First 1) } | Remove-Item -Recurse -Force`
- C:\tmp had about 1,820 top-level items, several full of pnpm `node_modules`. The per-item recursive walk ran past 30 minutes of CPU in Joe's admin terminal: process 36008 was at 1,911 s of CPU, with items dropping about 1 per 20 s. Joe asked "could it be that this is still running? im pressing enter and nothing is happening".
- The keep-list that must survive any sweep is in `skills/disk-doctor/windows.md` NEVER-TOUCH: `cc-target` while it's under 21 days old, `salvage`, `memory-backup-*`, loose `*.java`/`*.java.bak`, `sftp-*`, `live-*.yml`, plus `n8n-db.sqlite` that run.
- The block is the Claude Code harness's built-in system-path refusal, not a repo hook, so Claude cannot run the delete itself (pc-1257, `refs/incidents.md:104`).

## Approach

1. Add `skills/disk-doctor/tmp-age-sweep.ps1` with `-Days <n>`, `-Keep <names/globs>` and `-WhatIf`. Default to `-WhatIf`, so it lists items and GB first. `-Apply` deletes.
2. Compute each top-level item's newest-file mtime in ONE recursive pass: for example `Get-ChildItem C:\tmp -Recurse -File -Force`, grouped by the first path segment under C:\tmp, max LastWriteTime. Or use robocopy `/L /S /MAXAGE` / `/MINAGE` listing. Don't do a separate recursive walk per item. Skip reparse points so pnpm links aren't followed.
3. In windows.md's KNOWN-SAFE C:\tmp entry, tell Claude to hand Joe the script's absolute-path invocation, first with `-WhatIf`, then `-Apply`.
4. Add a unit test next to it (fake tree in a temp dir: old dir, new dir, old dir with one new nested file, keep-list items), following the repo's `skills/**/test_*.ps1` convention that `ci/run_all.py` picks up.

## Acceptance

- On a C:\tmp-sized tree (about 2k top-level items, node_modules-heavy), `-WhatIf` finishes in well under a minute.
- An item with any file newer than the cutoff is never listed. Keep-list items are never listed.
- `python ci/run_all.py` passes, with the new test included.

## Notes

- Fixed in 15a6985 (tmp-age-sweep.ps1 with preview default and test).
