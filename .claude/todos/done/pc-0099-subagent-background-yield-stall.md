<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Subagents stall when they background long work and yield their turn

**Type:** skill-improvement

## Goal

Stop losing wall-clock time to background subagents that launch a long command, end their turn to "wait for the notification", and then never resume.

## Context

Observed three times in one session on 2026-07-31 while e2e-verifying ticket 54740. A background agent was asked to run a Playwright flow and an ~85s `flutter build web`. Each time it started the command with `run_in_background`, returned a placeholder result to the main agent ("Standing by for the build notification", "Waiting for the background test run to finish"), and then sat idle. The completion notification for its OWN child task did not bring it back, so the main agent had to detect the stall and poke it with `SendMessage` each time.

Cost: three round trips of the main agent polling process tables and file mtimes to work out what phase the subagent was even in, plus one agent that was ultimately stopped with its result never reported (the work survived only because it had written files to disk).

The main agent also cannot inspect a subagent's `.output` file to recover the answer, since that path is the full JSONL transcript and reading it blows up context. So a stalled subagent's findings are effectively unrecoverable except through whatever artifacts it happened to leave on disk.

## Approach

Add an explicit rule to `~/.claude/refs/delegation-doctrine.md` (and mirror it into the dispatch-prompt requirements section) covering verification/build subagents:

- Dispatch prompts for subagents that run builds, test suites, or browser flows must instruct: run the command in the FOREGROUND and wait for it in the same turn. Do not background it and yield.
- If a command genuinely exceeds the tool timeout, the subagent should chunk it or poll in-turn, not end its turn.
- Dispatch prompts should require the subagent to write its key findings to a small artifact file (not just return them in its final message), so a stopped or stalled agent is still recoverable.

Rejected: having the main agent poll subagent progress by reading the task output file. That file is the JSONL transcript and reading it overflows context, which is why the workaround this session was indirect process/mtime inspection.

## Acceptance

- A dispatched verification subagent that runs an ~85s build returns its result in one turn without the main agent nudging it.
- If an agent is stopped mid-run, its partial findings are still readable from a small on-disk artifact.

## Notes

Related to todo 54 (`delegation-doctrine-staging-and-longrunner-rails`), which already covers long-runner rails; this may fold into it rather than becoming a separate rule. Check that one first before editing the doctrine file.

**Recurred 2026-08-06, and this raises the priority: the prohibition was already IN the dispatch prompt and the agent broke it anyway.** A verification subagent for the sc-55002 routing fix was dispatched with the doctrine's verbatim line ("ALL commands run synchronously in the same tool call: `run_in_background` is FORBIDDEN... Ending your turn while anything is still running is a failed dispatch"). It backgrounded the e2e suite regardless and returned "Full suite run and target-spec build verification are underway. Waiting for the background monitor to report completion" as its entire result. One `SendMessage` nudge got compliance on the second try, exactly the recovery the doctrine predicts.

So the wording fix in the Approach above is necessary but not sufficient: a prompt-level prohibition is not enforcement. Worth considering whether the harness can deny `run_in_background` to subagents outright, or whether the doctrine should require the artifact-file fallback unconditionally so a parked agent's work is recoverable without a nudge.
- Dropped via /cleanup-todos 2026-08-11: the prohibition text and nudge-recovery protocol already shipped; only a minor artifact-file bullet remained. Confirmed by dev 2026-08-11.
