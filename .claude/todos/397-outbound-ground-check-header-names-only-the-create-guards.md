<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# outbound-ground-check.md says it is enforced by the create guards only, but four hooks consume it

**Type:** task
**Origin:** ai

## Goal

Correct the "Enforced by" header in `refs/outbound-ground-check.md` so it names every hook that
really consumes the outbound marker, not just the two creation guards.

## Context

`refs/outbound-ground-check.md` lines 6-9 state the file is enforced by
`hooks/shortcut-create-guard.py` and `hooks/linear-create-guard.py`. Two more hooks read the same
outbound marker per their own code: `hooks/shortcut-mutation-guard.py` and
`hooks/linear-update-guard.py`.

The practical cost is that a reader checking which writes are gated undercounts by half, and the
mutation path is precisely the one where a wrong edit is visible to a whole team with no undo, so
undercounting there is the worse direction.

Surfaced by todo 381's builder on 2026-08-19 as a pre-existing gap it deliberately left untouched to
stay in its lane. Todo 380 (`3e0fdac`) and 381 (`de55513`) have since centralised
`FRESHNESS_SECONDS`, `OUTBOUND_MARKER_GLOB` and `CLAIM_FIELDS` into `hooks/_hooklib.py`, so the four
hooks now visibly share the mechanism the header describes.

Duplicate-checked against the backlog: no live or archived todo covers this header's contents.

## Approach

1. Read all four guards and confirm which really consume the outbound marker, rather than trusting
   this todo's list.
2. Update the header to name them, and say what each gates (creation versus claim-bearing update),
   since those are different acts with different blast radius.
3. While there: check whether the file's prose still restates the claim-bearing field list now that
   `_hooklib.CLAIM_FIELDS` owns it. Todo 381 was supposed to replace that with a pointer; verify it
   actually did.

## Acceptance

- The header names every hook that consumes the marker, and only those.
- Each named hook is described by what it gates.
- No prose copy of the claim-bearing field list survives outside `_hooklib.py`.
