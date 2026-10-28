<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1136 and 1139 (done) are the floor's node-check launcher failing; 357 (done) is a subagent's non-Node process escaping the orphan check. This is the floor's own sweep killing processes it does not own. -->
# testing-floor's node orphan sweep kills every live vitest on the machine, not just its own

**Type:** bug
**Origin:** ai
**Priority:** High
**Summary:** The end-of-turn testing check cleans up only the Node processes it started and never kills another session's running vitest or turbo.

## Why

Found 2026-10-08 in cueline: a backgrounded vitest run died mid-suite with no error, and the sweep matches every vitest process on the machine. Cause is plausible but unverified.

## Goal

The Stop-hook testing floor cleans up only the Node processes its own check started, and never
kills a vitest, turbo or tinypool process another session (or the same session's backgrounded
command) is legitimately running.

## Context

`hooks/_testing_floor_lib.py` `run_checks()` calls `sweep_node_orphans()` after every node-stack
check (line ~594). The sweep runs `Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' } | ForEach-Object { Stop-Process
-Id $_.ProcessId -Force }` (line ~540). That matches every such process on the machine, whoever
owns it.

Found 2026-10-08 in cueline, where it is a likely (UNVERIFIED) cause of cueline todo 52 ("vitest run
dies with exit 127 / -1 partway through the suite"):

- A backgrounded `node node_modules/vitest/vitest.mjs run` died at about 19:31:10, 58 s into it,
  with exit code 4294967295 (-1), no error on stderr, and no JSON report. Its stderr file was
  last written 19:31:09.
- The same session ended a turn that had edited source files shortly after a commit at
  19:26:06 (exact turn-end time not recorded). The floor hook therefore ran cueline's node check
  (`npm test`, typecheck plus a full vitest run) with `DEFAULT_TIMEOUT_SECONDS = 300`, and the
  sweep runs once that check returns, roughly 19:31:06-19:31:40. The death fits only if the turn
  ended within about 4 s of the commit, so this timing is suggestive, not proof (UNVERIFIED); a
  sweep from another session's hook would look identical. What IS verified from the code: the
  sweep's filter is machine-wide and does not check process ownership.
- The other two runs in the same batch, and an earlier 775 s run, finished normally. UNVERIFIED
  that no source-editing turn ended while those ran (likely, from the session's own timeline).
  The earlier deaths reported in cueline todo 52 (exit 127 through npx/Git Bash, "about 100 s"
  or "about 5 min" in) fit the same pattern.
- UNVERIFIED: a 45-minute idle node canary whose command line contains `vitest-canary
  tinypool-canary` was left running in cueline to catch the next sweep; its result was not in yet
  when this todo was filed.

Collateral: any concurrent session's vitest dies the same way, which would also explain peers
reporting suites that "die partway" with no failing test.

## Approach

1. Scope the sweep to the check's own process tree: kill only processes whose parent chain leads
   back to the pid the check launched (or run the check in a Windows job object and terminate
   the job).
2. Alternatively, snapshot matching pids before the check runs and only kill ones that appeared
   during it and descend from it.
3. Add a test in `hooks/test_testing_floor_guard.py` that a pre-existing matching process
   survives the sweep.

## Acceptance

- A `vitest run` started before a floor-hook node check is still alive after the hook finishes.
- Processes the check itself spawned are still cleaned up.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
