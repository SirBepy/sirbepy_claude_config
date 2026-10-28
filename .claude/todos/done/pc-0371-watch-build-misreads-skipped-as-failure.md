<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=8, reconfirm-count=1, content-hash=fdf651f9 -->
# watch-build.ps1 reports BUILD_RESULT=failure when a triggered workflow is `skipped`

**Type:** task
**Origin:** ai

## Goal

Stop `skills/commit/watch-build.ps1` from calling a green build red. A `skipped` workflow conclusion must not count toward `FAILED=`.

## Observed

2026-08-18, `claude_conductor` push of `f98cfc37` (v0.2.72 release). The watcher printed:

```
BUILD_RESULT=failure FAILED=1/2
----- FAILED: Auto-Fix Release Failure (run 32118357724) -----
```

with no log body under the header. The actual truth from `gh run list`:

| workflow | status | conclusion |
| --- | --- | --- |
| Auto-Fix Release Failure | completed | **skipped** |
| Tauri Release | completed | **success** |

The release genuinely succeeded - `gh release list` shows `tauri-v0.2.72` published at 08:49:27Z with `Claude-Conductor_0.2.72_windows_x64.exe`, its `.sig`, and `latest.json` attached.

`Auto-Fix Release Failure` is *supposed* to be skipped: it is conditioned on the release workflow failing. Every prior successful push shows the same pattern (`7a1af633` skipped, `9cce73f0` skipped, `9cca1907` skipped). So this misreport fires on **every** healthy release, not as a one-off.

Why it matters beyond noise: `build-watch.md`'s `BUILD_RESULT=failure` branch routes into the **gated auto-fix**, which can write the loop-breaker marker, edit code, and re-push on its own. A false `failure` aims that machinery at a build that was never broken. In this run it was caught only because the reporting-discipline rule ("enumerate every triggered run's conclusion") prompted a manual `gh run list`.

## Second, separate bug in the same script

The FIRST watcher launch for the same sha exited with:

```
BUILD_RESULT=timeout TIMEOUT_MINUTES=30 RUNS=
```

`RUNS=` is empty even though run `32115742584` for `f98cfc37` had been registered and `in_progress` since 08:18:54Z - well within the window. So the run-resolution step never latched onto an in-progress run, and the watcher sat for 30 minutes tracking nothing. Note `build-watch.md` explicitly distinguishes `no_run` ("no run registered within ~3 min") from `timeout`; this was neither - the run existed the whole time.

Also worth revisiting: a Tauri multi-platform release routinely outruns the 30-minute default, so the default ceiling is arguably too low for that project even once resolution is fixed.

## Approach

1. In `watch-build.ps1`, treat a conclusion of `skipped` (and almost certainly `cancelled` and `neutral`) as non-failing. Only `failure` and `timed_out` should increment the failed count. Check how the script currently derives `FAILED=` - the symptom suggests it counts "conclusion != success" rather than "conclusion == failure".
2. Fix the empty-`RUNS=` resolution path so an already-`in_progress` run for the target sha is picked up. Reproduce by launching the watcher against a sha whose run started a minute or two earlier.
3. Consider raising the default `-TimeoutMinutes`, or documenting in `build-watch.md` that Tauri-style multi-platform releases need an explicit higher value.
4. Sanity-check the empty log body too: the `----- FAILED: ... -----` header printed with nothing under it, so the failed-step log fetch also produced nothing for a skipped run.

## Acceptance

- A push whose release workflow succeeds and whose auto-fix workflow is skipped reports `BUILD_RESULT=success`, not `failure`.
- The watcher resolves and tracks a run that was already `in_progress` when it launched (non-empty `RUNS=`).
- A genuinely red build still reports `BUILD_RESULT=failure` with the failing step's logs - do not fix this by weakening failure detection.

## Notes

- Filed from a `claude_conductor` session per the "global findings go in the `~/.claude` backlog" rule; no global files were edited from that session.
- Relevant reporting rule already in `build-watch.md`: "A `success` conclusion with `skipped` jobs is not automatically benign - state WHY it skipped." That rule is what surfaced this; the script just does not implement the same distinction.
- 1dbaf1e: watch-build.ps1 no longer counts skipped/cancelled/neutral as failure; run resolution picks up an in-progress run for the target sha.
