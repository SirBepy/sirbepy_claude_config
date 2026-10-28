<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /e2e skill's Mode A table has no row for a wdio-driven Tauri desktop app

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a row to `~/.claude/skills/e2e/SKILL.md`'s Mode A delegate table for a WebdriverIO-driven
Tauri (or other native-webview) desktop app, so the skill stops falling through to "anything else"
for a stack that actually has a scripted, documented e2e suite.

## Context

Hit during a `/commit pushnbump` in `claude_usage_in_taskbar` (2026-10-19). That project's real
e2e suite is wdio (`package.json`'s `test:e2e*` scripts, `scripts/wdio-sweep.ps1` - a full
release-gate sweep with free/billed spec tiers, headless dock via server_supervisor, per-spec
verdicts), not Playwright-app-e2e. `/e2e`'s Mode A table
(`~/.claude/skills/e2e/SKILL.md`) only recognizes: Flutter (`pubspec.yaml`), Roblox/Luau
(`test.project.json`/`*.rbxlx`), Android/Gradle (`gradlew`), and Node/web with a Playwright config
or `snippets/test-e2e.md` import. None of those rows match a wdio-based desktop app, so the table
falls to its last row: "anything else ... no scripted e2e path exists - ask ... and drive/inspect
the real system by hand."

That fallback is wrong here specifically because a scripted path DOES exist - `/commit`'s own
Pre-push gate (step 2) and `CLAUDE.md`'s Commands section both point at `wdio-sweep.ps1` as the
project's intended release-gate e2e step. The session had to recognize this from the project's own
`CLAUDE.md` rather than from `/e2e` itself, which is exactly the gap: a cold session without that
context would follow `/e2e`'s literal table, conclude "no suite", and silently skip real e2e
coverage that was sitting right there.

`/commit`'s own Pre-push gate step 2 also leans on this same gap: "No suite means `/e2e`'s
Run-mode table matches only its 'anything else' row" - so a mis-detection in `/e2e` cascades into
a wrong "personal repo, skip e2e" branch in `/commit` too, even when a real suite exists.

## Approach

Add a `package.json` + `wdio.conf.js` (or equivalent `@wdio/cli` devDependency) row to the Mode A
table, delegating to the project's own documented e2e npm script / wrapper script (read the
project's `CLAUDE.md` Commands section for the exact command, same as the Flutter row defers to
`/flutter-e2e`). Consider whether this warrants a dedicated `/wdio-e2e`-style sub-skill the way
Flutter and Roblox get one, or whether "run the project's own documented wdio wrapper, per its
CLAUDE.md" is enough text inline - judgment call for whoever picks this up.

## Acceptance

`/e2e`'s Mode A table has a row that correctly routes a wdio-based desktop-app project to its real
suite instead of the "anything else" fallback, verified by re-reading the table against
`claude_usage_in_taskbar`'s actual stack.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): e2e Mode A table has a wdio row (wdio.conf.* or @wdio/cli) delegating to the project's documented e2e script; Rust/Tauri removed from the anything-else row.
