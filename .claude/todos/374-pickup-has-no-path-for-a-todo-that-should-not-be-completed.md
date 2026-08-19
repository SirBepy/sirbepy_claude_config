<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=7, reconfirm-count=1, content-hash=7c8c5a58 -->
# /pickup Step 7 assumes every claimed todo ends completed

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/pickup` an explicit path for a todo that was worked on productively but should NOT be moved
to `done/`, so the correct action isn't left to the agent improvising against the skill's text.

## Context

`~/.claude/skills/pickup/SKILL.md`, Step 7, states without qualification:

> Run `~/.claude/skills/close/complete-todo.ps1 -Id <id>` to move the todo to `done/`, prune its
> PLAN.md line, and release the claim in one call.

Every other exit it describes is an abort (Step 4 blocker, Step 5 failing verify), all of which say
"release the claim, stop". There is no third state.

That third state is real and common for **epic-scale handoff todos**. Encountered 2026-08-18 in
`zng-app`: todo 134's Goal is "finish the lenderless / share-to-claim borrower + lender flow, epic
54968". A full session of real work landed against it (three commits, all runtime-verified), yet
completing it would have been wrong - the epic has many tickets left, and moving it to `done/` would
have dropped the flow's entire accumulated context out of the lane.

The agent had to reason its way to "update the file, release the claim, leave it planned, and say so"
with no skill text supporting it. That is the kind of judgement call that comes out differently
across sessions, which is exactly what a skill is supposed to prevent. An unattended run
(`/autopilot`) following Step 7 literally would archive a live epic handoff.

Note this is NOT the same as the abort paths: nothing failed, nothing was blocked, and the work
should not be retried.

## Approach

In `pickup/SKILL.md`, split Step 7 into two outcomes and make the agent pick one explicitly:

- **Completed** - the todo's Acceptance is satisfied. Current behaviour, `complete-todo.ps1`.
- **Advanced but not finished** - real progress, Acceptance not yet satisfied (long-lived handoff,
  epic tracker, or a todo whose remaining work is blocked on someone else). Then: update the todo
  file with what changed, refresh its PLAN.md line so the lane reflects the new state, release the
  claim, and name the remaining work in the completion summary. Do **not** move it to `done/`.

Suggested tell for the second branch, so it is decidable rather than vibes: the todo's Goal names an
epic / multi-ticket outcome, or its Acceptance still has unmet items that this session did not and
could not address.

Worth checking whether `ai-todos-format.md` should carry the same distinction, since `/batch-todos`
and `/autopilot` execute todos through the same contract and inherit the same assumption.

## Acceptance

- `pickup/SKILL.md` Step 7 names both outcomes and gives a decidable test for choosing.
- The unattended path is explicit: an `--unattended` run must not archive a todo whose Acceptance is
  unmet.
- Re-reading the skill cold, "I did real work but this epic isn't done" has one obvious answer.

## Notes

- Surfaced by `/close` Phase 1 on 2026-08-18 from a `zng-app` session.
- Related: **368** (unpushed-overlap check in a never-pushed repo) is a different skill and a
  different failure, listed only because both were hit in the same session.
