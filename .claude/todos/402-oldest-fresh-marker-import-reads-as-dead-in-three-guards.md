<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=4, reconfirm-count=1, content-hash=6a4e3042 -->
<!-- duplicate-checked -->
# oldest_fresh_marker is imported but unused in three guards, and only the tests keep it alive

**Type:** task
**Origin:** ai

## Goal

Resolve the `oldest_fresh_marker` import in the three guards that never call it, either by having
the tests import it directly or by marking the re-export deliberate, so it stops reading as an
oversight to the next person who greps for unused imports.

## Context

Found by a `/code-check` dead-code pass on 2026-08-19. In each of these files a scoped grep for
`oldest_fresh_marker` returns exactly one hit, the import line itself:

- `hooks/linear-create-guard.py:35`
- `hooks/shortcut-create-guard.py:29`
- `hooks/shortcut-mutation-guard.py:29`

Within each guard's own logic the symbol is never called; only `consume_fresh_marker`, which wraps
it, is used.

It is NOT safely deletable, which is the part that makes this a real decision rather than a cleanup.
`hooks/test_linear_create_guard.py`, `hooks/test_shortcut_create_guard.py` and
`hooks/test_shortcut_mutation_guard.py` each call `guard.oldest_fresh_marker(...)` directly, two call
sites apiece, reaching through the guard module's namespace. Deleting the three imports breaks six
test assertions.

This predates the 2026-08-19 run. Commits `3e0fdac` (todo 380) and `de55513` (todo 381) touched these
exact import lines while adding `FRESHNESS_SECONDS`, `OUTBOUND_MARKER_GLOB` and `CLAIM_FIELDS`
alongside, and left it as-is. Notably the sibling `hooks/linear-update-guard.py` DID drop it in the
same pass, so the four guards are now inconsistent with each other.

## Approach

Pick one and apply it to all three, so they stop diverging:

1. Have the three test files import `oldest_fresh_marker` from `_hooklib` directly instead of
   reaching through `guard.`, then drop the import from the three guards. Cleanest, and it stops the
   tests depending on a guard's incidental namespace.
2. Keep the re-export and add a one-line comment saying the tests consume it, so the next unused-import
   sweep does not delete it and break the suite.

Whichever is chosen, make `linear-update-guard.py` consistent with the other three.

## Acceptance

- All four outbound guards handle this import the same way.
- `cd hooks; foreach ($t in Get-ChildItem -Filter "test_*.py") { python $t.FullName }` still passes
  every file.
- A grep for `oldest_fresh_marker` returns no hit that reads as accidental.
