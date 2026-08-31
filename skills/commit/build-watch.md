# Build watch (after any push variant)

Read on demand from `/commit`'s `push`, `pushbump`, and `pushnbump` flows, and
equally from a bare or direct `git push` run outside those flows - not needed
for a plain `/commit` that doesn't push.

After a successful `git push`, whether from `push`, `pushbump`, `pushnbump`, or a bare `git push` you ran directly, watch the GitHub Actions run(s) that push triggered. A single push can kick off several workflows (test + lint + build); the watcher tracks **all** runs for the pushed sha and reports failure if any of them fails. **Non-blocking**: launch the watcher in the background, tell the user it's watching, and yield control immediately. The user can ignore it or say "drop it" to stop caring.

**Timeout & killing a stuck watcher:** the watcher has a wall-clock ceiling, default 30 minutes (`-TimeoutMinutes`, override if needed). Past that it stops watching, prints `BUILD_RESULT=timeout`, and exits cleanly - no orphan process. A Tauri-style multi-platform release build routinely runs longer than 30 minutes across all its runners - pass a higher `-TimeoutMinutes` (e.g. 60) for that kind of workflow rather than trusting the default. It also writes its own PID to `skills\commit\watch-build.pid` on launch (removed on exit). If the dev says "drop it" and you want it gone immediately rather than waiting for the timeout:

`Stop-Process -Id (Get-Content "C:\Users\tecno\.claude\skills\commit\watch-build.pid") -Force`

Steps:

1. **Capture the pushed sha immediately.** The very next tool call after `git push` succeeds - before this doc's own marker-clearing step or anything else can let a peer's uncommitted-but-committed work land on top - run `git -C <path> rev-parse HEAD` and save the result. In a shared checkout HEAD can move between the push completing and the watcher launching (a peer commits, unpushed, right after), so this captured value, not a later `rev-parse`, is what step 4 passes to `-Sha`.
2. **Clear the loop-breaker marker for a fresh manual push.** If this push was initiated directly by the user (not a re-push from a prior auto-fix), delete `<git-dir>/commit-buildwatch-autofixed` if it exists. (`<git-dir>` = `git -C <path> rev-parse --git-dir`.) This gives each manual push its own one-shot auto-fix budget.
3. **Detect CI.** Only watch if ALL hold: `gh` is installed (`gh --version` succeeds), the repo has a GitHub remote (`gh repo view` succeeds), and `.github/workflows/` exists with at least one workflow file. If any fail, skip the watch silently - no message, no script launch.
4. **Launch the watcher in the background.** Get the branch (`git -C <path> rev-parse --abbrev-ref HEAD`), then run, in the background, WITH the sha captured in step 1 passed explicitly - passing it programmatically here avoids both risks a `-Sha` argument otherwise carries: a human mistyping a hand-typed sha, and (the one that bit this repo) a shared checkout drifting between push and launch:

   `& "C:\Users\tecno\.claude\skills\commit\watch-build.ps1" -Branch <branch> -RepoPath <path> -Sha <sha>`

   Use a literal path (never `$env:`-built) so it doesn't trigger a permission prompt.

   **"In the background" means the PowerShell tool's own `run_in_background: true` parameter, and
   nothing else.** Never `Start-Process`, `Start-Job`, `nohup`, or a trailing `&`: those detach the
   process from the harness's background-task tracking, so step 5's "you'll be re-invoked with its
   stdout" never fires and the watcher runs to completion with nobody reading the result. A 2026-08-10
   `windows_taskbar_widgets` push launched it via `Start-Process -WindowStyle Hidden` and the result
   was silently lost; the stray process had to be found with `Get-CimInstance` and killed. The call
   is a single PowerShell tool call carrying the line above, with `run_in_background` set to true.
5. **Announce and move on.** Tell the user: "Pushed. Watching the CI build in the background - I'll ping you when it lands. Say 'drop it' to ignore." Do NOT block or poll; you'll be re-invoked when the watcher exits.

When the watcher finishes you are re-invoked with its stdout. Parse the `BUILD_RESULT` marker:

- `BUILD_RESULT=success` -> all runs passed (the marker lists how many + their workflow names). Tell the user the build passed. Delete the `commit-buildwatch-autofixed` marker if present. Done.
- `BUILD_RESULT=no_run` -> no run registered for the pushed sha within ~3 min. Tell the user you couldn't find a CI run (it may not have triggered) and stop. Do not relaunch the watcher.
- `BUILD_RESULT=api_error` -> every poll in the detection loop errored (`LAST_ERROR` holds the last message) - this is NOT "no run exists", the watcher just couldn't reach/authenticate to the API (e.g. `gh`'s active account flipped mid-poll). Tell the user the watcher hit an auth/API problem, not a missing run, and offer `gh run list` as a direct fallback to check manually.
- `BUILD_RESULT=failure` -> the build is red. Run the **gated auto-fix** below.
- `BUILD_RESULT=watch_error` -> `gh` hit a persistent transient error (auth flip, network blip, rate limit) while polling and could not confirm a completed status for one or more runs after retrying with backoff. This is NOT a build verdict - the run(s) may still be green, red, or in progress. Tell the user the watcher couldn't confirm the result and relaunch it (same command as before) rather than diagnosing a "failure" that might not exist.
- `BUILD_RESULT=timeout` -> the wall-clock ceiling (`TIMEOUT_MINUTES`, default 30) was hit before all runs resolved. Not a build verdict either - CI may still be running. Tell the user the watcher gave up after the timeout and offer to relaunch it (same command as before) if they still want the result.

### Reporting discipline

Applies whenever you inspect runs yourself (e.g. `gh run list`), not just when parsing the watcher's marker:

- A push can trigger more than one workflow. Enumerate and report every triggered run's conclusion, not the first or newest: `gh run list --json workflowName,status,conclusion,databaseId` over all rows from that push, never `--limit 1`.
- Never report "CI is green" while any triggered run is still `in_progress` or `queued` - name what's still pending instead.
- A `success` conclusion with `skipped` jobs is not automatically benign - state WHY it skipped. For a tauri release workflow, the usual cause is a pre-existing `<tag-prefix><version>` tag, possibly left behind by an earlier failed run.

### Gated auto-fix

The watcher prints the failed-step logs after a `failure` marker. Diagnose from them, then branch:

- **First, check the loop-breaker.** If `<git-dir>/commit-buildwatch-autofixed` already exists, the one-shot budget is spent: go straight to **STOP and ask** with the new logs. Do not auto-fix.
- **Auto-fix, then re-commit and push without asking** ONLY when ALL hold:
  1. It's a real code failure (test, typecheck, lint, build/compile error) - NOT infra (runner timeout, network, expired secret, rate limit, obvious flake).
  2. The failure traces to files in the diff you just pushed.
  3. The fix is mechanical / unambiguous.

  When all three hold: write the marker file `<git-dir>/commit-buildwatch-autofixed` (records the one-shot is now used), apply the fix, run the project's fast checks locally to confirm green, then re-commit and push via `/commit push` (per the global rule, never commit directly). That re-push starts a fresh build watch automatically - the marker ensures a second failure can't trigger another auto-fix.
- **Otherwise: STOP and ask.** Show the diagnosis and the proposed fix, then ask the user (AskUserQuestion) to approve before changing anything. This covers infra/flake failures, failures in files you didn't touch, and any judgment-call fix.
