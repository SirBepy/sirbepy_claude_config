<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=542a4639 -->
<!-- duplicate-checked: grepped this backlog and done/ for "push-read-gate", "auto-commit.md" and "gate" + "read"; the only related entry is the original todo 467 that created the gate, which is about the missing check, not about how the check detects a read. -->
# 1005 - push-read-gate only counts Read-tool reads, so a `cat` of auto-commit.md does not satisfy it

**Type:** task
**Origin:** ai
**Created:** 2026-09-24

## Goal

Make `hooks/push-read-gate.py` either recognise a genuine non-Read-tool read of
`snippets/auto-commit.md`, or say in its error message that only the Read tool counts.

## Context

Found 2026-09-24 in a zng-app session (`eb19dc83`).

The session read `snippets/auto-commit.md` in full at the very start, in its first batch of setup
reads, via the Bash tool:

```
cd /c/Users/tecno/.claude && cat snippets/auto-commit.md
```

The whole file landed in context and was followed. Hours later, the first `git push` of the session
was blocked:

> [push-read-gate] This session's first `git push` is blocked until snippets/auto-commit.md has
> been read this session (todo 467: a skipped read of this exact file preceded an unasked-for push).
> Read it, then retry - every later push this session is ungated.

The fix was to re-read the same file with the `Read` tool, after which the push went through
unchanged. So the gate is keyed on the Read TOOL, not on whether the content was actually read.

This is a false positive against the gate's own stated intent. The costs are small but recur every
session that reads the file the other way:

1. A wasted round trip on the first push of every such session.
2. Worse, it trains the wrong lesson. An agent that has demonstrably read the file is told it has
   not, which invites re-reading files "to satisfy the hook" rather than because the content is
   needed.

Note the interaction with auto mode, which is what makes this reachable at all rather than rare:
that mode explicitly instructs reading files with `cat`/`head`/`sed` via Bash in preference to the
Read tool. So under auto mode the gate is close to guaranteed to misfire.

## Approach

Pick one, they are not equally good:

1. **Broaden the detection (preferred).** Also count a Bash tool call whose command contains a read
   of that path (`cat`, `sed -n`, `head`, `type`) with the filename matching `auto-commit.md`.
   String-matching a command is loose, but the failure direction is safe: the worst case is that
   the gate passes for a session that ran `cat` and ignored the output, which is no worse than the
   current state for a session that used `Read` and ignored it. The gate has never been able to
   prove comprehension, only exposure.
2. **Fix the message instead.** Leave detection as is and change the text to say explicitly that
   the read must be through the Read tool, not a shell `cat`. Cheaper and honest, but leaves the
   wasted round trip in place every time, and under auto mode that is every session.

Do NOT solve it by weakening the gate to a warning. Its whole point (todo 467) is that a skipped
read preceded an unasked-for push.

## Acceptance

- A session that reads `snippets/auto-commit.md` only via `cat` in the Bash tool can push without
  being blocked (option 1), OR the block message names the Read tool explicitly as the requirement
  (option 2).
- A session that has not read the file at all in any form is still blocked, unchanged.
- The second and later pushes in a session stay ungated, unchanged.

## Notes

- **Reproduced again 2026-09-26**, countoff session `57678915-3e08-4468-8a2d-7c1704da3989`, exactly
  as the Context section predicts. The session was in auto mode, read `snippets/auto-commit.md`
  with `cat` via the Bash tool, and the first `git push` was still blocked. Re-reading with the
  `Read` tool cleared it. Second independent sighting, different repo, so this is recurring rather
  than a one-off, and the auto-mode interaction called out above is what makes it near-certain.
- That same session found a **separate** defect while hitting this one: the gate fired a SECOND
  time hours later in the same session, against this todo's own last acceptance line. Filed
  separately as `1029-the-push-gate-refires-mid-session.md`, since the cause looks like marker
  files being deleted rather than anything about how a read is detected. Whoever picks either one
  up should read both: if 1029's cause turns out to be the prune in
  `write-session-marker.ps1`, then option 1 here becomes less urgent, because the wasted round trip
  would be happening once per prune rather than once per session.
- Completed by /loop-todos cycle 1 (2026-10-05), lane D2, test-first (RED against HEAD, then GREEN).
