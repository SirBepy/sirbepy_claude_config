<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/273 fixed the background-work wording itself; this is the paste-fidelity gap that let a paraphrase skip that wording -->
# Preamble guard passes a one-line paraphrase that drops the auto-background paragraph

**Type:** skill-improvement
**Origin:** ai
**Summary:** A subagent dispatch prompt that leaves out the auto-background paragraph of the builder preamble is rejected.

## Why

On 2026-10-13 a builder with a paraphrased preamble sat parked about 45 minutes and 410k tokens waiting on its own backgrounded command, until the orchestrator stopped it.

## Goal

A dispatch prompt that leaves out `refs/builder-preamble.md`'s auto-background paragraph ("When a
command gets auto-backgrounded past its cap ... deliver your final report now. Do not start a
`Monitor`.") is rejected, so a builder cannot sit parked for an hour on a backgrounded command.

## Context

2026-10-13, ObsidianVault session porting the global toolkit into `SirBepy/dashboard-a`. The
orchestrator wrote short hand-rolled preambles instead of pasting `refs/builder-preamble.md`
verbatim. `hooks/dispatch-preamble-guard.py` marker 2 only requires `run_in_background` and
`FORBIDDEN` to both appear (`refs/builder-preamble.md`, "What the guard actually enforces", item 2),
so one sentence such as "run_in_background is FORBIDDEN" passes it.

The Stage 3a builder (porting `skills/commit/`) wrote every file, then ran the copied 84KB test
suite. The command auto-backgrounded and the agent stopped "waiting on its own background work"
for about 45 minutes and 410k tokens, until the orchestrator stopped it with `TaskStop`. The
paragraph that tells a builder what to do in exactly that case was the one the paraphrase left out.

`done/273` already fixed the wording of that paragraph. The gap here is that nothing checks the
paragraph was pasted at all. The ref turns down a fourth marker for the prefilter paragraph; this
incident is new evidence for the auto-background paragraph specifically.

## Approach

- Preferred: tighten marker 2 in `hooks/dispatch-preamble-guard.py` to also require a phrase unique
  to the auto-background paragraph (for example `auto-backgrounds any command past 120 seconds`),
  so only a real paste passes. Update "What the guard actually enforces" in
  `refs/builder-preamble.md` to match.
- Rejected: a reminder line alone. The orchestrator already had the rule to paste verbatim and
  didn't follow it; this needs a mechanical check.
- Watch the cost the ref worries about: every dispatch in every repo goes through this guard, so
  pick a phrase that is stable in the canonical block.

## Acceptance

- A prompt with only "run_in_background is FORBIDDEN" and no auto-background paragraph is denied.
- A verbatim paste of the canonical block still passes, including READ-ONLY DISPATCH prompts.
- The guard's self-test covers both cases, and `python ci/run_all.py` stays green.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
