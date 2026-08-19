<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=8, reconfirm-count=1, content-hash=590e4b89 -->
# /linear's recipes select numeric `priority`, which reads as the opposite of what it means

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/linear` reporting an unprioritised ticket as urgent.

## Context

Linear's `priority` field is an Int where **0 = "No priority"**, 1 = Urgent,
2 = High, 3 = Medium, 4 = Low. Low number does NOT mean high priority.

`skills/linear/queries.md`'s "List tickets assigned to the dev" recipe selects
the raw `priority`. On 2026-08-18 that produced `REV-5073 ... P0` in my output,
which I then relayed to Joe twice as a top-priority ticket. It is unprioritised
and sitting in Triage. Joe asked *"what does P0 mean?"*, which is how it surfaced.

The API exposes `priorityLabel` (a String: "No priority" / "Urgent" / "High" /
"Medium" / "Low") on the same object, for free, in the same query.

`SKILL.md`'s Output format section already shows the intended rendering
(`Priority: High`), so the recipes contradict the skill's own example.

## Approach

In `skills/linear/queries.md`:

- Change the assigned-tickets recipe to select `priorityLabel` alongside or
  instead of `priority`.
- Add the same to the lookup-by-ID recipe, which also selects bare `priority`.
- Add a one-line warning under the recipes: numeric `priority` 0 means No
  priority, so never render it as `P0`.

## Acceptance

Running the assigned-tickets recipe prints a word ("High", "No priority"), never
a bare number, and no `P<n>` string appears in `/linear` output.
