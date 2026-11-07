<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo covers adding the CI unit-test job to the push gate -->
# Push gate runs the repo's CI unit-test job locally

**Type:** task
**Origin:** dev
**Summary:** The pre-push gate (code-check + e2e) also runs the same unit tests CI runs, so a red CI test is found before the push, not after.

## Goal
`/commit`'s Pre-push gate step runs the repo's CI test command (for claude_usage_in_taskbar: `cargo test --manifest-path src-tauri/Cargo.toml --lib`) and treats a failure like a red gate.

## Context
Release 0.2.146 (2026-11-06) passed code-check and the wdio sweep, then CI's `test` job failed on `mcp::dispatch::tests::send_message_forwards_every_validated_schema_property` (`visuals` never relayed to the daemon). The fix, re-push and re-watch cost a full extra CI round. The local gate never ran `cargo test --lib`. A cold run took 7.5 min, a warm run is much shorter.

## Approach
Detect the CI test command from `.github/workflows/*.yml` (the job named `test`) or a per-repo setting in `ship-config.py`, and run it in the gate before `mark`. Per-repo, not hardcoded to Rust. Run it unpiped and in the background (cargo-test-pipe-guard).

## Acceptance
A push whose range breaks a unit test CI runs is blocked locally with the failing test named.
