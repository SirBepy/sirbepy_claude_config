<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# screenshot-helper.cjs hardcodes the same disposable npx playwright path todo 288 just fixed

**Type:** task
**Origin:** ai

## Goal

Point `skills/screenshot/screenshot-helper.cjs` at real playwright resolution instead of the
hash-pinned npx cache path, the same fix todo 288 landed for the two hubstaff scripts.

## Context

Surfaced by the builder agent that executed todo 288 during the 2026-08-13 `/auto-do-todos` run,
reported through the report-back channel rather than filed directly, per the rule todo 291 added to
`refs/delegation-doctrine.md` in that same run.

Line 1 of `skills/screenshot/screenshot-helper.cjs` requires playwright from
`_npx/e41f203b7505f1fb/node_modules/playwright`. That is a content-addressed npx cache directory:
the hash changes when the npx invocation changes, and `npm cache clean` or a cache eviction deletes
it outright. When it goes, every screenshot skill that calls this helper fails with a raw
`MODULE_NOT_FOUND` rather than an actionable message.

This was out of scope twice over, which is why it survived: todo 288 named only
`scripts/hs_preflight.cjs` and `scripts/hs_weekshot.cjs`, and todo 287's screenshot work was about
the per-session subfolder rule, not module resolution.

The blast radius is wider than the hubstaff scripts were. `screenshot-helper.cjs` is the shared
entry point for `/screenshot`, `/mockup`, and the `/flutter-e2e` helpers.

## Approach

`skills/clockify-reconciliator/scripts/hs_common.cjs` already has the solved version of this
problem: `getChromium()` tries normal `require('playwright')` first, falls back to scanning
`_npx/*/node_modules/playwright` for the newest match, and throws a message naming the two fix
commands when neither resolves.

Decide between sharing that function and copying it. Sharing means `skills/screenshot/` takes a
dependency on a path inside `skills/clockify-reconciliator/`, which is a bad direction for a
general-purpose helper to depend on a specific one. Lifting `getChromium()` into a small shared
module both can require is the cleaner shape, but it is a third file for one function. Copying is
the third option and the reason this defect exists in two places already.

## Acceptance

- No hash-pinned `_npx/<hash>/` path remains anywhere under `skills/`.
- With the npx cache hidden, the helper fails with the actionable message naming the fix commands,
  not a raw `MODULE_NOT_FOUND`. Verified by actually running it, not by reading the code.
- `/screenshot` still captures a real screenshot after the change.

## Notes

- Filed by the orchestrator of the 2026-08-13 `/auto-do-todos` run from a builder's out-of-scope
  report, not by the dev.

- Renumbered 293 -> 295 on 2026-08-13 (todo 286): id 293 was claimed by two different files. The other file kept it because it was filed earlier. Any older reference to todo 293 may mean this one.
