<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=4, content-hash=3e2b2b3e -->
# Orphan-process forensics gets rewritten from scratch every time it is needed

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the Process Hygiene doctrine an executable audit instead of a prose instruction, so diagnosing
"what is eating my RAM / did we leak processes" is one call rather than four hand-written
PowerShell blocks.

## Context

Found by `/close` on 2026-08-07 in `claude_usage_in_taskbar`, during a session where Joe reported
Brave apparently holding 23 windows and suspected the app was leaking headless browsers.

Answering it took four separate, hand-authored PowerShell blocks, none reusable next time:

1. Group processes by name with summed working set, to rank the actual consumers.
2. Group WebView2 processes by parent and resolve each root's `--user-data-dir`, to prove the 39
   processes belonged to six different apps rather than one leaking one.
3. Walk each candidate's ancestry to a live `claude.exe`, marking `parent-dead` and
   `pid-recycled` (parent newer than child) separately - the PID-recycling case is the one a naive
   check gets wrong.
4. A rootless sweep over a name-filtered scope to find processes whose parent no longer exists.

`~/.claude/CLAUDE.md`'s Process Hygiene section mandates an orphan check after every test/build run
but supplies only a vitest-specific one-liner
(`Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }`).
That does not cover the general question, so the general question gets improvised each time.

The load-bearing detail worth encoding: **process count is not window count.** Brave showed 24
processes and exactly one window (`Get-Process brave | Where-Object MainWindowTitle -ne ''`), which
is what actually resolved Joe's report. A count-only view invites precisely the wrong conclusion.

## Approach

Add a `/orphan-audit` skill (or extend `~/.claude/refs/process-hygiene.md` with a canned script)
that takes an optional name filter and reports:

- top consumers grouped by process name, with summed working-set MB
- for chromium-family names, the true top-level window count alongside the process count
- rootless processes: parent dead, or parent created after the child (PID reuse), listed separately
- for a named scope, ancestry chains up to a chosen "owner" process name

Keep it advise-only by default, matching `/disk-doctor`'s stance - print what it found and the exact
kill command, do not kill. Killing processes attached to live sessions is a decision for Joe.

## Acceptance

- One invocation answers "is anything orphaned right now, and what is using the memory".
- Distinguishes parent-dead from pid-recycled rather than collapsing both into "orphan".
- Reports window count, not just process count, for chromium-family processes.
- Does not kill anything unless explicitly asked.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] Blocked by todo 58 (the skills-directory audit), which is itself waiting on your answer about how it should run. Nothing to decide here directly: answer 58 and this unblocks.

## Notes

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: new `/orphan-audit` skill, or a canned script referenced from
  `refs/process-hygiene.md`, matching the report shape the Approach already specifies - top
  consumers by summed working set, chromium-family window count against process count, parent-dead
  and pid-recycled rootless processes listed separately, ancestry chains up to a live `claude.exe`.
  Advise-only, same posture as `/disk-doctor`. Blocked on the skill audit, todo 58. This was
  produced by a strict second-pass re-triage that specifically asked whether a defensible answer
  exists without the dev; it concluded yes. Not executed only because the session ended.
- ee21444: orphan-audit.ps1 added under skills/disk-doctor as a runnable script (58 ruled script, not skill). Advise-only, never kills.
