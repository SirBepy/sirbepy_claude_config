<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=80053822 -->
<!-- duplicate-checked: grepped this backlog and its done/ for "final message", report_must_be_final and cleanup-memory/cleanup-todos step wording. Nearest hit is the zng-app memory feedback_report_must_be_final_message, which records the rule; nothing here proposes an enforcement path for it. -->
# 967 - "Report must be the turn's final message" has no enforcement, and gets broken

**Type:** skill-improvement
**Origin:** ai

## Goal
Make the final-message rule hold without depending on the model choosing to honour it, or drop the rule if it cannot be enforced.

## Context
Both `/cleanup-memory` (Step 7) and `/cleanup-todos` (Step 6) state that their report must be the turn's final message with nothing after it. `/iterate-it` carries the same contract, and the zng-app memory `feedback_report_must_be_final_message` records Joe having already corrected a session for breaking it.

**Broken twice in one session, 2026-09-06**, both times by the same reasoning: the constraint is justified in the skill text by a harness quirk where a same-turn question tool call swallows preceding text. In a Conductor session the report is delivered through `send_message`, which is a separate bubble and cannot be swallowed. So the stated rationale reads as not applying, and the session continued working in the same turn after both reports.

That reasoning is wrong in effect even if the mechanism is right: the rule's real purpose is that the dev actually reads the report before more work lands on top of it. But a rule whose written rationale does not cover the host it runs on invites exactly this rationalisation, and "be more careful" is not a fix.

Two candidate shapes, and the choice between them is the work:

1. **Restate the rationale so it holds on every host.** Say the rule is about the dev's attention, not about text being swallowed, and that it binds regardless of delivery mechanism. Cheap, no new machinery, still relies on compliance.
2. **Enforce it.** A `Stop` hook could check whether the last skill-report marker in a turn is followed by further tool calls. This is more mechanism than the problem may deserve, and it needs a reliable marker for "this was the report", which does not exist today.

Option 1 is probably right on its own; option 2 only earns itself if the restatement fails again.

## Approach
Pick one of the two above. If option 1, edit the Step 7 / Step 6 wording in `skills/cleanup-memory/SKILL.md` and `skills/cleanup-todos/SKILL.md` so the stated reason is the dev's attention rather than the harness quirk, and sweep `/iterate-it` for the same phrasing. If option 2, design the marker first; the hook is worthless without it.

## Acceptance
- The rule's written rationale is true on a Conductor host as well as a plain terminal.
- A session reading only the skill text has no defensible reading under which continuing the turn is fine.

## Notes
Filed from a zng-app session per root CLAUDE.md's rule that findings about the global tree belong in this backlog, not the surfacing project's. No global files were edited from that session.
