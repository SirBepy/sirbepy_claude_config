<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `/test` Rust row does not say what to do when `cargo test --lib` outlasts the 10 minute tool cap

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/test/SKILL.md` tells a session how to run a Rust lib test whose compile alone can exceed the Bash/PowerShell tool's 600000 ms ceiling, so it does not burn an hour re-launching a job the harness keeps killing.

## Context

2026-10-23, `claude_usage_in_taskbar` (shared checkout, several concurrent chats, one shared cargo target dir). `cargo test --manifest-path src-tauri/Cargo.toml --lib`, launched with `run_in_background: true` and the maximum `timeout`, was reported as "stopped after reaching its background time limit" six times in a row. Each attempt first waited on the target-dir lock behind another chat's cargo build, then recompiled the lib test binary (another chat's edit in between invalidated it), and that compile is itself close to ten minutes. The harness note says not to restart a job that already had the longest timeout, which leaves no instruction for a job that legitimately needs longer.

What worked: starting cargo detached so no tool cap applies, then watching its log with `Monitor`:

`Start-Process -FilePath cargo -ArgumentList test,--manifest-path,src-tauri/Cargo.toml,--lib -WorkingDirectory <repo> -RedirectStandardOutput <log> -RedirectStandardError <log2> -WindowStyle Hidden -PassThru`, then a `Monitor` loop that greps the log for `test result` and also checks the pid is alive, so a crash cannot look like "still running". Result: `test result: ok. 2054 passed; 0 failed; 4 ignored ... finished in 692.41s`.

`SKILL.md`'s Rust bullet (Step 3) currently only says to run `cargo test --lib` alone and to stop a supervised dev entry first. It is silent on duration, the lock, and the output-pipe guard (`hooks/cargo-test-pipe-guard.py` blocks any `| tail` style pipe, which is why the redirect-to-file form is the right one).

## Approach

Add two or three sentences to the Rust bullet in `skills/test/SKILL.md`: when other chats share the checkout or the lib-test compile may exceed the tool cap, start the run detached with output redirected to files and watch it with `Monitor`, never piped; a harness "stopped at the time limit" note on a cargo run means contention or a long compile, not a hang, so switch to the detached form instead of re-launching the same capped job. Keep it within the instruction token budget (`ci/check_instruction_budget.py`).

Rejected: raising the tool's own cap (not configurable from a skill), and a private `CARGO_TARGET_DIR` per session (recompiles every dependency from scratch, slower than waiting on the lock).

## Acceptance

- `skills/test/SKILL.md` carries the detached-run recipe and the "stopped at the limit is not a hang" line.
- `python ci/run_all.py` passes, including the instruction token budget.

## Notes

- skills/test/SKILL.md's Rust bullet now carries the detached Start-Process + Monitor recipe (log redirect, pid liveness, no pipe) and says a cargo time-limit stop is contention or a long compile, not a hang. Instruction budget check PASS.
