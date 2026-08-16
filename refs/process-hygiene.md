# Process Hygiene Reference

Detailed orphan-process defense and concurrency rules. CLAUDE.md has the short rules; this file has the full doctrine.

## Why this matters

Joe found 90+ orphan vitest processes from one session at 100% CPU and 90°C. The orphan issue, not concurrency itself, was what burned the CPU.

## Three-layer orphan defense

### Layer 1: subagent prompts that run tests/builds

Mandatory final step in the prompt:

> Run the project's orphan-check script (e.g. `pnpm check-orphans` if it exists, otherwise `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }`). If orphans remain, kill them with `Stop-Process -Id <PID> -Force` before reporting DONE.

### Layer 2: main-agent rule

After every subagent that ran Node commands completes, the main agent runs the same orphan check itself. If orphans are found, dispatch a one-shot cleanup subagent or kill them inline.

### Layer 3: optional Stop hook (recommended)

Configure a Claude Code Stop hook that runs the project's orphan-killer when the session ends. Acts as the last safety net.

## Orphan-check commands

**PowerShell (Windows):**
```powershell
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }
```

**Unix:**
```bash
pgrep node
```

**Kill orphans (Windows):**
```powershell
Stop-Process -Id <PID> -Force
```

## Concurrency cap (5)

Never run more than 5 Node-based commands concurrently:

- **turbo:** `--concurrency=5`
- **vitest:** `poolOptions.threads.maxThreads: 5` (or `pool: 'forks'` with `singleFork: true` for clean Windows exit)
- **pnpm:** `--workspace-concurrency=5`
- **Never** run `pnpm dev --parallel` outside of explicit dress-rehearsal use

Joe's hardware can handle 5 fine.

## Long-running dev servers

**Always launch them via the `/supervised-run` skill** (vite, `cargo tauri dev`, `next dev`, `flutter run`, backends, file watchers, etc.). The supervisor owns the process so there are no orphans, logs it centrally so the agent can read its output without a human pasting a terminal, and can spawn outside the agent's sandbox job (on Windows, a bare agent-shell launch is denied `CREATE_BREAKAWAY_FROM_JOB`, which is the real reason a long-lived server won't start under the agent directly). The skill falls back to a plain shell run only if the supervisor is unreachable.

If you ever bypass the supervisor: track the PID and ensure it terminates on session end / Ctrl-C / completion of the parent task.

## Secrets on the command line

A secret passed as a `--dart-define` or an env-prefix argument sits in that process's command line
for its whole lifetime, readable by anything that can enumerate processes. Prefer a file or a real
environment variable instead (2026-08-14, `revaire-mobile`: a live API key sat exposed this way in
an orphaned `flutter run`).

## Subagent commit handoff (READY_TO_COMMIT marker)

Subagents cannot invoke skills, so they must NEVER commit (the global rule covers the verbatim "stage only" dispatch sentence). For **background** subagents specifically: have them write a short `READY_TO_COMMIT.md` marker (or similar report-back doc) listing what they staged, so when the completion notification arrives the main agent knows there is staged work waiting and can run `/commit` against it.
