<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=9, reconfirm-count=1, content-hash=f2b259de -->
# Builder dispatches must specify an explicit `timeout` for long builds

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "run everything synchronously" rule in the delegation doctrine actually satisfiable.

## Context

`~/.claude/refs/delegation-doctrine.md`'s canonical builder preamble says verbatim:

> "ALL commands, including the verify floor (build/test/lint/typecheck), run synchronously in the
> same tool call: `run_in_background` is FORBIDDEN in builder subagents, a long build is waited out,
> not backgrounded."

**That instruction cannot be obeyed as written.** The Bash tool's default timeout is 120s, and the
harness AUTO-BACKGROUNDS any command that exceeds it. The agent never chooses to background
anything; the harness does, and the agent then correctly observes it has a running job and ends its
turn. The doctrine then reads the result as a disobedient agent.

Evidence, `claude_usage_in_taskbar`, 2026-08-13: four separate sonnet builders parked on backgrounded
cargo builds in one session, every one of them carrying the FORBIDDEN wording. The fourth said the
mechanism outright: "The build was auto-backgrounded because it exceeded the default 120s tool
timeout (not a deliberate backgrounding on my part)." `cargo build --all-targets` in that repo takes
6-17 minutes, so it trips this every single time. Two agents died mid-task; one had done ~45 minutes
of real work, recovered only because its edits survived in the working tree.

This has been mis-attributed before. `feedback_builders_run_verify_synchronously` (2026-07-30)
recorded the same symptom for three agents and concluded sonnet "reaches for backgrounding" on long
builds, prescribing stronger wording and a SendMessage nudge. The wording was then applied verbatim
and it recurred four more times, which is what makes this a harness-parameter problem rather than a
compliance problem.

## Approach

Amend the canonical builder preamble in `~/.claude/refs/delegation-doctrine.md` so the prohibition
ships with the parameter that makes it possible, e.g.:

> Any command that may exceed 120 seconds MUST pass an explicit `timeout` (up to 600000). The tool's
> default is 120s and the harness auto-backgrounds past it, so omitting this backgrounds your build
> whether you intended it or not.

Also worth stating the cheaper fallback that actually worked: for a verify floor that is pure
mechanical command execution, the orchestrator can run it itself. It is not a feature-sized edit, so
it sits inside the orchestrator's surgical exception, and it removes the failure mode rather than
mitigating it.

Then update `feedback_builders_run_verify_synchronously` in that project's memory to point at the
real cause (already done 2026-08-13) so the old "sonnet reaches for backgrounding" framing stops
being retried.

## Acceptance

- The preamble names the explicit-timeout requirement, not just the prohibition.
- A builder dispatched from that template against a 10-minute build completes its verify floor
  without parking.

## Notes

- Completed via /auto-do-todos 2026-08-15: refs/delegation-doctrine.md now requires an explicit timeout (up to 600000ms) on any builder command that may exceed 120s, stated in both the Dispatch discipline bullet and the canonical preamble block so the two copies stay in sync. Reason recorded inline: the harness auto-backgrounds past 120s, which is what parked four builders on cargo builds.
