<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1108 (done) is "chats should self-close + stop idle servers" as a general policy, already resolved - this is a specific execution bug inside /close's own Phase 6 (the already-written HARD ORDERING RULE got skipped), not a policy gap. 1000/101/1096/208 share only generic "rule/session/mechanical" vocabulary with no actual overlap on close_session ordering. -->
# /close's HARD ORDERING RULE (close_session before the kill script) is doc-only, no mechanical enforcement

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it hard to run `/close` Phase 6's kill script in a Conductor-hosted session without having
called `close_session` first, instead of relying on the model reading and following the prose rule
every time.

## Context

In `mc_plugins_tag`, 2026-10-17: Phase 6 was run, `close_session` was skipped (went straight to
`rename-session.ps1 -Close`) even though the tool was available in the session's tool list. The
HARD ORDERING RULE paragraph in `skills/close/SKILL.md` says this exact script line is "FORBIDDEN"
until `close_session` has returned - the rule is correct and clearly written, it just wasn't
followed. The process got killed, but the Conductor daemon respawned it on the next turn (per the
rule's own stated reasoning: "killing the process is MEANINGLESS to the daemon ... only the tool
call actually ends the chat"), so the chat never actually closed. The dev noticed only because he
sent a follow-up message and got a response instead of a closed chat, then asked "why didn't you
/close?".

## Approach

Two independent angles, either is worth doing on its own:

1. **Script-side guard.** Have `rename-session.ps1 -Close` (and the `.sh` equivalent) check, before
   killing, whether a Conductor host is present (e.g. the same signal `close_session`'s own
   availability implies) and whether `close_session` was actually called this turn. If a host is
   present and no confirmation is found, refuse/warn loudly instead of silently killing a process
   the daemon will just respawn.
2. **Stronger prose placement.** The rule already exists and is already marked "HARD ORDERING
   RULE" / "FORBIDDEN" - consider whether it needs to be restated immediately above the Windows/
   Mac-Linux script block itself (where the model's eyes land right before issuing the command),
   rather than only in the paragraph above it, in case proximity is the actual gap.

## Acceptance

A `/close` run in a Conductor-hosted session either calls `close_session` before the kill script
every time, or the script itself refuses to proceed silently when that call was skipped.

## Notes

- [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it. - dev delegated to autopilot on 2026-10-24 (Jarvis answered for Joe; re-check found the fix lands in `skills/close/`, not `hooks/`).
- rename-session.ps1/.sh -Close now refuse (exit 3, REFUSED line) in an SDK-hosted session (CLAUDE_CODE_ENTRYPOINT sdk-*), since the host respawns a killed process; /close Phase 6 says so next to the script block, and -Force/--force covers an SDK host without close_session. Test: skills/close/test_rename_session_close.py (refusal paths only; the kill path cannot run from a test without killing the session).
