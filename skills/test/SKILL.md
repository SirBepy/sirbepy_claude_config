---
name: test
description: Runs a project's fast checks - unit tests plus whatever typecheck/lint/build the detected command already covers - with the stack inferred from the repo rather than named.
disable-model-invocation: true
argument-hint: "[free-form scope - a file, a package, or 'full']"
---

# /test

> One verb. Point it at a repo, it works out the stack and runs the fast checks.

**`/test` typed by Joe means the fast-checks floor.** This skill is what `CLAUDE.md`'s testing
floor points to when it says "run every fast check the project has" - typing `/test` runs it
explicitly, stack inferred, with a real report instead of an ad-hoc command per project. Browser-
driven end-to-end runs live in `/e2e` now, a separate command that delegates rather than living
here.

Free-form arguments narrow the run - a file path, a package name, `full`. No arguments means the
whole project.

## Step 1 - Detect the stack

Deterministic marker lookup from the repo root, never a guess about what the project "feels like".
A repo can match more than one row (a Tauri app matches Rust *and* Node); run every row it matches.

| Marker at repo root | Stack | Command |
|---|---|---|
| `pubspec.yaml` with a `flutter:` dependency | Flutter | `fvm flutter test` |
| `package.json` | Node / web | resolved from `scripts.test` |
| `Cargo.toml` or `src-tauri/Cargo.toml` | Rust / Tauri | `cargo test --lib` |
| `test.project.json`, `*.rbxlx`, or a `testing/wally.toml` | Roblox / Luau | `/jest-lua run` |
| none of the above | scripts / docs repo | see "Scripts repo" below |

State the detected stack(s) and the exact commands in one line before running anything. If nothing
matches and the repo has no runnable checks at all, say that plainly - do not invent a suite.

## Step 2 - Confirm the working directory FIRST

Every command runs from the target repo root. A bare `flutter test <absolute path into another
repo>` resolves package imports from the CURRENT repo and fails with phantom `Undefined name`
errors - this happened for real and produced todo 98's guard. Same class of trap for `cargo` in a
workspace: pass `--manifest-path src-tauri/Cargo.toml` rather than relying on cwd inference.

## Step 3 - Run the fast checks

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

## Step 4 - Report

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
- [ ] Node runs capped at concurrency 5 and orphan-checked afterwards

## Related

- `CLAUDE.md` "Testing & verification floor" - the automatic pre-done checks this skill runs
  explicitly on demand. Stays fast-only, same as the floor.
- `~/.claude/skills/e2e/SKILL.md` - browser/app-driven end-to-end runs and the design-fidelity
  render-and-diff mode. Separate command on purpose; ask for `/e2e`, not `/test e2e`.
- `~/.claude/refs/process-hygiene.md` - orphan rules and the concurrency cap.
