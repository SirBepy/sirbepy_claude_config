<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1136 and 1139 (done) are the floor's node-check launcher failing; 357 (done) is a subagent's non-Node process escaping the orphan check. This is the floor's own sweep killing processes it does not own. -->
# testing-floor's node orphan sweep kills every live vitest on the machine, not just its own

**Type:** bug
**Origin:** ai
**Priority:** High

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

Found 2026-10-08 in cueline, where it is the most likely cause of cueline todo 52 ("vitest run
dies with exit 127 / -1 partway through the suite"):

- A backgrounded `node node_modules/vitest/vitest.mjs run` died at about 19:31:10, 58 s into it,
  with exit code 4294967295 (-1), no error on stderr, and no JSON report. Its stderr file was
  last written 19:31:09.
- The same session ended a turn that had edited source files right after a commit at 19:26:06.
  The floor hook therefore ran cueline's node check (`npm test`, typecheck plus a full vitest
  run) with `DEFAULT_TIMEOUT_SECONDS = 300`, and the sweep runs once that check returns. 19:26:30
  plus 300 s is about 19:31:30, matching the death to within seconds.
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
