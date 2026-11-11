<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Build watcher should flag a partial Tauri release

**Type:** skill-improvement
**Origin:** ai
**Summary:** Teach the commit build-watch skill that a red run with the Windows publish already green is a partial release, so it never auto-fixes or re-pushes at the same version.

## Why

Found by two review passes on 2026-11-11 in `claude_usage_in_taskbar` (workflow change 507309f6). Joe has not yet approved a global skill edit; this is filed, not applied.

## Goal

`skills/commit/build-watch.md` (and optionally `watch-build.ps1`) handle the new release shape: `publish-windows` can succeed while `build-macos`/`publish-macos` fail.

## Context

- `watch-build.ps1:199` matches skipped jobs with `^(publish|release)([\s(_-]|$)`, which already matches `publish-windows` and `publish-macos` and not `upload-android`, so no code change is strictly required.
- On a macOS-only failure the watcher reports `BUILD_RESULT=failure FAILED=1/1` followed by the failed logs. Nothing says Windows is already live, and the skill's default next step (auto-fix, re-push via `/commit push`) is a no-op: the `check` job skips once the `tauri-vX` tag exists (`.github/workflows/tauri-release.yml`, job `check`).
- The project's own `.github/workflows/auto-fix-release.yml` already ignores failures after the tag; the global skill is the remaining gap.

## Approach

In `build-watch.md` "Gated auto-fix" and "Reporting discipline": when a Tauri release run fails and `publish-windows` succeeded, report it as a PARTIAL release naming which platform shipped; do not auto-fix or re-push at the same version; offer `gh run rerun <id> --failed` (within 30 days of the run) for a transient failure; a code fix needs a version bump via `/release`. Optional: have `watch-build.ps1` list job names and results on `failure`.

## Acceptance

- A simulated run with `publish-windows` green and `build-macos` red is reported as partial, with the rerun advice, and triggers no auto-fix.
- `test_watch_build.sh` still passes.
