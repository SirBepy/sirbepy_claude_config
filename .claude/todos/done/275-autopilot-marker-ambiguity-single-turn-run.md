<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=4, reconfirm-count=1, content-hash=a81c43e4 -->
# autopilot skill doesn't say what to do when a run starts and finishes in one turn

**Type:** skill-improvement

## Goal

Clarify `~/.claude/skills/autopilot/SKILL.md`'s sidebar-badge contract for the case where an
entire autopilot run (dispatch through completion) happens inside a single assistant turn, so
the `<cc-autopilot:on>` marker doesn't get silently skipped.

## Context

2026-08-06, the chat-wide image gallery feature: the dev said "im fine with you implementing
this with /autopilot", and the whole 5-chunk build (scout, 5 builder dispatches, 5 commits, final
verify) ran inside one continuous assistant response, ending with `<cc-autopilot:off>` in the
final summary. `<cc-autopilot:on>` was never emitted, because the skill's instructions read as
"emit on at the end of your first response, emit off at the end of your final response" and
those were the same response - emitting only `off` felt right in the moment but means the host
app's sidebar badge (which reads `on` to show the "autopilot" badge) never fired at all, even
though it's meant to always fire whenever autopilot activates, per `~/.claude/skills/autopilot/SKILL.md:17-23`.

## Approach

Add an explicit line to the "Sidebar badge" section covering this case: either (a) always emit
`<cc-autopilot:on>` at the point autopilot activates even if `<cc-autopilot:off>` follows in the
same response, so the host at least sees a fired-and-immediately-cleared badge, or (b) explicitly
say that a same-turn on+off collapse is fine to skip `on` since the badge would never be visibly
shown anyway - whichever the app-side implementation actually expects. Check with the
`claude_usage_in_taskbar` app's sidebar-badge handling code (`src/`) for which behavior it
actually needs before picking.

## Acceptance

- The skill file states unambiguously what to do in the single-turn-run case.
- No regression to the normal multi-turn case (on at activation, off at completion, unchanged).

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #527) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Not a dev-facing bug report - the dev never noticed or asked about this, self-flagged during
`/close`'s retrospective. Low priority; the sidebar badge showing briefly then clearing vs. never
showing at all is a minor UX gap, not a correctness issue.
- Dropped via /cleanup-todos 2026-08-12: worth 4/10. The todo self-rates as a minor UX gap rather than a correctness issue, and the dev never noticed the marker ambiguity in practice.
