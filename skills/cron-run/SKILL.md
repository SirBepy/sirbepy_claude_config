---
name: cron-run
description: Triggers on /cron-run only. Schedules a queue of LOCAL overnight agents via Windows Task Scheduler; PC must stay on and logged in (Claude Code need not be open). For remote/PC-off use /night-run.
argument-hint: "<count|all> [every] <interval> [till HH[AM|PM]] | tick | cancel"
---

# /cron-run

> Schedule overnight agents to work plan files locally via **Windows Task
> Scheduler**, one task at a time, with review and side-branch failure isolation.
> The PC must stay on and the user logged in (screen may be locked). Claude Code
> does NOT need to remain open: each tick launches a fresh headless `claude -p`.

## Why Task Scheduler (read this)

The previous version used the in-app `CronCreate` tool with `durable: true`. On
this build that flag is **silently downgraded to a session-only in-memory timer**
that is never written to `scheduled_tasks.json` and only advances while the REPL
is actively cycling. Left idle overnight it fires nothing. This was diagnosed and
proven: a binary self-upgrade or simply closing/idling the REPL kills the timer.

This skill therefore schedules **OS-level Windows Scheduled Tasks** that fire
independently of any Claude session. Each firing runs a wrapper script
(`run-tick.ps1`, alongside this file) that launches `claude -p "/cron-run tick"`.
Verified working live: a scheduled task fired on time while the REPL was idle,
launched headless claude as the user, authenticated, ran, and exited.

## Terminology

- **Plans** (source): implementation plans from superpowers. Live in
  `docs/superpowers/plans/*.md`.
- **Queue** (execution order): the ordered list this run executes. Lives in
  `docs/night_run/queue/*.md` plus `docs/night_run/INDEX.md` for state.

Both live in the same git repo, so all moves are plain `git mv`.

## Modes

The first argument selects the mode:

- `tick` -> single task cycle (the scheduled task fires this; never run by the dev
  except for a manual dry-run)
- `cancel` (or `stop`) -> remove all this project's cron-run scheduled tasks
- anything else -> schedule mode (the dev runs this)

## Prerequisites (schedule mode only)

Refuse with a clear message if any check fails:

1. Inside a git repo (`git rev-parse --is-inside-work-tree`)
2. Platform is Windows (this skill uses Task Scheduler). On non-Windows, refuse and
   suggest `/night-run` (remote) instead.

Working-tree cleanliness and queue-population are resolved interactively in Steps
0 and 0.5.

---

## Schedule mode

### 0. Import plans into the queue

The source dir `docs/superpowers/plans/` IS the curated list. Whatever lives there
gets queued, no selection prompt.

Glob `docs/superpowers/plans/*.md`.

- If empty AND `docs/night_run/queue/` is also empty (or absent): refuse with
  "No plans in `docs/superpowers/plans/` and queue is empty. Write a plan via
  superpowers first, then re-run /cron-run."
- If empty BUT `docs/night_run/queue/` already has plans: skip to Step 0.5.
- Otherwise: print `Importing <N> plan(s) to queue:` + a bullet list (filename +
  first `# ` heading). Then for each plan:
  - Create `docs/night_run/queue/` if missing (`mkdir -p`)
  - `git mv docs/superpowers/plans/<file>.md docs/night_run/queue/<file>.md`

Then commit via `/commit` (Skill tool) - subject `night-run: queue <N> plan(s)
from superpowers`, body lists moved slugs - and push. (Schedule mode runs in your
interactive session, so `/commit` is fine HERE. Only TICK mode must avoid it; see
the warning in Tick mode.)

### 0.5. Resolve dirty working tree

Run `git status --porcelain`. If empty, continue.

If non-empty, present via `AskUserQuestion` (single-select):

- **Commit via /commit** - invoke `/commit`. After it completes and the tree is
  clean (`git status --porcelain` empty), continue. If `/commit` aborts/fails,
  abort `/cron-run`.
- **Abort** - stop without scheduling.

(A clean tree at schedule time matters more than usual: ticks reset the working
tree on the failure path. See Tick mode step 8b guard.)

### 1. Parse arguments

Free-form, tokens in any order:

- count: `all` or positive integer
- interval: regex `(every )?(\d+)(m|min|h|hr)` (e.g. `30m`, `every 1h`, `2hr`)
- end cap (optional): regex `(till|until) (\d{1,2})(:\d{2})?(am|pm)?`
  (case-insensitive). No am/pm and hour <= 12: assume the next occurrence.

