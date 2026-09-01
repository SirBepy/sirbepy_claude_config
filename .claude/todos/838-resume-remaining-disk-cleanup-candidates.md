<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Resume the remaining disk-doctor cleanup candidates from the 2026-08-29 scan

**Type:** task
**Origin:** ai

## Goal

Offer the still-untouched safe-cache cleanup items from the 2026-08-29 Windows disk-doctor scan
through the per-item delete-confirmation gate (`skills/disk-doctor/gate.md`), the next time Joe
runs `/disk-doctor` or otherwise asks about freeing up space.

## Context

That session ran the full scan, then executed one approved delete (C:\tmp items older than 14
days, ~821 MB, verified removed). Claude then listed further candidates and said "say which and
I'll send them through the approval gate" - the conversation moved on to Steam/D:-drive questions
instead, and none of these were ever confirmed or declined:

- Docker (LocalAppData) - 27.24 GB, `docker system prune -a`
- LocalAppData\Temp - 26.43 GB
- Gradle cache (`~/.gradle/caches`) - 17.41 GB
- pip cache - 6.72 GB
- npm-cache/cargo registry/pnpm store - ~5 GB combined
- Project build-artifact dirs (revaire-mobile incl. 2 active worktrees, meetily-diarize `.venv`,
  ssy-mobile `build`, odysseus `venv`, claude_usage_in_taskbar stt-sidecar `.venv`, zng-app
  `build`, llama.cpp `build`) - ~30 GB combined, all regenerate via their own build command

All of the above are cache/build-artifact patterns already in `windows.md`'s KNOWN-SAFE list, so no
new judgment call is needed on whether they're safe - only per-item confirmation through the gate
before any delete actually runs.

## Approach

1. Re-check current sizes are still roughly accurate (they'll have drifted somewhat since
   2026-08-29) rather than reusing stale numbers verbatim.
2. Send each item through `mcp__cc_conductor__ask_user_question` per `gate.md`'s delete-confirmation
   gate - one item (or tightly-related group) per question, naming the exact path/size/command.
3. Run only what Joe approves; verify each deletion independently afterward per the existing
   gotcha in `windows.md`.

## Acceptance

- Every item above has been offered through the gate at least once (approved-and-run, or
  explicitly declined) - this todo is done once none remain silently unoffered.

## Notes

- Not urgent/blocking - these are optional disk-space wins, not anything broken. Fine to fold into
  the next `/disk-doctor` invocation rather than proactively resurrecting this session.
