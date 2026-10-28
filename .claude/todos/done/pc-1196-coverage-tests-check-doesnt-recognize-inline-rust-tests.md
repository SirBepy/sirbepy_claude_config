<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1045 and 1138 are the same check but already-shipped (done/), different gaps - 1045 is about the client-repo owner list, 1138 taught the basename/path-segment heuristic to recognize verify/probe-style test FILE names. This is a distinct gap: a test living INSIDE the same .rs file as the code it covers (Rust's idiomatic #[cfg(test)] mod tests), not a separate test-file path at all, which no basename/path-segment heuristic can ever recognize. 1038 is code-check's exercise-test gate, a different script entirely. -->
# `coverage-tests-check` doesn't recognize inline Rust `#[cfg(test)] mod tests`

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/commit-pathspec.sh`'s `coverage-tests-check` should recognize a Rust file's own
inline `#[cfg(test)] mod tests` block as test coverage for that same file, instead of refusing
every commit that touches a `.rs` file with no separate `test_*`/`*_test.*` path in the pathspec.

## Context

Observed 2026-10-19 across a `windows_taskbar_widgets` session (Rust/Tauri repo): every single
commit that touched a `.rs` file needed `--force coverage-tests`, 6 times in one session
(`5c9f589`, `b63b74a`, `58b7721`, `1b4c5c8`, `974850e`, plus the version-bump commits that touched
`Cargo.toml`). Every one of those commits genuinely added or updated tests - they're just written
as an inline `#[cfg(test)] mod tests` block in the same file, the standard Rust convention, not a
separate `test_*`/`*_test.*`/`*.test.*`/`*.spec.*` file the check's basename/path-segment heuristic
(`skills/commit/SKILL.md`'s "Test-coverage check" paragraph, extended by todo 1138) can see.

This isn't specific to this one repo: any Rust project following the idiomatic inline-test
convention hits the same false refusal on every commit, which trains the habit of reflexively
reaching for `--force coverage-tests` without actually checking whether a test was added - exactly
the failure mode the gate exists to prevent.

## Approach

Teach `commit-pathspec.sh`'s coverage-tests-check to also pass when a `.rs` file in the pathspec
has a `#[cfg(test)]` (or `#[cfg(test)] mod tests`) block in its current working-tree content, not
just when a separate test-shaped path is present. A git-diff-aware version (did this commit's diff
touch content inside that block, not just anywhere in the file) would be stronger but a same-file
presence check is already a large improvement over refusing every Rust commit outright.

## Acceptance

- A commit touching only `src-tauri/src/some_file.rs`, which contains a `#[cfg(test)] mod tests`
  block with new/updated tests in the same diff, passes `coverage-tests-check` without
  `--force coverage-tests`.
- The existing behavior (refuse when a non-test source file changes with no test coverage at all)
  stays intact for a `.rs` file that has no `#[cfg(test)]` block.

## Notes

- Done by /loop-todos cycle 2 on 2026-10-23: coverage-tests-check passes a .rs file whose working-tree content has a line-anchored #[cfg(test)] (covers itself only); SKILL.md steps 6b and 8 name the case. Presence check, not a parse: a block-comment or raw-string occurrence also counts.