Reject and ask if count or interval is absent.

### 2. Build INDEX.md

- Branch via `git rev-parse --abbrev-ref HEAD`
- Glob `docs/night_run/queue/*.md`. Title = first `# ` heading or filename.
- If `docs/night_run/INDEX.md` exists, preserve `[x]` and `[!]` lines by plan
  path. New plans get `[ ]`.
- unfinished = count of `[ ]` lines after merge
- If count is an integer, unfinished = min(unfinished, count)
- firings = unfinished + 2 if unfinished > 0, else 0 (flat buffer; empty queue
  schedules nothing)
- window_minutes = firings * interval_minutes
- If end cap given: window_minutes = min(window_minutes, minutes from now to
  end_cap). If that is less than unfinished * interval, note in the summary:
  `<X tasks won't fit in the window>`.
- Write INDEX.md (format below), commit (`git add docs/night_run/INDEX.md`,
  `git commit -m "cron-run: init INDEX"`), and push.

### 3. Register the scheduled task

ONE recurring task with a time-window repetition (not N one-shots: easier to clean
up, and the stateless INDEX-driven tick does not care how firings arrive).

Compute:
- `$SkillDir` = the base directory of THIS skill (given to you at invocation,
  e.g. `C:\Users\tecno\.claude\skills\cron-run`). `$Wrapper = $SkillDir\run-tick.ps1`.
- `$RepoPath` = absolute repo root (`git rev-parse --show-toplevel`, backslashed).
- `$repoSlug` = repo folder name, non-alphanumerics -> `-`.
- `$branchSlug` = current branch, non-alphanumerics -> `-`.
- `$TaskName = "ClaudeCronRun_<repoSlug>_<branchSlug>"`.
- `$At` = first fire = now + interval (local). `$Interval` minutes. `$Window`
  minutes from Step 2.

Run this (PowerShell 5.1; one tool call). Substitute the `$...` values literally:

```powershell
$TaskName = "ClaudeCronRun_<repoSlug>_<branchSlug>"
$Wrapper  = "<SkillDir>\run-tick.ps1"
$RepoPath = "<RepoPath>"
$At       = (Get-Date).AddMinutes(<Interval>)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument ('-ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $Wrapper + '" -RepoPath "' + $RepoPath + '" -TaskName "' + $TaskName + '"')
$trigger = New-ScheduledTaskTrigger -Once -At $At `
  -RepetitionInterval (New-TimeSpan -Minutes <Interval>) `
  -RepetitionDuration (New-TimeSpan -Minutes <Window>)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes <max-tick-minutes, e.g. interval minus 5, floor 20>) `
  -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -TaskPath "\ClaudeCronRun\" `
  -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
  -Description "Claude cron-run for <repoSlug>/<branchSlug>. Auto-created; safe to delete." -Force | Out-Null
