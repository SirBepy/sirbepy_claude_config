<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Builder subagents still park on backgrounded commands despite the doctrine forbidding it

**Type:** skill-improvement
**Origin:** ai

## Goal
Make `~/.claude/refs/delegation-doctrine.md`'s "no `run_in_background` in builders" rule actually hold, rather than restating it more loudly.

## Context
Observed 2026-08-14 in claude_usage_in_taskbar during a seven-builder fan-out. One Rust builder ended its turn twice with nothing but "Still waiting for the background cargo build to complete" and "Waiting for the test run to complete", burning roughly 45 minutes of wall clock across two dead turns.

The dispatch prompt contained the doctrine's exact prescribed text, verbatim: "ALL commands, including the verify floor (build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background` is FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn while anything is still running is a failed dispatch." It did not help. The doctrine already anticipates this and prescribes a recovery nudge, expecting to repeat it once; here it took two nudges, and the second only worked because it explicitly told the agent to stop running commands entirely and report facts it already had.

Note the shape of the failure: the work was DONE and correct on disk the whole time. The file split had landed, the code compiled. Only the report was missing. So the cost is pure orchestration overhead, and it is invisible until you go looking, since a parked agent reports as "completed".

This is the same enforcement-gap category the doctrine names elsewhere: a rule stated verbatim in every dispatch of the run that broke it anyway (see the em-dash note at doctrine lines 49-53, todo 290). Wording-only fixes have already failed once for that exact class of rule.

## Approach
Prefer a structural fix over stronger wording, since stronger wording is what already failed:
- Have the dispatch specify a per-command timeout the builder must pass (the tool accepts up to 600000ms), so "this will take too long for one call" stops being the builder's own judgment call.
- Instruct builders that when a command genuinely exceeds the foreground cap, the correct move is to report the partial result WITH the command still running and say so, rather than ending the turn silently waiting.
- Consider adding a recovery line to the doctrine that the orchestrator should take verification over itself after ONE failed nudge rather than two, and just run the build in the main thread.

Whatever lands, add it to the doctrine's "embeds, without exception" list so every dispatch carries it.

## Acceptance
A builder dispatched with a multi-minute build either returns a real report with real command output, or returns explicitly saying a command is still running and why. No more turns whose entire content is "waiting".

## Notes

- Done 2026-08-16, commit 8a55286. The timeout instruction was already present and clear in refs/builder-preamble.md, so no wording was strengthened. The missing structural piece was added instead: the only case allowed to end a turn unfinished is a foregrounded command outliving its 600000ms cap, and it must report the partial output plus the exact command still in flight, never a bare 'still waiting'. The doctrine's Recovery section now says the orchestrator takes verification over itself after ONE failed nudge rather than sending a second, since the second nudge only ever worked by telling the agent to stop and report facts it already had.
