<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Autopilot sends too many chat bubbles; define what Joe wants surfaced and use write_plan for the rest

**Type:** skill-improvement
**Origin:** dev

## Goal

An `/autopilot` run in a Conductor chat shows progress through the live `write_plan` step checklist,
and sends a chat bubble only for the things Joe has said he cares about.

## Context

Joe, 2026-09-29, during an `/autopilot` run on claude_usage_in_taskbar (session c3db09b6): "i see you
write a lot more than you need to in chats like these. if youre on /autopilot you dont gotta write
this much stuff ... we should add a todo to better define what i actually care about and what i
dont. i think this could have been more helpful if it was moreso using this kind of style of
visualizing for me (the steps mcp)". He attached a screenshot of the `write_plan` checklist (green
done steps, one active, greyed pending steps).

What that run did wrong, concretely: it called `write_plan` once at the start and never updated it,
then sent roughly fifteen multi-paragraph `send_message` bubbles, one per landed commit or decision,
each listing shas, todo ids and mechanism detail. The checklist would have carried most of that.

Where the rules live today:
- `skills/autopilot/SKILL.md` has no reporting-cadence section at all; it only says to end with a
  written summary.
- The Conductor harness instructions say send_message is for results, blockers, discoveries,
  verification outcomes, commits landing; and write_plan is for in-progress work. "A commit landing"
  is listed as a send trigger, which under autopilot means a bubble per commit.
- Project memory `feedback_report_before_ending_turn` ("never silent") pulls toward more messages.

## Approach

1. Ask Joe (one question card, multi-select) which events he actually wants a bubble for during an
   autopilot run. Candidates: a genuine blocker or parked item needing him; a decision made on his
   behalf that he might reverse (iterate-it verdicts, UX calls); a real product bug found; something
   to look at (a screenshot); the final summary. Candidates he likely does NOT want: each commit
   landing, each todo closed, builder dispatches, mechanism explanations.
2. Add a short "Reporting" section to `skills/autopilot/SKILL.md` (and check `/mega-todos`,
   `/auto-do-todos` inherit or reference it): keep `write_plan` current at every step change (one
   step per todo or chunk, `detail` holding the sha), and send a bubble only for the agreed list,
   each at most two or three lines.
3. Decide whether the harness's "commit landing" send trigger should be overridden for autopilot, and
   say so explicitly in the skill so the two instructions stop conflicting.

## Acceptance

- Joe's answer recorded here.
- `skills/autopilot/SKILL.md` has the Reporting section; a dry read of it gives an unambiguous
  answer to "do I send a bubble for this commit?".

## Notes

- Conflicting enforcement to reconcile: the Conductor `send-message-stop-guard` Stop hook (todo 410)
  blocks a turn after 3-4 consecutive turns end with only `report_turn_status`. During the same
  2026-09-29 run, right after Joe asked for fewer bubbles, that guard forced a bubble on turns that
  only committed a small fix. Whatever the Reporting rule becomes, the guard needs a matching
  exemption (e.g. a turn that updated `write_plan` counts as reporting), or it will keep forcing
  exactly the noise Joe asked to cut.

