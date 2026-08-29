<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=5, reconfirm-count=1, content-hash=b88cdbcb -->
<!-- duplicate-checked -->
# build-watch.md has no recovery path when a run is stuck `queued` and even the cancel API refuses it

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/build-watch.md`'s `BUILD_RESULT=timeout`/`watch_error` guidance assumes the stuck
run will eventually resolve or can be cancelled and retried. Add the recovery path for the case
where it does neither.

## Context

Filed 2026-08-26 from a `claude_usage_in_taskbar` session's `/close` retrospective (todo 809 in
that repo's own backlog covers the unrelated screenshot follow-up from the same session).

Sequence observed: `/commit pushnbump` pushed two commits; `watch-build.ps1` reported
`BUILD_RESULT=failure FAILED=1/` for the `Tauri Release` run, but the failed `check` job had
`status=queued`, empty `steps: []`, and `updated_at` identical to `run_started_at` - it never
actually started, so there were no logs to diagnose (`gh run view --log-failed` printed nothing).

Per `build-watch.md`'s own gated-auto-fix rule this correctly was NOT a code fix (infra, no
traceable failure). The next step tried was `gh run rerun <id> --failed`, which failed:
`"This workflow run cannot be retried"`. A relaunched watch then hit `BUILD_RESULT=timeout` after
the full 30 minutes, with the run STILL `queued` 4+ hours later. `gh run cancel <id>` then failed
too: `"Cannot cancel a workflow run that is completed"` (contradicting the run's own `queued`
status - a genuinely broken run object, not user error). The raw REST cancel endpoint gave the
real reason: `"Cannot cancel a workflow re-run that has not yet queued."` (HTTP 409).

Root cause, per githubstatus.com checked mid-session: a GitHub Actions incident that day ("3.7% of
jobs on larger runners became stuck") had already been marked resolved, but this specific run
never recovered on its own even after resolution - an orphaned run object stuck in limbo, not
something `gh run rerun`/`gh run cancel` can touch.

**What actually worked:** `gh workflow run <workflow-file> --ref <branch>` (manual
`workflow_dispatch`, confirmed present as a trigger in `tauri-release.yml`) started a completely
fresh run that went `in_progress` within seconds and later completed `success`. None of
`build-watch.md`'s existing guidance names this path.

## Approach

Add a new bullet to `build-watch.md`'s `BUILD_RESULT=timeout` (and possibly `watch_error`)
handling: if a relaunched watch times out AGAIN on the same run, or `gh run cancel`/`rerun` both
fail with a state-contradicting error (run object claims `queued`/`completed` inconsistently
across `gh run view` vs `gh run cancel` vs the raw REST `cancel` endpoint), treat it as an
orphaned run rather than continuing to poll or retry the same run id. Recovery: confirm the
workflow file has `workflow_dispatch:` in its `on:` triggers (most release/CI workflows do,
including this repo's own `tauri-release.yml`), then `gh workflow run <file> --ref <branch>` to
start a genuinely fresh run, and watch THAT one (a fresh `-Branch`/`-RepoPath` call, since it
resolves HEAD itself). If the workflow has no manual-dispatch trigger, say so plainly rather than
guessing another retry path - an empty commit / re-push is the fallback in that case, but should
be a last resort, not a default.

## Acceptance

- `build-watch.md` names this orphaned-run scenario and its exact recovery steps, distinguishing
  it from a normal transient `timeout` (which just means "still running, maybe check again") or a
  normal `watch_error` (API auth/network blip).
- The distinguishing signal is spelled out concretely (contradictory status across `gh run view`
  vs `gh run cancel`, or a second consecutive timeout on the same run id) so a future session
  doesn't have to rediscover the diagnostic sequence from scratch.

## Notes

Not urgent - this is a rare GitHub-infra edge case, not a routine failure mode. The value is in not
re-deriving the multi-command diagnostic dance (view -> cancel -> REST cancel -> githubstatus.com
-> workflow_dispatch) from zero next time it happens.
