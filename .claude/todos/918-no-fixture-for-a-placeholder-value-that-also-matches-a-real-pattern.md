<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hit, done/471, is the FIX that added placeholder allow rows and is complete. This is the intersection case that fix left uncovered - a value that is placeholder-shaped AND matches a real credential pattern. Follow-up, not a refiling. -->
# secret-scan has no fixture for a placeholder-shaped value that also matches a real pattern

**Type:** task
**Origin:** ai

## Goal

The secret-scan allow rules are pinned against the one case that would silently disarm them: a
value that looks like a placeholder AND prefix-matches a real credential pattern.

## Context

Surfaced 2026-09-04 by the builder that closed todo 471 (commit `d0c35fd`), as an out-of-scope
finding on its own work.

Todo 471 added allow rows to `hooks/secret-patterns.txt` keyed on self-evident placeholder markers
in the value (`not-`, `fake`, `dummy` and similar), so `"not-the-real-token"` stops being flagged.
That fix is committed and has coverage on both arms: a placeholder now passes, and a real-looking
credential (`password = hunter2hunter2`) still blocks.

What has **no** fixture is the intersection: a value that carries a placeholder marker while also
matching the shape of a genuine credential, for example an `AKIA`-prefixed AWS-shaped key that
happens to contain `not-` somewhere in it. If an allow row is broader than intended, that is the
value that slips through, and nothing currently proves it does not.

This is the failure mode that matters, because an over-broad allow row fails SILENTLY and in the
unsafe direction: the check keeps reporting clean while no longer checking. A false positive is
noisy and self-correcting; a false negative on a credential is neither.

## Approach

1. Read `hooks/secret-patterns.txt` and identify every allow row added by todo 471, and the deny
   patterns each one could plausibly overlap.
2. For each overlap, add a fixture to `hooks/test_secret_write_guard.py` asserting the value is
   still **blocked**, so a real credential shape does not become allowed just because a placeholder
   token appears somewhere in it.
3. If any such value turns out to be allowed today, that is a live hole in the scan, not a test to
   write around: narrow the allow row so the placeholder marker must dominate the value (anchored
   at the start, say) rather than merely appear in it.

Remember the two-engine constraint the pattern file is under: portable ERE only, no `\b`, no `\d`,
no lookahead or lookbehind. See `skills/commit/secret-scan.md`.

## Acceptance

- At least one fixture per todo-471 allow row proving an overlapping real-credential shape is still
  blocked.
- `python ci/run_all.py` passes with the new fixtures.
- If a narrowing was needed, the todo-471 fixtures still pass unchanged afterwards, so the original
  false positive stays fixed.
