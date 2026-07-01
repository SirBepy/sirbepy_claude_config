---
name: schedule-once
description: Triggers on /schedule-once only. Schedules a SINGLE future run of a Claude prompt (or a raw shell command) on THIS machine via Windows Task Scheduler, as a self-deleting one-time task. The local, one-shot counterpart to the cloud /schedule and the recurring /cron-run. PC must be on and logged in at fire time; Claude Code itself need not be open. Also supports list and cancel.
argument-hint: "<prompt> at <time> [with <model>] [<effort> effort] | --shell <cmd> at <time> | list | cancel <id|all>"
---

# /schedule-once

> Fire one prompt (or command) once, later, on this machine. No cloud, no recurrence.

Local sibling of the cloud `/schedule` (which runs on Anthropic's infra) and `/cron-run` (which runs a *recurring* local queue). Use `/schedule-once` for "run this one thing at this one time on my PC, then forget it."

## When to use which

- **`/schedule-once`** — one prompt/command, once, locally. Self-deletes after firing.
- **`/cron-run`** — recurring local overnight queue grinding plan files. Not for one-shots.
- **`/schedule`** — cloud routines (PC can be OFF). Use when the machine won't be on.

## How it works

A single-fire Windows Scheduled Task under task path `\ClaudeOnce\`. At schedule time the registrar writes a job sidecar (`%LOCALAPPDATA%\ClaudeScheduleOnce\jobs\<task>.json`) holding the prompt/command, working dir, and resolved `claude.exe`. When the task fires, `run-once.ps1` reads that sidecar, runs the job (logging to `%LOCALAPPDATA%\ClaudeScheduleOnce\logs\<task>.log`), then unregisters its own task and deletes the sidecar. The sidecar indirection means an arbitrary prompt (quotes, slashes, newlines) never has to be escaped into a Task Scheduler argument string.

**Caveat (state it to Joe):** the PC must be powered on and the user logged in at fire time. If asleep, `-StartWhenAvailable` runs it on next wake. If powered off, it runs at next logon. For a guarantee the machine will be on, use `/schedule` (cloud) instead.

## Argument parsing

Free-form, tokens in any order. Determine the subcommand first:

- Contains `list` (and nothing schedulable) → **List**.
- Starts with `cancel` / `stop` → **Cancel** (`cancel all` or `cancel <task-name-or-slug>`).
- Otherwise → **Schedule**. Split into the payload and the time:
  - **Time**: the `at <when>` / `in <duration>` / trailing time phrase. Accept "3pm", "15:30", "in 2 hours", "in 90m", "tomorrow 9am", "jun 8 14:00", etc.
  - **Payload**: everything else. If it begins with `/` or reads like a Claude instruction → a **prompt**. If the user wrote `--shell <cmd>` (or "run command"/"shell:") → a **raw PowerShell command**.
  - **Perm mode** (prompt jobs): default `acceptEdits`. If the user says "yolo"/"bypass"/"no prompts" → `bypassPermissions`. If "plan only" → `plan`.
  - **Model** (prompt jobs, optional): if the user names one ("with opus", "use sonnet", "model fable", or a full id like `claude-opus-4-8`) → pass it through. Omitted = the machine's default model.
  - **Effort** (prompt jobs, optional): if the user names a level ("high effort", "max effort", one of low/medium/high/xhigh/max) → pass it through. Omitted = default.

If the time is missing or ambiguous, that is the ONE thing worth a quick `AskUserQuestion` (you cannot safely guess when to fire). Everything else: pick a sensible default and proceed.

## Schedule

1. **Resolve the time to an absolute datetime.** Get "now" from `Get-Date` (the machine clock is authoritative, not the session date). Convert the user's phrase to a concrete `yyyy-MM-dd HH:mm:ss`. For a bare clock time already past today, roll to tomorrow. Confirm the resolved instant back to the user in your final message.
2. **Capture the working dir** = the current project folder (cwd). Jobs run there.
3. **Register it** by calling the registrar (literal path — do not build it from `$env:` so it does not trigger a permission prompt). One command, no chaining:

   Prompt job (add `-Model <alias>` and/or `-Effort <level>` only when the user asked for them; omit otherwise):
   ```powershell
   & "C:\Users\tecno\.claude\skills\schedule-once\schedule-once.ps1" -At "<yyyy-MM-dd HH:mm:ss>" -WorkDir "<cwd>" -PermMode acceptEdits -Model opus -Effort high -Prompt '<the prompt>'
   ```
   Shell job:
   ```powershell
   & "C:\Users\tecno\.claude\skills\schedule-once\schedule-once.ps1" -At "<yyyy-MM-dd HH:mm:ss>" -WorkDir "<cwd>" -Shell '<the command>'
   ```
   - **Quote the payload with SINGLE quotes** so PowerShell does not interpolate `$` or backticks. If the payload itself contains a single quote, double it (`''`) per PowerShell escaping.
   - The script validates the time is in the future, resolves `claude.exe`, writes the sidecar, registers the task, and prints `TaskName / FiresAt / Mode / WorkDir / LogFile / JobFile`.
4. **Report** the task name, exact fire time, mode, and the log file path so Joe can check the result later. Mention it self-deletes after firing and that the PC must be on/logged in.

## List

```powershell
Get-ScheduledTask -TaskPath '\ClaudeOnce\*' -ErrorAction SilentlyContinue | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; [PSCustomObject]@{ Task = $_.TaskName; State = $_.State; NextRun = $i.NextRunTime } } | Format-Table -AutoSize
```

If none, say "no one-time tasks scheduled." To inspect what a pending task will do, read its sidecar: `Get-Content "$env:LOCALAPPDATA\ClaudeScheduleOnce\jobs\<task>.json"`.

## Cancel

- **All:**
  ```powershell
  Get-ScheduledTask -TaskPath '\ClaudeOnce\*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
  ```
  then clear sidecars:
  ```powershell
  Remove-Item "$env:LOCALAPPDATA\ClaudeScheduleOnce\jobs\*.json" -Force -ErrorAction SilentlyContinue
  ```
- **One** (full task name, e.g. `ClaudeOnce_my-slug_20260607-153000`):
  ```powershell
  Unregister-ScheduledTask -TaskName "<task-name>" -TaskPath '\ClaudeOnce\' -Confirm:$false
  ```
  then remove its sidecar:
  ```powershell
  Remove-Item "$env:LOCALAPPDATA\ClaudeScheduleOnce\jobs\<task-name>.json" -Force -ErrorAction SilentlyContinue
  ```
  If the user gave a partial slug, run List first and match it to the full task name.

## Notes

- Logs persist at `%LOCALAPPDATA%\ClaudeScheduleOnce\logs\<task>.log` even after the task self-deletes, so Joe can review what happened.
- Prompt jobs run headless via `claude -p "<prompt>" --permission-mode <mode> [--model <m>] [--effort <e>] --no-session-persistence` — no chat state is inherited; write self-contained prompts. `--model`/`--effort` are appended only when set at schedule time (older sidecars without those fields run unchanged).
- One command per call; never chain with `;`/`&&`/`|`. PowerShell on Windows.
- This skill schedules on the local machine only. It never touches the cloud or the network.
