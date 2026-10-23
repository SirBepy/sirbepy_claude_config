<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1160 is the testing-floor orphan sweep; no other backlog file mentions the floor running a server-backed e2e package -->
# testing-floor-guard runs mc_plugins_tag's e2e/ bot suite as a "fast check"

**Type:** hook-bug
**Origin:** ai

## Goal
The Stop-hook testing floor never runs a slow, server-backed e2e suite as a per-turn fast check.

## Context
- mc_plugins_tag session 726c, 2026-10-08: the session edited only Java under `dragonballs/` and a
  scratch script in `C:\tmp`. The floor still ran `npm test` in `e2e/` (its `package.json` has
  `"test": "node run-all.mjs"`, the full Mineflayer bot suite) and blocked the turn with
  `connect ECONNREFUSED 127.0.0.1:25575`, because no e2e server was running.
- `_testing_floor_lib.py` adds a "node" row for any `package.json` whose `scripts.test` isn't npm's
  placeholder, so a package whose tests need a live server reads as a fast check. CLAUDE.md's floor
  keeps e2e suites out of the per-change floor.
- The documented escape hatches are global: the env var can't be set from inside a turn, and
  `hooks/.testing-floor-skip` turns the guard off for every concurrent session.
- Recurrence folded in from 1221 (archived as a duplicate, 2026-10-23): mc_plugins_tag, 2026-10-22,
  after a commit that edited `e2e/almanac.mjs` the floor reported `node check failed (exit 1)` with
  `ECONNREFUSED 127.0.0.1:25577` (the e2e server's RCON port, deliberately stopped) on attempts 1/3,
  2/3 and 3/3, releasing only at the cap. Same root cause: the node row runs `npm test` in `e2e/`
  (`_testing_floor_lib.py:350-362` adds the row, `:485-512` runs it), not the edited file. 1221's
  extra acceptance worth keeping: a real syntax error in an edited `e2e/*.mjs` should still fail
  the floor, so an opt-out could fall back to `node --check <file>` rather than skipping outright.

## Done when
- A package can opt out (e.g. a marker file, or a `testing-floor: skip` field in package.json), or
  the floor only runs the node row for packages under directories the turn actually edited.
- mc_plugins_tag's `e2e/` no longer blocks a Java-only turn.
