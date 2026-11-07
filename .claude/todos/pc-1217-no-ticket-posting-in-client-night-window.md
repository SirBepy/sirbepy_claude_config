<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-22; no live or done todo covers ticket posting time; done/1111, 1140, 1150 are commit-window-guard tokenizer/override bugs, a different surface -->
# Extend the client night window (23:00-10:59) to ticket and PR posting

**Type:** task
**Origin:** dev
**Summary:** Claude does not create or edit tickets or post PR comments for a client repo between 23:00 and 10:59 without Joe's in-session OK.

## Why

At about 03:00 on 2026-10-22 Joe said "i dont wanna create a ticket at 3am"; today only commits and pushes are guarded by the night window.

## Goal

Claude does not create or edit Shortcut/Linear tickets or post PR comments for a client repo between 23:00 and 10:59 local without Joe's in-session OK, the same rule CLAUDE.md's Git Commits section already applies to commits and pushes.

## Context

- 2026-10-22, zng-biller session (3 BE tickets for Stevan): at about 03:00 Joe answered a "file ticket 2?" card with "i dont wanna create a ticket at 3am ... at 11am you can post them". Claude held tickets 2 and 3 and posted them at 11:00 via a `schedule` item into the same chat (the outbound-verify hook reads that chat's transcript, so a new chat could not have posted them).
- Today only commits/pushes are guarded: CLAUDE.md "Client repos: no commit/push 23:00-10:59 local without Joe's in-session OK", enforced by `hooks/commit-window-guard.py`. Nothing stops a Shortcut POST at 03:00; ticket 1 of that same session was posted overnight before Joe said this.
- Client repos are listed in `refs/client-repos.txt`; the outbound write detection already exists in `hooks/outbound-verify-guard.py` and `hooks/shortcut-create-guard.py`.

## Approach

- Add one line to CLAUDE.md's Git Commits client-repo bullet (or a sibling bullet) extending the window to tracker and PR writes Claude itself makes.
- Enforce it: either a check inside `hooks/shortcut-create-guard.py` / `hooks/outbound-verify-guard.py` (they already classify the call as an outbound write), or a small shared helper with `commit-window-guard.py`'s window logic. Allow an explicit in-session OK the same way the commit guard does.
- Document the working deferral recipe in `skills/ticket/SKILL.md`: verify now, write the JSON body file, `schedule` with `target: "this_chat"` at 11:00, marker in its own call at fire time.

## Acceptance

- A Shortcut story POST from a client-repo session at 02:00 is blocked with a message naming the window and the override.
- The same POST at 11:05 passes.
- The deferral recipe is in the ticket skill.

## Notes

- Joe's words are the source; no other incident yet.
- Deferred question (needs an attended session for its `hooks/`/`settings.json` writes) answered 2026-11-07: Joe said run it now, in the attended 2026-11-07 session; he approves each permission prompt as it appears.
