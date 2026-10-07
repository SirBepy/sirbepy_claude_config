<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=7, reconfirm-count=1, content-hash=4b3da45a -->
<!-- duplicate-checked: 291/1011 are about builders writing into .claude/todos; this is a scout blocked from writing its own sanctioned output file -->
# A READ-ONLY DISPATCH subagent cannot write the one output file the doctrine allows it

**Type:** skill-improvement
**Origin:** ai

## Goal

`refs/delegation-doctrine.md` and what the harness actually lets a read-only subagent do agree.

## Context

`refs/delegation-doctrine.md` "Scout before builder" says a read-only scout may write ONE named
output file "allowing that single file inside an otherwise `READ-ONLY DISPATCH`". On 2026-10-03, in
the fibo repo (session 88f76f6a), a sonnet `general-purpose` dispatch carrying the literal
`READ-ONLY DISPATCH` line and an explicit instruction to write
`.for_bepy/impeccable-sweep/REPORT.md` had its `Write` refused with "Subagents should return
findings as text, not write report files". The orchestrator had to write the 20 KB report from the
returned text. The same session's other dispatches, which did NOT carry the marker, wrote their
findings files under `.for_bepy/` without trouble, so the marker (or the `REPORT.md` filename) is
the likely trigger. UNVERIFIED which of the two it is: would check the hook or harness rule that
emits that message (grep `hooks/` for "return findings as text").

## Approach

1. Find what emits "Subagents should return findings as text, not write report files" (a hook in
   `hooks/`, or a harness rule outside this repo).
2. Either let a READ-ONLY dispatch write the single file its prompt names, or change the doctrine
   and `refs/builder-preamble.md` to say a scout that must write a file omits the marker and uses
   the screenshots-id line instead.

## Acceptance

- The doctrine's scout-writes-one-file rule matches what the harness permits, verified by one
  dispatch that writes its named file (or by the doctrine no longer promising it).
