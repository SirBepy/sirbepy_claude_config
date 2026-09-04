<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Searched this backlog + done/ for "cargo", "pipe", "tail", "buffer". Nothing covers a shell
     guard for it. The rule exists in two places already (a claude_usage_in_taskbar project memory
     and global CLAUDE.md's never-buffer-streaming-output bullet) and is still being broken, which
     is what makes this an enforcement gap rather than a documentation one. -->
# PreToolUse guard: reject piping a long-running cargo/build command through tail or head

**Type:** skill-improvement
**Origin:** ai

## Goal

Make "never pipe a cargo run through `tail`/`head`" mechanically enforced instead of a rule that
each session has to remember.

## Context

Broken again on 2026-09-02 in `claude_usage_in_taskbar`, twice in one session, by an instance that
had the rule available both ways:

- `cargo build --manifest-path src-tauri/Cargo.toml 2>&1 | tail -5` - no output for ~30 minutes, so
  there was no way to tell a live build from a hung one. Breaks global CLAUDE.md's "Never buffer
  streaming build output - hides hangs".
- `cargo test --manifest-path src-tauri/Cargo.toml --lib 2>&1 | tail -6` - the documented
  pipe/EOF trap. The project memory `project_cargo_test_piped_hangs_on_spawned_daemon` describes
  this exact failure (a spawned daemon inherits the pipe's write end, so `tail` never sees EOF).
  The `--lib` half eventually flushed, but the chained `--test export_types` half never printed its
  verdict at all and had to be re-run bare.

Both are the same shape: a long-running build/test command whose output is swallowed by a
line-limiting filter. Rules alone have not held, across multiple sessions.

## Approach

Extend the existing shell-guard hook family (`hooks/shell-content-write-guard.py` is the closest
precedent for shape - a `PreToolUse` hook that inspects the command string and rejects with an
explanatory message naming the alternative).

Match: a command containing `cargo` with `build`/`test`/`check`/`clippy`, piped into `tail`,
`head`, or a bare `grep` with no `--line-buffered`. Reject with: run it bare with
`run_in_background: true` and read the output file, or add `--line-buffered` for grep.

Deliberately NOT matched, or the guard will be turned off:

- a pipe on a command that is not cargo (`git log | tail` is fine)
- `grep --line-buffered`, which flushes per line
- reading an already-finished output FILE (`tail -20 <path>`), which is the correct pattern the
  guard should be steering toward

## Acceptance

- `cargo test --manifest-path src-tauri/Cargo.toml --lib 2>&1 | tail -6` is rejected with a message
  naming the background-run alternative.
- `tail -20 /tmp/some-build.output` and `git log --oneline | head -5` both still run.
- `python ci/run_all.py` green (the hook needs its own `hooks/test_*.py` suite, per this repo's
  convention).

## Notes

- Completed in wave 2, commit b71e365: the build, check and clippy subcommands were appended to CARGO_SUBCOMMANDS, with the matched subcommand threaded through so the block message names it. 27 cases pass.
