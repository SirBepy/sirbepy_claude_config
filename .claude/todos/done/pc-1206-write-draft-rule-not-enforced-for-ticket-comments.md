<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo found for write_draft enforcement gaps as of 2026-10-20. -->
# 1206 - the "ticket comment belongs in Drafts panel" rule has no enforcement, only a system-reminder instruction

**Type:** skill-bug
**Origin:** ai
**Created:** 2026-10-20

## Goal

Either add a lightweight guard/reminder that catches an outbound ticket-comment draft being pasted
directly into `send_message` instead of routed through `write_draft`, or confirm no such mechanism
is feasible and downgrade this to "rely on the instruction" deliberately rather than by default.

## Context

zng-biller session, 2026-10-20, sc-56444 pickup. After 5 rounds of `outbound-verify` panel checks
on a Shortcut comment draft, the final verified text was pasted in full directly into a
`send_message` call so Joe could review it, instead of going through `write_draft`. The relevant
instruction is explicit and lists "a ticket comment" as a named example of content that belongs in
the Drafts panel, not chat text - and the session still got it wrong on the first attempt. Joe
caught it ("why did you write this message to me like this instead of like a draft") and it was
corrected by moving it to `write_draft` after the fact.

Unlike the outbound-verify gate (`hooks/outbound-verify-guard.py`, enforced mechanically on the
actual Shortcut API call) and the ground-check gate (`hooks/shortcut-create-guard.py` /
`hooks/shortcut-mutation-guard.py`), there is nothing that inspects a `send_message` call's text for
ticket-comment-shaped content and redirects it. The rule is pure instruction-following, with no
hook backing it up - the same category of gap those other hooks were built to close for their own
rules.

## Approach

Options to weigh, not a prescribed fix:

- A `PreToolUse` hook on `send_message` (or the host-side equivalent) that heuristically flags text
  resembling a ticket comment (e.g. contains a `shortcutapp://members/` mention token, or is >N
  chars and the transcript shows a recent Shortcut/Linear API read) and blocks or warns.
- Decide this is genuinely not reliably detectable (false-positive risk on legitimate long
  explanatory chat messages) and leave it as instruction-only, documented as a known-accepted gap
  rather than an open todo.

## Acceptance

- Either a guard exists and a repro case (drafting a ticket comment, then trying to paste it into
  `send_message`) is blocked/redirected, or this todo is closed with a note explaining why
  enforcement isn't worth building and the instruction is the permanent mechanism.

## Notes

- Archived by the cleanup-todos pass 2026-10-23: worth 4. Decision recorded: the write_draft rule for ticket comments stays instruction-only; a send_message hook would be heuristic with real false-positive risk.
