# Em-dash ban has no mechanical enforcement - relies on self-catch, which failed this session

**Type:** skill-improvement


## Goal

Find a way to actually catch em-dash usage in Claude's outbound chat messages, instead of relying on Claude remembering the rule every single message.

## Context

Global rule (`~/.claude/CLAUDE.md` "Communication" section): "Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead." Scope is already correctly narrowed by an existing memory (`feedback_em_dash_scope.md`: "ban is code + outbound messages only").

During the 2026-07-13 pipe-EOF diagnostics session (`claude_usage_in_taskbar`), multiple outbound chat messages used the em dash character ("â€”") despite the zero-exception rule, e.g. "Investigation agents are running in the background â€” I'll pick up analysis once they report back." and several lines in the final findings summary and the diagnostics-added report. Nobody (Joe) flagged it during the session; it only surfaced during this close's retrospective self-scan.

The rule is not a project-level thing - it's global, so this affects every project, not just this repo. This todo lives here only because this is the session that caught the recurrence; the fix (if any) is global.

## Approach

The core problem: outbound assistant text is not a tool call, so `PreToolUse`/`PostToolUse` hooks (which only see tool inputs/outputs) cannot intercept or block it before it reaches the user - there is no known hook point in the Claude Code harness that fires on "about to send a chat message". Options, roughly in order of plausibility:

1. **Accept it's a self-discipline rule, not a mechanically enforceable one** - close this as "won't fix", and instead strengthen the CLAUDE.md wording (e.g. move it earlier/bolder in the Communication section, or add a line like "check your own message for em dashes before sending") to see if salience alone helps. Cheap, unproven.
2. **A `Stop` hook that great-string-searches the just-completed transcript turn for "â€”" and, if found, blocks/warns** - needs confirming whether a `Stop` hook can see the assistant's own outbound text (not just tool-call state) and whether it can still act after the message already rendered to the user (if so, it's a detect-after-the-fact, not a prevent-before-send - still useful for tracking recurrence rate, not for silently fixing it).
3. **Do nothing extra, just note the recurrence** - if this is a rare, low-stakes cosmetic issue, it may not be worth harness engineering. Weigh against how often future sessions catch it in retrospective self-scans (grep the auto-memory/close history for this) - if it recurs often, escalate to option 2.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #251) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Recurrence log (evidence for the "how often does this recur" weighing in option 3):

- **2026-07-16** (overlay cursor-transparency session, `claude_usage_in_taskbar`): two more em dashes in outbound chat, e.g. "Yes, easy â€” it's a one-line CSS fix." and "...next time you hover the overlay â€” otherwise a restart of the dev server would be needed to see it." Again self-caught only in the /close retrospective, not during the session or by Joe. Second confirmed recurrence since this todo was filed - leans toward escalating to option 2 (Stop-hook detection) rather than closing as won't-fix.
- Dropped via /cleanup-todos 2026-08-12: re-opens the em-dash enforcement hook the dev explicitly closed as won't-fix on 2026-08-11. Duplicate of archived 59 and 213. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).

## Acceptance

- Either: a working detection/warning mechanism exists and is verified to fire on a deliberately-planted em dash in a test message, OR
- A documented decision that this stays a self-discipline-only rule, with the CLAUDE.md wording change (if any) applied.
- No regression to the rule's existing correct scope (code + outbound messages only, per `feedback_em_dash_scope.md` - do not expand to internal reasoning/thinking blocks).
