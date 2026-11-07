<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: a new measurement about where a parallel builder's scratch cargo target goes; no existing todo covers it -->
# Builder preamble's scratch cargo target advice costs parallel lanes about 40 minutes a link

**Type:** skill-improvement
**Origin:** ai
**Summary:** `refs/builder-preamble.md` sends a private cargo target to `D:\cargo-target\<name>`, and on that spinning disk parallel lanes spend most of their time linking.

## Why

Measured 2026-11-05 on the subchats build in `claude_usage_in_taskbar`:
- Private target on `D:` with full debug info: `rust-lld` took about 44 minutes to link the lib test binary with 3-4 lanes linking, and two runs died at the 30 minute cap.
- `$env:CARGO_TARGET_DIR='C:\Users\tecno\cargo-scratch\<name>'; $env:CARGO_PROFILE_DEV_DEBUG='line-tables-only'`, in a brand-new dir, with other lanes running: `cargo test --lib` compiled in 2m 24s.

The disk and the debug info were changed together, so which matters more is unmeasured.

## Context

`refs/builder-preamble.md` says: "put it under `D:\cargo-target\<name>`, the HDD the global `~/.cargo/config.toml` already builds into. Not `$env:TEMP` or an in-repo path: both sit on the C: SSD". The reason is a 2026-10-05 scan that found 23 GB of leaked scratch targets on C:, and that concern is real: each target ran about 25 GB here, and C: free space fell from 283 GB to 156 GB during the run. Those dirs were removed afterwards. `D:\cargo-target\` also blocks removal, since a shell command naming it trips the removal guard.

Project memory: `project_parallel_lanes_no_cargo_shared_target_lock` in that repo.

## Approach

Change the preamble's paragraph: a parallel lane's scratch target goes under `C:\Users\tecno\cargo-scratch\<name>` (not a drive-root child) with `CARGO_PROFILE_DEV_DEBUG=line-tables-only`, and the orchestrator removes the dirs when the run ends. Check `/mega-todos` and `refs/delegation-doctrine.md` for the same advice, and `/disk-doctor` for whether it knows that folder. Measure debug info alone on D: first if the leak risk argues for staying on D:.

## Done when

The preamble and any sibling doc give one measured recommendation, and `/disk-doctor` reports leftover scratch targets.


## Notes

- Decided (triage 2026-11-07): default CARGO_PROFILE_DEV_DEBUG=line-tables-only; C: cargo-scratch only for 2 or fewer lanes (D:\cargo-target for 3+), orchestrator cleans up; the 30-minute disk-vs-debug-info measurement skipped. refs/builder-preamble.md paragraph rewritten; windows.md line on scratch targets now names C:\Users\tecno\cargo-scratch so /disk-doctor lists leftovers. refs/delegation-doctrine.md and skills/mega-todos carry no cargo-target advice (grep), and are outside this lane anyway. Doc-only, no test applies (hooks/test_dispatch_preamble_guard.py still passes).