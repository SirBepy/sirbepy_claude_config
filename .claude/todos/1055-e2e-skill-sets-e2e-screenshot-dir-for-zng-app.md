<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped todos and done/ for E2E_SCREENSHOT_DIR, rename-session, "screenshot dir" on 2026-09-30; relocated from zng-app todo 41, nothing here covered it. -->
# 1055 - /e2e (or /flutter-e2e) should set E2E_SCREENSHOT_DIR from rename-session.ps1 -GetId

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-30

## Goal

Screenshots from a zng-app e2e run land in the session folder `/close` and `/disk-doctor` look in,
without the client repo calling Joe's personal `~/.claude` tooling.

## Context

Relocated from zng-app todo 41 on 2026-09-30. `zng-app/e2e/lib/config.js:97-118` names the
screenshot folder by walking the process tree to a `claude*` ancestor, the same walk
`rename-session.ps1` was moved off because it resolved to two different PIDs within one session.
Measured 2026-08-29: `/close` resolved `20736-134325031119280387` while the same session's e2e run
wrote to `.for_bepy/screenshots/33700-639236021641924960/`, so `/close` reported 0 screenshots for
a session that captured 5, and 45+ orphan id folders accumulated.

Fixing it inside zng-app (shelling out to `rename-session.ps1`) was rejected by the 2026-09-30 B3
scout: zng-app is a tracked client repo and must not depend on a personal `~/.claude` script. The
repo already honours an override, `E2E_SCREENSHOT_DIR` (`e2e/lib/config.js:107`, `e2e/README.md:115`).

## Approach

1. In the skill that launches the zng-app suite (`skills/e2e` delegating to `skills/flutter-e2e`,
   or wherever `run-all.js` is invoked), resolve the id once via `rename-session.ps1 -GetId` and
   pass `E2E_SCREENSHOT_DIR=<repo>/.for_bepy/screenshots/<id>` in the run's environment.
2. Mention the same in `refs/builder-preamble.md`'s screenshot paragraph if dispatched agents run
   the suite directly.

## Acceptance

- A `/e2e` run in zng-app writes screenshots into the folder `rename-session.ps1 -GetId` prints.
- No change to any zng-app tracked file.

## Notes
