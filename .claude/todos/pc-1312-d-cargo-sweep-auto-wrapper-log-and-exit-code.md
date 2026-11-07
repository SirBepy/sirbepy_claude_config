<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new scripts from 2026-11-04, no existing todo covers d-cargo-sweep-auto.ps1 -->
# d-cargo-sweep-auto.ps1 logs a refused or aborted sweep as "done" and keeps a stale Tier C filter

**Type:** task
**Origin:** ai
**Summary:** Make the scheduled D: sweep's log line and Task Scheduler result tell the truth when the sweep was refused or aborted, and drop the leftover Tier C wording.

## Goal

`%LOCALAPPDATA%\d-cargo-sweep\log.txt` and the task's last result must show whether a run swept, was refused (exit 3), or was aborted mid-sweep (exit 4), and the wrapper's comments and filter must match its B and D only tiers.

## Context

Found by the `/close` code-check of commits b4cb674 and f9b3753 (fresh subagent, 2026-11-04).

- `skills/disk-doctor/d-cargo-sweep-auto.ps1:47-51` never reads `$LASTEXITCODE`. The child exits 3 (`d-cargo-sweep.ps1:83`, a build is running) or 4 (`:206`, a build started mid-sweep), yet the wrapper always logs `done: ... (+0 GB)` and exits 0.
- `d-cargo-sweep-auto.ps1:50` keeps only the first 12 lines matching `Tier [CD]:|removed|STILL PRESENT|REFUSING|ABORT`. The child prints one `removed <path>` line per tier B dir before the `Tier D:` summary and any ABORT line, so a run that removes 12 or more incremental dirs cuts the lines that say whether it worked.
- The `Tier C` alternative in that regex is dead since f9b3753 removed tier C from the wrapper.
- The comment at `d-cargo-sweep-auto.ps1:10-11` says B and D remove "superseded variants, which a new build never rewrites". That is true for D. Tier B removes incremental cache dirs, which a new build does recreate (rebuild cost only), so the sentence is wrong for B. CLAUDE.md Code Style: "A wrong comment is worse than none".
- Optional hardening, no failure observed (UNVERIFIED as a real risk): `& powershell` resolves through PATH while the task names `powershell.exe`; `$path.StartsWith($deps + '\')` at `d-cargo-sweep.ps1:232` is culture and case sensitive.

## Approach

1. After the child call, capture `$LASTEXITCODE`; log `refused` (3) or `aborted` (4) with the code, and exit with it or with 0 plus a distinct log prefix (Joe's call which; ask before choosing).
2. Replace the tail filter with an anchored one (`^(Tier D:|REFUSING|ABORT|STILL PRESENT)`) and log a count of `removed ` lines instead of listing them.
3. Reword the comment so B is "aged incremental cache, rebuild cost only" and D is "superseded variants".
4. Optionally use `$PSHOME\powershell.exe` and an ordinal-ignore-case `StartsWith`.

## Acceptance

- A forced refused run (start a `cargo` process, run the wrapper with `-ThresholdPct 100`) logs `refused` and does not log `done`.
- The wrapper's no-op path still logs `ok: ...` as before.
- No comment mentions Tier C in the wrapper except the one saying it stays manual.
