<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no other backlog file covers disk-doctor's advise-only wording -->
# disk-doctor SKILL.md still says "advise-only, Claude never deletes"

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/disk-doctor/SKILL.md` (description and line 9) agrees with what `gate.md` and `windows.md`
actually let Claude do, so a reader never gets two contradictory rules about who runs a delete.

## Context

Found 2026-10-23 by the builder of todo 1214 during a loop-todos run. `SKILL.md`'s frontmatter
description says "advise-only (Claude never deletes)" and line 9 says "You **advise**, never delete
- Joe runs the delete commands". `gate.md` (around lines 30 and 49) discusses Claude's own
`Remove-Item` hitting an access-denied and the removal guard, and `windows.md` now marks the
`LocalAppData\Temp\*-target` entries as deletable by Claude while the `C:\tmp` drive-root ones are
handed to Joe. UNVERIFIED which rule is current: the check is to read `gate.md` in full and the
2026-10 SCAN LOG entries in `windows.md`, then decide which file is stale.

## Approach

Read `gate.md` and the latest SCAN LOG entries; if Claude does run approved deletes now, reword the
description and line 9 to "Claude deletes only after an explicit per-card approval" (keeping the
description inside the 25w/120c frontmatter budget); otherwise bring `gate.md`/`windows.md` back to
advise-only.

## Acceptance

- `SKILL.md`, `gate.md` and `windows.md` state one consistent rule for who runs a delete.
- `python ci/check_skill_frontmatter.py` reports nothing for disk-doctor.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [SEC] Needs an attended session: the committed `gate.md` (Joe, 2026-08-29) and `windows.md` already let Claude run a delete after a per-item `ask_user_question` approval, so `SKILL.md` (description and line 9) and `macos.md` line 3 are the stale side. The unattended loop's edit of `SKILL.md` to say so was denied by the auto-mode classifier as self-modification (it widens Claude's stated delete authority), so Joe has to approve the wording edit in-session. Proposed description: "Use when Joe asks what to delete or how to free disk space. Repeatable cleanup scan; Claude deletes only per-item approved candidates."
