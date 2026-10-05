<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=0c6dbe0c -->
<!-- duplicate-checked: read 1010 in full. It is the same skill and the same blind spot (the backlog is never consulted) but a different step, failure and fix: 1010 is step 7b orphaning todos AFTER a script deletion; this is steps 3-5 paying for a fan-out that re-derives findings already filed. 1019 is the same skill again, different defect (the API ref denying the story-history endpoint). 233 and 312 are scope/arg-mode changes. 328 is /complete-todo, a different skill. -->
# 1023 - shortcut-done-audit fans out without reading the project's own todo backlog

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

`/shortcut-done-audit` reads the target repo's `.claude/todos/` before dispatching per-ticket
subagents, so it stops paying for findings that are already filed.

## Context

Measured on a real run, zng-app, 2026-09-25. Six tickets had commit signal, five sonnet subagents
were dispatched, ~580k subagent tokens total. When the findings came back and the backlog was
finally checked, **three of the four actionable findings already existed**:

- sc-55587's discarded account number was todo **143**, filed 2026-09-22: same root cause, same
  `_handleConfirm` early-return, same file.
- sc-55652's missing `payment-method-selected` coverage was todo **171**, filed 2026-09-23. The run
  did add one new call site to it, so this one was partly new.
- sc-55666's unreachable second `screen` payload value was todo **136**'s batch-2 item 4, filed
  2026-09-22, already phrased as a question for the analytics owner.
- sc-55360's Agree-skip was todo **183**, which knew the skip existed; the run added the mechanism.

Only one finding, a double-fire between two share events, was genuinely unfiled. The net outcome
was right (four existing todos updated rather than four duplicates filed), but the backlog check
happened AFTER the dispatch cost was paid, and only because the writing step's duplicate guard
forced it.

`SKILL.md` today goes from step 3 (match commits) to step 4 (dispatch-volume gate) to step 5 (fan
out). The backlog is never mentioned. `investigation-prompt.md` tells each subagent to check sibling
TICKETS for supersession, but never the repo's own todos.

## Approach

1. Add a step between the current 3 and 4: grep `.claude/todos/*.md` and `.claude/todos/done/*.md`
   in the target repo for each candidate ticket id. Report the hits alongside the candidate list.
2. Feed the hits INTO that ticket's dispatch prompt rather than skipping the ticket. An existing
   todo is prior art the investigator should confirm, extend, or contradict, not a reason to assume
   the ticket is handled. Extending todo 171 with a fourth call site is the outcome to design for.
3. Keep `done/` in the sweep. A finding already archived as done is the strongest signal that a
   "new" finding is stale, and it is the same check `/code-check` step 4a already runs against
   `done/` and `dropped-findings.log`.
4. While in `SKILL.md`, make step 6's report distinguish findings that already had a todo from
   genuinely new ones. Presenting four findings as new when three were known overstates the run.

## Acceptance

- A run against a repo with a matching todo prints the prior-art hits before dispatching anything.
- Each dispatch prompt for a ticket with prior art quotes that todo's id and goal.
- The final report separates new findings from ones that already had a todo.

## Notes

The same run produced todo 1019 (the skill's dispatch prompt asserting no story-history endpoint
exists, when it does). Both are cheap edits to the same two files, so whoever picks one should take
the other. Related: [[1010-shortcut-done-audit-7b-deletes-a-script-without-sweeping-the-backlog]],
the other half of this skill's backlog blind spot.
