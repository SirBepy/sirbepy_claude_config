<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1172 and 1163 are testing-floor hook bugs; this one is /e2e routing for the push gate -->
# /e2e: route a Flutter repo with a committed `e2e/run-all.js` to that suite

**Type:** skill-improvement
**Origin:** ai

## Goal

`/e2e` in a Flutter repo that ships its own committed suite (`e2e/run-all.js`) runs that suite as the push gate's e2e step, instead of falling through to `/flutter-e2e`'s hand-written scripted or plan-file modes.

## Context

- 2026-10-22, zng-admin todo 86: zng-admin now has a committed suite in `e2e/` (plain Node + `playwright` 1.61.1, `flows/flow-*.js`, `run-all.js`), the same layout as zng-app's `e2e/`.
- `skills/e2e/SKILL.md`'s Run-mode table maps any `pubspec.yaml` repo to `/flutter-e2e`. `/flutter-e2e` mentions zng-app's tracked suite (`node run-all.js`) only as a harness to reuse, not as "the suite to run". Neither skill says: when `e2e/run-all.js` exists, build the release bundle and run it.
- zng-admin works around this with a local-only line in its own `CLAUDE.md` ("E2E suite" section). zng-app has no such line, so a push gate there depends on the session noticing `e2e/README.md`.
- Related, separate: 1163 (the testing floor runs an `e2e/package.json` `test` script as a fast check). zng-admin's suite names its script `e2e`, not `test`, to stay clear of it until 1163 lands.

## Approach

Add a row (or a pre-check above the table) to `skills/e2e/SKILL.md`: a Flutter repo with `e2e/run-all.js` runs `e2e/README.md`'s documented command (release build with the repo's local env file, then `node run-all.js`), and reports its PASS/FAIL summary. Keep `/flutter-e2e` for repos without one.

## Acceptance

- `/e2e` in zng-admin and zng-app runs `node run-all.js` without project-specific CLAUDE.md hints.
- Repos with no committed suite still route to `/flutter-e2e` as today.
