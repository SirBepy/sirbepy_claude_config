<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1178 is about step 7a's post_message redundancy with the daemon commit lock, 1196 is about coverage-tests-check missing inline Rust tests, 105 (done/) is a different step-1 enforcement gap, 1057 is about clockify's plan stating per-repo commit counts, 1106 is about push-gate mark needing its own tool call - none cover the Pre-push todo sweep's step 2 subagent-dispatch mandate; only vocabulary overlaps (commit/step/sweep/instead) -->
# `/commit`'s Pre-push todo sweep step 2 got judged inline instead of dispatched

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether `~/.claude/skills/commit/SKILL.md`'s "Pre-push todo sweep" step 2 should spell out
an explicit no-dispatch exception for an obviously-disqualified candidate, or whether the mandatory
subagent dispatch should stay unconditional and get enforced some other way.

## Context

During a `/commit pushnbump` in `claude_usage_in_taskbar` (2026-10-19), the Pre-push todo sweep
step found two open backlog todos touching files the push's commits also touched
(`.claude/todos/1231-...md`, `.claude/todos/1235-...md`, both naming `shortcuts.ts`/Ctrl+N). The
skill's step 2 says: "Dispatch ONE read-only subagent (`model: 'sonnet'` ...). A todo qualifies
only when all three hold: it touches files an unpushed commit already changes, it is EASY by
`/batch-todos`'s table, and it is the same concern or ticket as that commit."

Instead of dispatching, the session read both todo files directly and judged inline that neither
qualified: #1231 is an unreproduced investigation needing harness work (not EASY), #1235 needs
Joe's own physical action (a live demo) and isn't the same concern as the commit it references.
Both calls were clear-cut, but the step's literal text makes no allowance for skipping the
subagent dispatch on an obvious case - it reads as unconditional.

This is a minor, arguably-harmless deviation here (the two candidates were genuinely disqualified
on inspection), but it's the kind of shortcut that's easy to keep taking on less-clear-cut calls
where the independent-reviewer property the dispatch exists for actually matters - the same
rationale `/code-check` states explicitly for why ITS analysis always runs in a fresh subagent
("the session that wrote the code never reviews it"). The pre-push sweep's dispatch likely exists
for a similar reason (unbiased judgment on whether a todo really fits), and nothing in the skill
currently distinguishes "skipped because trivially disqualified" from "skipped because inline
judgment was faster."

## Approach

Pick one:
1. Add an explicit, narrow inline-judgment carve-out to step 2 (e.g. "skip the dispatch only when
   every candidate todo fails EASY or the same-concern test on its face, and state why inline"),
   matching how other steps in this skill distinguish mechanical checks from judgment calls.
2. Leave it unconditional and rely on review (`/code-check` of this skill's own adherence, or a
   future `/close` catching the same pattern again) rather than changing the text.

Whichever is chosen, make the skill's intent explicit rather than leaving it to be inferred again
next time.

## Acceptance

`skills/commit/SKILL.md`'s Pre-push todo sweep section either states the carve-out explicitly, or
a deliberate decision to leave it unconditional is recorded (e.g. in this todo's resolution) so the
same question doesn't get re-litigated from scratch next time it's noticed.

## Notes

- Archived by the cleanup-todos pass 2026-10-23: worth 3. Decision recorded: the Pre-push todo sweep step 2 stays unconditional; the todo itself called the skip harmless.
