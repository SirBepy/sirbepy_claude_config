<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=8, reconfirm-count=1, content-hash=0acd622a -->
<!-- duplicate-checked: 1043 and 1081 cover message surfacing / stop-guard ordering, not turn status while blocked on a dev action -->
# A turn blocked on Joe's physical action must report `question`, not `working`

**Type:** skill-improvement
**Origin:** ai

## Goal
When a Conductor session's only remaining blocker is something Joe has to do himself (join a local server, click a panel button, test in a real client), the turn ends with an `ask_user_question` card and `report_turn_status(question)`. The chat then shows input-needed. Today a plain `send_message` plus `report_turn_status(working)` leaves the chat looking busy.

## Context
mc_plugins_tag, 2026-10-05, session 8e00b706: Claude booted server/local at 18:33 UTC for a backpack-format capture that needed Joe's client. It asked him to join via `send_message`, started a background join-watcher, and reported `working` across ~2 h of later turns (peer relays). Joe had to point it out ("youve been working on this over an hour and a half btw"). The `report_turn_status` tool description already defines `working` as "your own background subagents/tasks in THIS session are still running and will re-invoke you". A watcher waiting on Joe is not that, so it was a rule violation with no mechanical catch. The related project memory "Player Claude: ask Joe as a question" covers only the /claude listener case.

## Approach
Pick one and implement it:
1. A rule line in `~/.claude/CLAUDE.md` Communication, or in the Conductor output-style text: "Waiting on Joe's own action = `ask_user_question` + status `question`. A background watcher for that action does not make it `working`."
2. Better, a Stop-hook nudge in the Conductor daemon (`claude_usage_in_taskbar`): if `report_turn_status(working)` fires while the turn's last `send_message` contains an instruction aimed at Joe ("join", "reply", "click", "run") and no Agent is running, warn the model to use `question` instead.

## Acceptance
- Rerunning the scenario (server booted, waiting for Joe to join) ends the turn with an input-needed card, not a `working` row.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): option 1 as rule 12 in output-styles/silent.md (the always-loaded Conductor output style, so it is in front of every turn): waiting on the user = question card + status question; working is only for this session's own still-running background tasks. Option 2 (a daemon Stop-hook nudge) would live in claude_usage_in_taskbar; not filed.
