<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo covers watch-build.ps1 treating cancelled or skipped jobs as success -->
# watch-build.ps1 reports success when a job was cancelled and publish was skipped

**Type:** task
**Origin:** ai
**Summary:** The build watcher printed `BUILD_RESULT=success` for a release run whose macOS job was cancelled and whose tag and publish jobs were skipped, so nothing was published.

## Goal
`watch-build.ps1` never reports `success` for a run where a build job was cancelled or the publish job was skipped.

## Context
2026-11-06, claude_usage_in_taskbar, release 0.2.146. After the fix push 2c1abe57 the watcher printed `BUILD_RESULT=success RUNS=3 (...)` with the note `non-success conclusions (not failures): ... Tauri Release=cancelled`. In fact the macOS job was cancelled (GitHub: "The configuration 'macos-14-arm64-us-default' is not supported"), so `tag` and `publish` were skipped and no release existed. Only a manual `gh run view <id> --json jobs` showed it, and the rerun failed the same way. `skills/commit/build-watch.md` "Reporting discipline" already says a success with skipped jobs is not benign, but the script's own verdict ignores it.

## Approach
Treat a `cancelled` workflow conclusion as its own marker (for example `BUILD_RESULT=cancelled`) with the failed job names, and in `build-watch.md` tell the caller to check that `publish` ran when the push was meant to release. Add a case to the watcher's tests if it has them.

## Acceptance
A run whose conclusion is `cancelled`, or whose publish job is `skipped` after a version bump, produces a non-success marker naming the job.