```

Notes baked in:
- `-LogonType Interactive` + `-RunLevel Limited`: PROVEN to launch headless claude
  with working keychain auth. Do NOT use `S4U` (no keychain) or `Highest` (UAC
  prompt fails unattended).
- Do NOT add `-NoProfile` to the action: the PS profile sets PATH for
  `git`/`fvm`/`flutter`. Keep `-ExecutionPolicy Bypass` so the unsigned wrapper runs.
- `-MultipleInstances IgnoreNew`: a slow tick that overruns the interval drops the
  next firing instead of doubling up.
- `WakeToRun` is intentionally omitted: for a desktop, advise disabling sleep for
  the window rather than relying on wake timers. If the dev wants wake-from-sleep,
  they must enable wake timers in their power plan and the task needs `-WakeToRun`.

### 4. Print summary

- branch, repo path
- interval, firings (= tasks + 2 buffer), window end time
- first and last fire time (local)
- task name + Task Scheduler folder `\ClaudeCronRun\`
- per-tick log dir: `docs/night_run/logs/`, heartbeat: `docs/night_run/heartbeat.log`
- reminder: PC must stay on and logged in (screen may lock). Claude Code does NOT
  need to be open. Recommend disabling sleep for the window.
- how to cancel: `/cron-run cancel`
- offer a watchable first tick: "register fired in <interval> min; to verify now,
  run `/cron-run tick` once manually."

---

## Tick mode

Launched by the wrapper as a fresh headless `claude -p`. No inherited chat state.
INDEX.md is the only source of truth.

> CRITICAL - NO `/commit` IN TICK MODE. The `/commit` skill runs the project test
> suite and ABORTS waiting for a human if tests fail. Overnight there is no human:
> the work would never commit, the task would never be marked done, and the next
> tick would redo it on a dirty tree. Use RAW GIT for every commit below, exactly
> as `/night-run` does. (Schedule mode may use `/commit`; tick mode may not.)

### 1. Reclaim stale locks

Read `docs/night_run/INDEX.md`. Interval comes from the `Interval:` header. For
each `[~ HH:MM]` line, if `now - HH:MM` > `ceil(interval * 1.25)` minutes, rewrite
it back to `[ ]`.

### 2. Pick next task

First `[ ]` line in document order. If none: output the exact token
`CRON_RUN_ALL_DONE` on its own line (the wrapper greps for it to self-unregister
the task), also print "cron-run: all tasks done", and exit cleanly.

### 3. Pre-flight guard (protect the dev's work)

Run `git status --porcelain`. If it shows changes (the tree is dirty before we
start) AND `docs/night_run/.tick.lock` does NOT exist or is younger than this
process: this is likely the dev's own uncommitted work, OR a prior tick's debris.
Do NOT blindly destroy it. Instead:
- If the only dirty path is `docs/night_run/INDEX.md`, proceed (that is ours).
- Otherwise mark the chosen task `[!] <slug> (dirty tree - skipped)`, commit the
  INDEX update with raw git, push, log it, and exit. Never run `git clean`/`git
  reset` against pre-existing unknown changes.

### 4. Soft-lock the task

Rewrite the chosen `[ ]` to `[~ HH:MM]` (current local time, zero-padded). Then:
- `git add docs/night_run/INDEX.md`
- `git commit -m "cron-run: lock <slug>"`
- `git push`

### 5. Verify branch

`git rev-parse --abbrev-ref HEAD` vs the `Branch:` value in INDEX. If different,
`git checkout <branch>`. If that fails, mark `[!]` with reason `branch mismatch`,
commit + push INDEX (raw git), exit.

### 6. Execute the plan

Read the linked plan file. Decide subagent-driven vs inline per CLAUDE.md
"Subagent-Driven vs Inline Execution". Execute every change the plan describes.

**Forbidden in tick mode** (no human to supervise): do NOT start any long-lived
process - no dev servers, watchers, `flutter run`, `npm run dev`, `docker compose
up` without `-d`+teardown, `/supervised-run`, `/flutter-dev-runner`. If a plan step
needs a running server to verify, do the build/compile checks only and note the
skipped runtime check in the commit body.

### 7. Review subagent

Dispatch a fresh general-purpose Agent subagent:

> Cold review of the current uncommitted diff against HEAD. The plan being
> implemented is at `<plan-path>`. Look for: bugs, unsafe patterns, missed edge
> cases, broken or missing tests, scope creep beyond the plan, security issues.
> Report issues as a numbered list with severity tags BLOCKER, WARN, or NIT. Do
> not edit any files. Be thorough; this code lands unsupervised.

### 8. Fix loop

If review has any BLOCKER: apply targeted fixes, re-dispatch the reviewer. Up to 4
total attempts (1 + 3 retries). WARN/NIT do not trigger a retry; capture them in
the commit body.

### 9a. Success path (no BLOCKER)

Stage by name (avoid `git add -A` so stray files are not swept in; if the plan
created many files, add the specific dirs it touched):
- `git add <changed paths>`
- `git commit -m "<slug>: <one-line summary>" -m "<WARN/NIT list if any>"`
- `git push`
- Rewrite `[~ HH:MM]` to `[x]` in INDEX.md
- `git add docs/night_run/INDEX.md`
- `git commit -m "cron-run: complete <slug>"`
- `git push`

### 9b. Failure path (BLOCKER after 4 attempts)

Commit the WIP to a side branch FIRST so nothing is lost, THEN restore:
- `slug` = kebab-case plan filename without extension
- `git checkout -b cron-run/failed-<slug>`
- `git add -A`
- `git commit -m "WIP: cron-run failed <slug>" -m "<last review summary>"`
- `git push -u origin cron-run/failed-<slug>` (skip push if no remote; the branch
  still preserves the work locally)
- `git checkout <branch>` (from INDEX header)
- Now the tree may hold leftover untracked files from the failed attempt. Because
  the WIP is safely on the side branch, reset is safe: `git reset --hard HEAD`
  then `git clean -fd`. (This only runs after a clean checkout back to the run
  branch, never against pre-existing work - Step 3 guarded that.)
- Rewrite `[~ HH:MM]` to `[!] <slug> (side: cron-run/failed-<slug>)` in INDEX.md
- `git add docs/night_run/INDEX.md`
- `git commit -m "cron-run: failed <slug>"`
- `git push`

### 10. Log the run

Append one line to `docs/night_run/log.md` (create with `# Night Run Log` header
if missing):

