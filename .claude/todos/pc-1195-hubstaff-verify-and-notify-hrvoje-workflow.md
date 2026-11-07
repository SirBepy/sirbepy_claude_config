<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Design a Hubstaff-verify-then-notify-Hrvoje workflow

**Type:** task
**Origin:** dev
**Summary:** A workflow confirms Hubstaff hours for a period are really filled, then schedules a message telling Hrvoje Herceg the hours are in.

## Why

"I want to make a workflow that always does this accurately doesn't mess up like you just did now" (Joe, 2026-10-19). He deferred scoping it that day.

## Goal

Joe wants a workflow that (1) reliably confirms Hubstaff hours for a period are filled and correct
(screenshot genuinely shows real data, not stale/empty), then (2) automatically schedules a message
to Hrvoje Herceg (Cinnamon Agency, messaged on Google Chat - confirmed via the `person` tool
2026-10-19, alias "Hrvoye" now saved) through some MCP, to tell him the hours are in.

## Context

Raised 2026-10-19 in a zng-app session (Joe: "I want to make a workflow that always does this
accurately doesn't mess up like you just did now, and then it automatically schedules a message to
Hrvoye using my NCP [MCP, voice mishear] ... but that part doesn't matter right now"). He
explicitly deferred scoping it in that session - this todo exists so the ask isn't lost, not
because it's blocking.

Same session fixed the immediate trust problem in `~/.claude/skills/clockify-reconciliator/scripts/hs_weekshot.cjs`:
it now deletes stale `hubstaff-weekly-*.png` files from `--out-dir` before writing, and parses the
page's own "Total: H:MM:SS" text into a `totalHours` field (warns if unreadable or all-zero)
instead of relying on file size alone. See `feedback_hubstaff_screenshot_handoff_must_be_fresh.md`
in the zng-app project's memory for the full incident writeup. That fix covers part (1) above at
the script level; a full "workflow" (scheduled/triggered run, not just a safer manual script) is
still undesigned.

Part (2) - the Hrvoje notification - has no design at all yet: which MCP Joe means, what
triggers the send (every Friday? every full week filled? on demand?), and what the message should
say are all unanswered.

## Approach

Do not design this inline - run it through `/brainstorm` per CLAUDE.md's rule for creative/feature
work, with Joe present, when he says he's ready. Questions to front-load at that point:
- Trigger: cron/schedule, or fired manually after a /clockify-reconciliator run reaches the
  HubStaff gate (step 10a)?
- What "accurately" should check beyond what `hs_weekshot.cjs` already does now (just the
  screenshot, or also the step 11 Clockify/HubStaff comparison?).
- Which MCP/channel reaches Hrvoje - he's on Google Chat per his vault note; confirm Joe has an
  MCP for that specifically, since none is referenced elsewhere in this repo's skills.
- Message content/tone - Hrvoje's vault note says Croatian or English; check his "Writing to them"
  section if one exists before drafting anything.

## Acceptance

- Joe has approved a concrete trigger, scope, and message draft before anything gets built.
- No hours ever get silently fabricated to hit a target - this must stay bound by the existing
  clockify-reconciliator "never invent hours" rule, not loosen it.

## Notes

Not urgent - Joe said explicitly the notification part "doesn't matter right now." Pick up only
when he raises it again.
