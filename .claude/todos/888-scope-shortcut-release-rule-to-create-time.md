<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: read 831 (the /ticket log.md append being blocked by the permission classifier from a project session) and 333 in done/ (receipt discipline for outbound chat drafts) in full. Both share only the generic ticket/shortcut/rule vocabulary; neither touches the Release custom field or its scope. -->
# 888 - Scope the Shortcut Release rule to ticket creation only

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-02

## Goal

Narrow `~/.claude/skills/ticket/shortcut.md:56` so it cannot be read as licence to set the Release
custom field on a ticket that already exists.

## Context

That line currently states the Release custom field is **ALWAYS** `Next release`
(`value_id 698b4bce-ecd7-44c3-b62a-2b49b2506c1d`, `field_id 68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb`).
Written for ticket CREATION, but the word "always" reads broader, and a prior session correctly
refused to act on it unilaterally rather than guess.

Asked directly on 2026-09-02 whether to backfill Release on two already-shipped stories
(SC-55343, SC-55334, both moved to Testing on 2026-09-01, both returning **four** custom fields and
no Release field from `GET /api/v3/stories/<id>`), and whether to set it on the tickets from that
session's push, Joe answered:

> dont bother setting the release, dont worry about that, we will set release when we release them

So Release is set by Joe at actual release time. A missing Release field on an existing ticket is
not a gap to fill, and a workflow-state move (In Progress -> Testing) never touches it.

Surfaced from zng-app todo 77, now closed won't-do on that answer.

## Approach

Edit the `shortcut.md` line to say the rule applies when CREATING a ticket, and add an explicit
"never set Release on an existing ticket, including on a state move" clause. Keep both field UUIDs
exactly as they are; they are still current and must not be re-derived.

Check whether `/ticket`'s update/state-move path says anything about custom fields elsewhere in the
same file, so the two halves do not disagree after the edit.

## Acceptance

- `shortcut.md` states the create-time scope and the never-on-existing rule in one place.
- Nothing else about the GET/merge/PUT recipe changes: `PUT` still replaces the whole
  `custom_fields` array, so any future write still merges first.

## Notes

- The matching project memory is already updated: zng-app's `feedback_shortcut_release_next.md`
  carries the scope boundary and Joe's exact wording, dated 2026-09-02.
- Do not "fix" this by deleting the create-time rule. Release IS set at creation; only the
  existing-ticket case is out of scope.
