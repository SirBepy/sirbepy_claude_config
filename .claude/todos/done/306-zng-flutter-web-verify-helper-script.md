<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# A small helper script for the zng flutter-web restart-and-verify dance

**Type:** skill-improvement

## Goal

The "restart the flutter-run supervisor entry, poll `/logs` until `is being served at` appears,
then run one Playwright script" sequence was repeated manually ~10 times in a single session
(sc-54746 verification, 2026-08-06), each time as a fresh multi-line Bash curl+poll block. The
underlying DDC/DWDS one-connection-per-process-lifetime limit is already documented in
[[reference_zng_admin_dev_login]], but there's no reusable script for the restart+wait half of
the dance - only prose describing it.

## Context

Every fresh Playwright connection to a still-running zng flutter-run process (admin, app, or
biller) needs a restart first, or it hangs indefinitely on a blank page. This session hand-wrote
the same `curl -X POST .../restart` + poll loop over a dozen times across `Bash` calls, burning
turns and tokens on boilerplate instead of the actual verification logic.

**Update 2026-08-11:** recurred again during SC-54834 verification (2 hand-written restart+poll cycles, one after hitting the exact "second cold connection stalls on blank page" trap this todo already references). Still no reusable script; still worth building.

## Approach

A small PowerShell or Node helper (e.g. `~/.claude/skills/supervised-run/restart-and-wait.ps1
-ProcId <id>`) that: reads the supervisor token/port, POSTs `/restart`, polls `/logs` for `is
being served at` (or `serving at` for non-flutter kinds) up to a timeout, and exits 0/1
accordingly. Callable as a single Bash/PowerShell line before each fresh Playwright script
instead of hand-rolling the loop. Could live in the `supervised-run` skill folder since it's the
skill that already owns the restart/health-check vocabulary.

## Acceptance

Restarting a supervised flutter-run entry and waiting for it to be ready is a single command
call, not a hand-written poll loop, the next time this pattern comes up.

## Notes

- Relocated from `62` in `zng-admin` via /cleanup-todos 2026-08-13: it builds a script inside `~/.claude/skills/supervised-run/`, a global skill folder.
- Re-verified 2026-08-13: `~/.claude/skills/supervised-run/` holds only `proxy-hub.md`, `SKILL.md`, `sv.ps1`, `tauri.md`; a repo-wide `find -iname "*restart-and-wait*"` under `C:\Users\tecno\.claude` returns zero hits.
- Done 2026-08-13, placed GLOBALLY in skills/supervised-run/ rather than the zng repo. Reasoning: the repeated pain is the restart-then-poll-logs dance against the server_supervisor API, which is generic across flutter, Vite, NestJS and anything else supervised. The zng-specific parts (auth, dev-login DDC quirks, which Playwright script) already live in project memory and skills/flutter-e2e/. New restart-and-wait.ps1 takes -Id, optional -Marker, -TimeoutSec and -NoRestart; it reads the supervisor token the same way sv.ps1 does, calls /reload for flutter kind and /restart otherwise, then polls logs using a HIGH-WATER-MARK index so a stale marker from before the restart cannot false-positive readiness. Flutter kind gets a default marker; other kinds must pass one since there is no universal ready line. It also reports the live-reload proxy URL, which is the port a Playwright script actually needs, per that skill's own proxy-versus-raw-port gotcha. Verified live against the real running supervisor for three cases including proving the staleness guard rejects an old marker. NOT verified: the actual /reload and /restart POSTs and the flutter default-marker path end to end, because that would mean restarting one of Joe's live entries without asking.
