<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=9, reconfirm-count=2, content-hash=6870f672 -->
<!-- duplicate-checked -->
<!-- Searched backlog + done/ for "cargo", "pipe", "tail", "hang". 779 is comment-noise.sh's regex.
     Nothing covers a shell-command guard for piped test output. -->
# PreToolUse guard: reject piping a `cargo test` through tail/head/grep

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a `PreToolUse` guard that blocks a Bash/PowerShell command matching `cargo test` piped into
`tail`, `head`, or `grep`, with a message naming the alternative (run bare with
`run_in_background: true`, then grep the output file).

## Context

Second occurrence of the same 20-minutes-to-2-hours loss, by two different sessions, in a project
that already has a memory documenting it:

- **2026-08-19** (`claude_usage_in_taskbar` todo 692): `cargo test --test daemon_user_todos_e2e ...
  2>&1 | tail -40` produced 0 bytes for 2h17m. The spawned `cc-conductor-daemon.exe` child inherits
  the pipe's write end, so `tail` never sees EOF.
- **2026-08-25** (this session, a `/mega-todos` verify barrier): `cargo test --manifest-path
  src-tauri/Cargo.toml --lib 2>&1 | tail -25` hung ~23 minutes. Killed it, re-ran identical but
  unpiped, passed 1142/1142 in 236s. The kill also invalidated the build cache, so the retry
  rebuilt the whole dep tree (ring/rustls/iroh) - the real cost was well over the 23 minutes.

The second one is the interesting failure, and it is why a memory is not enough. A memory DID exist
and had been loaded. Its description read "Piped cargo **e2e** test hangs", so at the moment of
writing a `--lib` command it did not register as applying. A guard does not care how the operator
mentally classified the command.

## Approach

1. New hook in `hooks/`, wired as `PreToolUse` on `Bash`/`PowerShell` in `settings.json`, following
   the shape of the existing shell guards (`shell-content-write-guard.py` is the closest model -
   same "inspect the command string, block with an explanatory message" pattern).
2. Match: a command containing `cargo test` AND a pipe into `tail`/`head`/`grep`/`Select-Object`.
   Do NOT match `cargo build`/`cargo check` - those have no spawned-child problem and piping them is
   fine and common.
3. Message must name the fix, not just the ban: run bare with `run_in_background: true`, then
   `grep -E "^test result" <output-file>`.
4. Consider whether this should be repo-scoped. The mechanism (a test spawning a daemon that
   inherits the pipe) is not unique to `claude_usage_in_taskbar`, and the guard is cheap and easy to
   satisfy, so global is probably right - but check the hook's cwd is available so it CAN be scoped
   if a false positive shows up.
5. Add a `hooks/test_<name>.py` self-test so `ci/run_all.py` covers it, matching the other hooks.

## Acceptance

- `cargo test --lib 2>&1 | tail -25` is blocked with a message naming the background-run
  alternative.
- `cargo build 2>&1 | tail -5` is NOT blocked.
- `python ci/run_all.py` passes with the new self-test included.

## Notes

The corresponding project memory was widened in the same session to stop saying "e2e"
(`project_cargo_test_piped_hangs_on_spawned_daemon`). This todo is the enforcement half; the memory
alone has now demonstrably failed once.
