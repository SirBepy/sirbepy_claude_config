<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Subagents still background their work despite an explicit no-backgrounding instruction

**Type:** skill-improvement

## Goal

Stop dispatched subagents from parking on a backgrounded command or a spawned child and returning a
non-answer, when their prompt explicitly forbade it.

## Context

`~/.claude/refs/delegation-doctrine.md` already forbids backgrounding in builder prompts (added by
todo 437, done). Every dispatch in the 2026-08-05 `/auto-do-todos` run carried the instruction
verbatim: "Do NOT run anything in the background. Everything synchronous."

Two of roughly sixteen dispatches ignored it and burned a full dispatch returning nothing usable:

- The backlog dedupe scan spawned its own background children and returned the literal text
  "I'll wait quietly for the two background agents to notify completion." Its children did return
  the data, so the work survived, but the parent's answer was useless and the orchestrator had to
  reconstruct the dedupe itself.
- The `projects_ipc` compile fix returned "I'll stop issuing filler calls and wait for the monitor's
  completion notification." It HAD made the correct one-line edit, but never verified it; the
  orchestrator ran the test itself and found it green.

A third (the `pump.rs`/`parser.rs` work) reported that a build "auto-backgrounded on timeout" and it
re-ran synchronously, which is the failure mode handled correctly.

So the instruction is present, understood often enough, and silently ignored sometimes. The failure
is cheap to detect (the report is obviously a non-answer) but only because a human-shaped reader
noticed; an orchestrator that trusted the report would have recorded both todos as done.

## Approach

Prose in the dispatch prompt is demonstrably not sufficient on its own. Options worth weighing:

- A structural check on the orchestrator side: treat a report with no verification output, or one
  matching a "waiting/will wait/notify" shape, as a FAILED dispatch and re-dispatch, rather than
  reading it as a result. This is the cheapest and needs no harness change.
- Make the report contract explicit and checkable: require every builder report to include the
  verbatim output of at least one command it ran, so a report that ran nothing is structurally
  invalid.
- Investigate whether a long-running foreground command auto-backgrounds on a timeout and whether
  the subagent can distinguish that from a deliberate background call. The third case above suggests
  it can, and recovers, so the other two may be a different root cause.

Do not just re-word the doctrine line; it is already explicit and was already followed by most
dispatches. Whatever lands has to be a check, not a stronger sentence.

## Acceptance

- A dispatch that returns without having run its verification is caught mechanically, not by the
  orchestrator happening to notice the report reads oddly.
- The rule lives in one place (the doctrine ref), with the check wherever dispatches are evaluated.
- Must not regress: the doctrine's existing no-backgrounding line stays; this adds enforcement.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #501) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Filed by /close on 2026-08-05 from the `/auto-do-todos` run's retrospective. Related:
[[feedback_verify_subagent_writes_landed]] and [[feedback_subagents_degrade_product_to_pass_tooling]],
both of which are about not trusting a subagent's self-report.

**Recurred 2026-08-11 during a `/cleanup-todos` run, with two new facts worth folding into the fix.**

A triage agent given 40 todos spawned four background agents of its own and returned "All four batch
agents are running in the background. I'll wait for their completion notifications" - the same shape
as the 2026-08-05 dedupe scan, 47k tokens for zero data. Its children's results were never seen.

1. **The instruction has a hole.** The dispatch said "Do NOT use run_in_background for anything." That
   bans the FLAG, not the behaviour: spawning a child `Agent` is backgrounding by another route and is
   not literally covered. Any wording fix has to ban child-agent spawning explicitly, which also means
   the Approach's "re-word the doctrine" dismissal is too strong - the current line is not merely
   ignored here, it is genuinely silent on this path.
2. **Resume beats re-dispatch, and it works.** `SendMessage` to the agent's id, restating the task with
   "no further Agent/Task spawning, read the files yourself", resumed it from its own transcript and it
   returned complete cited verdicts. A fresh dispatch would have discarded the context it had already
   paid to build. This is a cheap recovery the Approach does not currently mention: the orchestrator
   check should resume-with-ban, not re-dispatch, once it detects the non-answer shape.

Detection was again by a human-shaped reader noticing the report read oddly, which is the exact gap
the Acceptance criteria describe. Still open.
- Dropped via /cleanup-todos 2026-08-12: the run_in_background prohibition (delegation-doctrine.md:65-67) and the nudge-recovery protocol (:117-118) already ship; duplicate of archived 99, dev-confirmed dropped 2026-08-11. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