```
<YYYY-MM-DD HH:MM> <[x]|[!]> <slug> attempts=<N>
```

- `git add docs/night_run/log.md`
- `git commit -m "cron-run: log <slug>"`
- `git push`

### 11. Finisher check

Re-read INDEX.md. If every task line is now `[x]` or `[!]` (no `[ ]` or `[~]`):
- Invoke `/next-ai-prompt --caller "cron-run tick" --mode night-run` (this runs as
  a top-level headless agent, so the Skill tool is available - this is NOT a
  forbidden `/commit`, it just writes a file). Then `git add
  .for_bepy/NEXT_AI_PROMPT.md`, `git commit -m "cron-run: next prompt"`,
  `git push`.
- Output the token `CRON_RUN_ALL_DONE` on its own line so the wrapper unregisters
  the scheduled task. (Belt-and-suspenders: the task's window also expires on its
  own, and any later no-op tick re-emits the sentinel from step 2.)

### 12. Orphan check before exit

Per CLAUDE.md "Process Hygiene", check for and kill orphan node/dart processes the
tick spawned (vitest/turbo/tinypool, stray dart/flutter). The wrapper does a
subtree sweep too, but do not rely on it alone.

---

## Cancel mode (`/cron-run cancel` or `stop`)

List this project's tasks and remove them:

```powershell
Get-ScheduledTask -TaskPath "\ClaudeCronRun\*" -ErrorAction SilentlyContinue |
  Select-Object TaskName, State
```

Then unregister (all of them, or just this repo's if the dev specifies):

```powershell
Get-ScheduledTask -TaskPath "\ClaudeCronRun\*" -ErrorAction SilentlyContinue |
  Unregister-ScheduledTask -Confirm:$false
```

Also remove a stale `docs/night_run/.tick.lock` if present. Report what was removed.

---

## INDEX.md format

```
# Night Run - YYYY-MM-DD

Branch: <branch>
Interval: <interval>
Scheduled: <N> (<unfinished> tasks + 2 buffer)
Started: HH:MM
End cap: <HH:MM | none>

## Tasks

- [ ] <title> - @docs/night_run/queue/<file>.md
- [~ HH:MM] <title> - @docs/night_run/queue/<file>.md
- [x] <title> - @docs/night_run/queue/<file>.md
- [!] <title> - @docs/night_run/queue/<file>.md (side: cron-run/failed-<slug>)
```

## Notes

- The wrapper `run-tick.ps1` (next to this file) owns working dir, per-tick
  logging (`docs/night_run/logs/tick_<stamp>.log`), a start-of-tick heartbeat
  (`docs/night_run/heartbeat.log`), a re-entrancy lock, and the reliable teardown
  (it greps the tick's stdout for `CRON_RUN_ALL_DONE` and calls
  `Unregister-ScheduledTask` itself - more reliable than asking the LLM).
- Gitignore the logs: add `docs/night_run/logs/`, `docs/night_run/heartbeat.log`,
  and `docs/night_run/.tick.lock` to `.gitignore` in schedule mode if not present.
- Permission mode: the wrapper uses `--permission-mode acceptEdits`, which relies
  on the dev's `settings.json` `permissions.allow` list for shell commands. If a
  plan needs a command not on the allowlist, that tick will stall until its
  `ExecutionTimeLimit` kills it (then the lock is reclaimed). If the dev wants
  guaranteed no-stall on a trusted personal repo, they can switch the wrapper to
  `--permission-mode bypassPermissions` (runs ANY command unattended - only for
  repos you fully trust).
- All tick commits use RAW GIT, never `/commit` (see the Tick mode warning).
- The dev can run `/cron-run tick` manually for a watchable dry-run before walking
  away.
- Optional hardening (not default): run ticks in a dedicated git worktree so the
  failure-path reset can never touch the dev's main checkout. Worth adding if the
  dev edits the same repo while runs are active.
- For a PC that will be OFF overnight, use `/night-run` (remote) instead.
```
