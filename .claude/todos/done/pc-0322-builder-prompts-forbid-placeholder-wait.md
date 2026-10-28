<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Builder-dispatch prompts should forbid ending a turn on a placeholder wait

**Type:** skill-improvement
**Origin:** ai

## Goal

Strengthen the standard subagent builder-dispatch pattern (used by `/delegate`, project CLAUDE.md
subagent rules, and `feedback_no_placeholder_wait_agents.md`) so a dispatched builder never ends
its turn on an unresolved "waiting for the build/test to finish" message when a long-running
command is part of its own task.

## Context

2026-08-13, project `claude_usage_in_taskbar`: two of three dispatched builder subagents (fixing
an `is_remote` tagging bug and an account-pin resolution bug, both involving `cargo build`/
`cargo test`/`cargo test --test export_types` in a large Tauri+iroh workspace) ended their turn
2-3 times each with only "waiting for the build/test to finish" and no further progress, instead
of blocking on the process or completing before reporting. The main session had to manually
verify via `Get-CimInstance Win32_Process` that a real build was in-flight (not a stalled agent)
and re-`SendMessage` the agent to resume each time - 3 extra round-trips total, no data lost, but
pure overhead. This is exactly the anti-pattern `feedback_no_placeholder_wait_agents.md` already
names ("self-notifies; headless default") - the rule exists but isn't reliably followed by agents
running genuinely long (multi-minute) shell commands.

## Approach

The dispatch prompts already included "run cargo build/test to verify" as a step, but didn't
explicitly forbid ending the turn early on a long-running command. Add an explicit line to the
standard builder-prompt template (or each call site, if no central template exists yet): "If you
run a command that takes more than ~30s (e.g. a cold cargo build/test), do not end your turn until
it actually completes and you have its real output - a message like 'waiting for X to finish'
with no further action is not an acceptable final report." Also worth investigating: is this a
tool-timeout issue (the Bash/PowerShell tool call is genuinely returning control before the
process exits) rather than an agent-judgment issue - if so the real fix is elsewhere (raise the
default timeout for known-slow commands, or standardize on `run_in_background` + an explicit
poll-until-done loop instead of a foreground blocking call for cargo-scale builds).

## Acceptance

- A subagent dispatched with a cargo build/test step in a large Rust workspace completes and
  reports real output in one turn, without needing a manual resume for a placeholder wait message.

## Notes

Filed from `claude_usage_in_taskbar` per the global-vs-project todo rule (this is a global
dispatch-pattern/rule-enforcement gap, not project-specific code) - the project's own build being
slow just made it a reliably reproducible trigger this session.
- Dropped via /cleanup-todos 2026-08-15: refs/delegation-doctrine.md already carries this rule verbatim (lines 115-118, run_in_background FORBIDDEN in builder subagents, ending the turn while anything is still running is a failed dispatch) plus a dedicated Recovery procedure at lines 133-134, both predating the cited incident in commit 79e96be. Adding more wording restates an existing rule; the real open question (tool-timeout vs agent judgment) is a different problem than this todo Approach proposes. Origin ai, no confirm gate.
