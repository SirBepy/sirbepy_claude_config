<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 450 is about WHEN code-check fires, this is about it re-proposing findings already resolved as declined. Different failure. -->
# 898 - /code-check re-surfaces findings that were already declined

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/code-check` from proposing structural findings that a previous run already surfaced and a
human already declined, so its output stays worth reading.

## Context

Measured 2026-09-03 in zng-app. A `/code-check` run returned a class-2 finding proposing that
`_SharedStatusToggle` be extracted from
`lib/ui/loan_request_v2/status/v2_request_status_screen.dart`.

That exact extraction has now been proposed at least five times:

- filed as zng-app todo 16, after runs on `6bf0364` (2026-08-27), `c95426a` (2026-08-28) and
  `7f54ae7` (2026-08-29), each re-surfacing it
- **declined** by `/cleanup-todos` on 2026-09-01, scored 4/10: "behaviour-neutral file split in a
  zirtue-corp repo, no downside to leaving as-is". The todo moved to `.claude/todos/done/`.
- surfaced again 2026-09-02 and logged to `dropped-findings.log`, whose own entry already
  diagnoses the cause: *"/code-check cannot see done/ so it re-surfaces every run"*
- surfaced again 2026-09-03, which is this todo

The reviewer is not wrong each time. The file genuinely is 472 lines with a clean seam. But the
decision not to split it was made deliberately, and nothing carries that decision forward into the
next review.

The cost compounds: an orchestrator has to re-derive the whole history (read the finding, search
the backlog, discover the hit is in `done/`, read it, notice it says "Dropped", check
`dropped-findings.log`) before it can safely ignore a finding. That is several tool calls per
close, on a finding whose answer has not changed in three days.

This is distinct from todo 450, which is about WHEN `/code-check` fires. This is about it having
no memory of what was already resolved.

## Approach

Options, roughly cheapest first. Pick one, do not do all three.

1. Have `/code-check`'s dispatch prompt include the titles of `.claude/todos/done/*.md` and the
   contents of `.claude/todos/dropped-findings.log`, and instruct the subagent to omit any finding
   matching one. Cheap, no new machinery, but it grows the prompt over time and relies on the
   subagent's judgement about what "matching" means.
2. Keep the review blind (which is its whole value) and filter on the ORCHESTRATOR side in Step 4a:
   before filing, diff each finding's target `path:line` against `done/` and
   `dropped-findings.log`, and route a match straight to the log with `dropped as DECLINED`
   instead of filing. Preserves reviewer independence, which option 1 erodes.
3. Give a declined finding a durable marker at the site itself, so any reviewer sees it in the code
   rather than in a backlog it cannot read. Most robust, most invasive, and it puts process
   metadata in source, which this project's comment rules push back on hard.

Option 2 looks right: it keeps the reviewer uncontaminated, which is the property `/code-check`
exists for, and puts the bookkeeping where the bookkeeping already lives.

## Acceptance

- A `/code-check` run over a diff touching `v2_request_status_screen.dart` does not file a todo
  proposing the `_SharedStatusToggle` extraction.
- It still logs it, so a genuine change of heart stays recoverable rather than the finding
  vanishing silently.
- A finding NOT present in `done/` or the log is unaffected and still files normally. Prove this
  with a second run over a diff that has a real new finding, rather than only proving the
  suppression half.
