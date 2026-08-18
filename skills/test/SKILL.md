---
name: test
description: Runs a project's unit and e2e suites with the stack inferred from the repo rather than named.
disable-model-invocation: true
argument-hint: "[unit|e2e] [free-form scope - a file, a flow, a test-plan path, or 'full']"
---

# /test

> One verb. Point it at a repo, it works out the stack and runs the right suites.

**`/test` typed by Joe means unit AND e2e.** That is the whole difference between this skill and
the automatic testing floor in `CLAUDE.md`, which stays fast-checks-only and never runs e2e on its
own. Do not blur the two: an explicit `/test` is allowed to be slow, the pre-done floor is not.

Free-form arguments narrow the run - `unit`, `e2e`, a file path, a flow description, a test-plan
`.md` path, `full`. No arguments means both halves, whole project.

## Step 1 - Detect the stack

Deterministic marker lookup from the repo root, never a guess about what the project "feels like".
A repo can match more than one row (a Tauri app matches Rust *and* Node); run every row it matches.

| Marker at repo root | Stack | Unit | E2E |
|---|---|---|---|
| `pubspec.yaml` with a `flutter:` dependency | Flutter | `fvm flutter test` | `/flutter-e2e` |
| `package.json` | Node / web | resolved from `scripts.test` | `snippets/test-e2e.md` policy |
| `Cargo.toml` or `src-tauri/Cargo.toml` | Rust / Tauri | `cargo test --lib` | none exists - say so |
| `test.project.json`, `*.rbxlx`, or a `testing/wally.toml` | Roblox / Luau | `/jest-lua run` | none exists - say so |
| none of the above | scripts / docs repo | see "Scripts repo" below | none |

State the detected stack(s) and the exact commands in one line before running anything. If nothing
matches and the repo has no runnable checks at all, say that plainly - do not invent a suite.

## Step 2 - Confirm the working directory FIRST

Every command runs from the target repo root. A bare `flutter test <absolute path into another
repo>` resolves package imports from the CURRENT repo and fails with phantom `Undefined name`
errors - this happened for real and produced todo 98's guard. Same class of trap for `cargo` in a
workspace: pass `--manifest-path src-tauri/Cargo.toml` rather than relying on cwd inference.

## Step 3 - Unit

- **Flutter:** `fvm flutter test`. **Its exit code is a lie** - `fvm flutter test` returns 0 on a
  genuinely failing run (confirmed 2026-08-13, same test returned 1 through the pinned
  `flutter.bat`). Read stdout for the real verdict; never branch on `$LASTEXITCODE` here. Full
  writeup: `skills/flutter-bump/references/fvm-landmines.md` bug 3.
- **Node / web:** read `scripts.test` instead of assuming vitest or jest. Pick the package manager
  from the `packageManager` field if pinned, else the lockfile - a bare `npm`/`yarn` in a pinned
  repo is blocked by the corepack guard and a global Yarn 1 once rewrote a Yarn 4 lockfile. Cap
  concurrency at 5 (`--maxThreads=5` / `--workspace-concurrency=5`), then check for orphans per
  `refs/process-hygiene.md` before reporting.
- **Rust / Tauri:** `cargo test --lib` alone, which already compiles the lib. Do NOT stack it with
  `cargo check` and `cargo build` - the three emit different artifact sets, so serially they cost
  roughly three full builds, not one plus increments. Any `check`/`build` you do add takes
  `--all-targets`, or `#[cfg(test)]`-only imports report as unused. **If `/supervised-run` has a
  `cargo tauri dev` entry up, stop it first** - the running app holds a lock on the target exe and
  the test fails with "Access is denied (os error 5)". Restart it after.
- **Roblox / Luau:** hand off to `/jest-lua run`; it already owns `scripts/check.sh` and the
  `run-in-roblox` fallback.
- **Scripts repo** (`~/.claude` itself is one): `python <each hooks/test_*.py>`, `python -m
  py_compile` over changed `hooks/*.py`, `node --check` over changed `.mjs`/`.cjs`, and
  `[System.Management.Automation.Language.Parser]::ParseFile` over changed `.ps1`.

## Step 4 - E2E

Delegate, never reimplement. The tree-wide "fold everything into one router" idea scored 3/10 across
two rating panels; these specialist skills stay specialist.

- **Flutter web** -> `/flutter-e2e`. A test-plan `.md` path in the arguments selects its plan-file
  mode; anything else selects scripted mode.
- **Node / web** -> only if the project imports `snippets/test-e2e.md` or has a Playwright config.
  Follow that snippet exactly: affected-specs for a routine run, full suite when asked, dispatched
  to a **background subagent** (`model: 'sonnet'`) that attaches to an already-serving dev port
  rather than starting a second one, and returns pass/fail plus the first error line per failing
  spec - never raw logs into this context.
- **Rust / Tauri, Roblox / Luau** -> no e2e path exists in this tree. Report that instead of
  improvising one.

If `/test` was invoked with `unit`, skip this step. If e2e genuinely cannot run (no config, no dev
server, headed-only), say which and why - a skipped e2e is never silent.

## Step 5 - Report

One block, no log dumps:

- Detected stack(s) and the exact commands run.
- Per suite: pass/fail plus counts. Per failing test: its name and first error line only.
- Anything skipped, and why.
- Orphan-process check result for any Node or dev-server run.

A failing suite is the headline, not a footnote. Never report "done" over a red run.

## Acceptance checklist

- [ ] Stack came from marker files, and every matching row ran - not just the first
- [ ] Commands ran from the target repo root
- [ ] Flutter verdict read from stdout, not from the exit code
- [ ] Supervised Tauri dev entry stopped before `cargo test`, restarted after
- [ ] E2E delegated to the owning skill, or explicitly reported as unavailable
- [ ] Node runs capped at concurrency 5 and orphan-checked afterwards

## Related

- `CLAUDE.md` "Testing & verification floor" - the automatic pre-done checks. Separate from this
  skill on purpose, and stays fast-only.
- `~/.claude/snippets/test-e2e.md` - the per-project e2e opt-in policy.
- `~/.claude/skills/flutter-e2e/SKILL.md`, `~/.claude/skills/jest-lua/SKILL.md` - the delegates.
- `~/.claude/refs/process-hygiene.md` - orphan rules and the concurrency cap.
