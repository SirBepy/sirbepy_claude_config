<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are done todos on verifying deletes (04), the Docker vhdx (06), mechanical delete-gate enforcement (835); none covers what the card text must say -->
# disk-doctor delete cards omit what created each item and whether it is still in use

**Type:** skill-improvement
**Origin:** ai

## Goal

Each per-item delete question already answers the two things Joe asks before approving: what produced this, and whether anything still uses it. That way a card can be decided in one round.

## Context

On 2026-10-05, `/disk-doctor` posted 7 delete cards. Each gave the path, size, a "regenerates" note, and the exact command. Joe answered 4 of the 7 (Temp, pip cache, `C:\tmp\pw-*`, npm+pnpm) with "u sure this is safe? whats it from?" or "are we myb still using it?". Answering took a second investigation round: newest-file dates, a grep of the projects for references to `C:\tmp\pw-`, and the age split of Temp. After that, every card was approved. The approvals stalled because the information was missing, not because the deletes were risky.

The delete gate's bullets live in `skills/disk-doctor/gate.md` ("Delete-confirmation gate"). They require the path, the size and the command, and nothing about provenance or recency.

## Approach

- Add one bullet to gate.md's delete-gate list. Each question also states (a) what created the item (which tool, app or session type), and (b) last-use evidence: the newest file mtime inside it, plus a running process or a project reference if one was checked. "Nothing references it" needs a receipt, such as a grep result or a process list.
- In windows.md's "How to run a scan", ask the scan subagent to return the newest-file mtime for each candidate dir over 1GB, so the cards can quote it without another round.

## Acceptance

- A dry run of the card text for a cache dir (for example pip) includes the producer, the newest file date, and whether anything reads it at runtime.
- The existing gate rules are unchanged: one question per item, the exact command named, NEVER-TOUCH items never offered.
