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

For vite, fastify, etc.: track the PID and ensure it terminates on session end / Ctrl-C / completion of the parent task.
