<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard's four hits all touch copy-paste-format.md but none covers status-update conciseness - 507 (done) is newline density, 305 (done) is per-person language override, 262 is Windows-path markdown escaping, 870 is a Clockify overlap check. Shared vocabulary only. -->
# Add a "team status updates" rule to the global copy-paste-format ref

**Type:** skill-improvement
**Origin:** dev

## Goal

Add a short "Team status updates" rule to `~/.claude/refs/copy-paste-format.md` so status messages Claude drafts for Joe to forward to coworkers are concise by default, across ALL projects (not just SSY).

## Context

During the SSY release session Joe pushed back on a forwarded team update being too verbose ("no need to give so much details bro... too much") and on wording ("say live instead of ziva"). A project-scoped memory was saved in the ssy-mobile backlog's own memory dir (`feedback_employee_messages.md`), but Joe forwards updates on other projects too (zirtue, revaire), so the rule belongs in the global ref. Joe explicitly accepted the offer to add it there but it was never executed.

Re-verified 2026-09-05 against `C:\Users\tecno\.claude\refs\copy-paste-format.md`: a grep for `team status|forwarded|status update|conciseness|outcome-first` returns no matches, so no such subsection exists. Two neighbouring rules HAVE since landed in that same file and must not be re-litigated here:

- Language matching already checks the recipient's `People\<Name>.md` for a stated language before defaulting to Croatian (todo 305, done 2026-08-13).
- Message length already says a drafted teammate message goes in short lines/short paragraphs, not one dense block (todo 507, done via commit a41ee81).

So the only genuinely missing piece is the CONTENT rule: what a status update should and should not say.

## Approach

Append a brief "Team status updates" subsection to `~/.claude/refs/copy-paste-format.md`, scoped to a drafted status update Joe forwards to coworkers:

- Lead with the outcome or decision. Cut the technical play-by-play (no DNS/TTL/propagation, no how-it-was-done).
- Account for send time: if Joe sends it hours later, write the end state ("live"), not the in-progress state ("propagira se, kroz ~sat").
- Prefer the borrowed English term the team actually uses over a translated one ("live", not "ziva") - a specific case of the existing "English tech terms left as-is" line, worth naming because the correction happened on exactly that word.
- Everything else (blockquote form, language matching, line breaks) is already covered by the surrounding sections - point at them rather than restating.

## Acceptance

- `refs/copy-paste-format.md` contains the new subsection.
- A future forwarded-update draft follows it without the ssy-mobile project memory needing to fire.
- Nothing in the new subsection duplicates the Language matching or Message length rules already in that file.

## Notes

- Relocated from `0001` in `C:\Users\tecno\Desktop\Projects\ssy-mobile` via /cleanup-todos 2026-09-05: the file it edits (`refs/copy-paste-format.md`) lives in this repo, not in ssy-mobile, per `close/ai-todos-format.md`'s "Which repo's backlog" rule.
