<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1080 wrote the prose rule; 1192 is an unrelated commit-pathspec path bug; this adds the enforcement -->
# Hook-enforce /commit's "never pipe commit-pathspec.sh output" rule

**Type:** skill-improvement
**Origin:** ai
**Summary:** A command that pipes commit-pathspec.sh output into a filter without pipefail is denied before it runs.

## Why

On 2026-10-22 Claude piped the script into tail right after reading the rule against it; a refused commit would have looked like success. The rule is prose only today.

## Goal

A Bash call that pipes `commit-pathspec.sh` output into a filter without `set -o pipefail` is denied before it runs, the same way `hooks/cargo-test-pipe-guard.py` handles `cargo test`.

## Context

- `skills/commit/SKILL.md` step 8 says: "**Never pipe this script's output** (`| tail`, `| head`, `| grep`, etc.) ... either one can swallow the script's own non-zero exit" (todo 1080). It is prose only.
- 2026-10-22, zng-admin session (todo 86): Claude ran `bash ~/.claude/skills/commit/commit-pathspec.sh ... 2>&1 | tail -6` for a `~/.claude` docs commit, after reading that rule the same session. The commit succeeded, so no harm, but a refusal would have read as success from the filtered tail.
- `hooks/cargo-test-pipe-guard.py` (+ `test_cargo_test_pipe_guard.py`) is the existing pattern for exactly this shape.

## Approach

Add a PreToolUse Bash hook (or extend the cargo guard into a generic "exit-code-sensitive command piped" guard) that denies a command containing `commit-pathspec.sh` followed by an unquoted `|` when `set -o pipefail` is absent from the same command. Deny message names the rule and the fix (run unpiped). Self-test alongside it.

## Acceptance

- `bash .../commit-pathspec.sh -m x -- f | tail -3` is denied; the same command unpiped, or with `set -o pipefail;` first, is allowed.
- `python ci/run_all.py` passes with the new self-test.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
