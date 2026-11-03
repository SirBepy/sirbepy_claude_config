<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1151 fixed outbound-verify-guard; shortcut-create-guard is a different hook -->
# shortcut-create-guard denies read-only commands that only name the Shortcut host

**Type:** skill-improvement
**Origin:** ai
**Summary:** `hooks/shortcut-create-guard.py` fires on any command text that contains the Shortcut API host, so a read-only diagnostic or a probe script that merely mentions the URL is blocked.

## Goal
A command that only reads from Shortcut, or only names the host inside a probe, is not blocked by `shortcut-create-guard.py`, while a real create call still is.

## Context
Reported 2026-11-03 by the pc-1151 builder, whose own probe command was blocked this way, and by the pc-1213 triage. It is the same family as pc-1151 (the outbound guard treating a GET as a write), but a separate hook and file. Trust boundary: it is a write gate, so a fix needs a negative test that a create still denies.

## Approach
Read the guard, restrict the match to an HTTP write (POST or PUT to a stories or comments path, or the MCP create tools) the way pc-1151 did for the outbound guard, and add cases to its test file.

## Acceptance
- [ ] A GET against the Shortcut host, and a script that only prints the host, pass.
- [ ] A create call still denies, covered by a test.
