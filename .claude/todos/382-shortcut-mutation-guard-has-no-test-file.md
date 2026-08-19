<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# shortcut-mutation-guard has no test, and two guards carry an unused import

**Type:** task
**Origin:** ai

## Goal

Give `hooks/shortcut-mutation-guard.py` a test file like every other guard has, and drop two imports
that nothing uses.

## Context

Found by `/code-check` during the 2026-08-18 `/close`.

**The gap.** Of the four outbound guards, three have tests and one does not:

| guard | test |
|---|---|
| `shortcut-create-guard.py` | `test_shortcut_create_guard.py` |
| `linear-create-guard.py` | `test_linear_create_guard.py` |
| `linear-update-guard.py` | `test_linear_update_guard.py` |
| `shortcut-mutation-guard.py` | **none** |

That is the one that most needs a test. It carries three separate decisions, not one: the
ownership check (`requested_by_id` must equal `SHORTCUT_OWNER_UUID`), the Release-field bypass for
`zirtue-release-backfill`, and the claim-bearing marker gate added 2026-08-18. All three were
verified by hand on 2026-08-18 and none is pinned by a test.

It is also the guard with the worst failure history. Two live bugs were found in it on 2026-08-18:
a hand-rolled JSON parse that choked on a UTF-8 BOM, and, via that, the discovery that
`~/.claude/.env`'s BOM had been making the owner check **fail closed on every Shortcut mutation**.
A test would have caught the first immediately.

**The unused imports.** `oldest_fresh_marker` is imported but referenced nowhere in:

- `hooks/linear-update-guard.py:32` - its test does not use it either
- `hooks/shortcut-mutation-guard.py:31` - no test exists to use it

This is NOT true of `linear-create-guard.py` or `shortcut-create-guard.py`, where the import exists
so the test can reach `guard.oldest_fresh_marker`. That is a deliberate pattern; keep it there.

## Approach

1. Write `hooks/test_shortcut_mutation_guard.py` following the shape of the existing three
   (`_testlib.load_module`, a `CASES` table, `_testlib.run_cases`, `sys.exit(_testlib.summarize(...))`).
   Cover, without network calls, by testing the pure functions directly:
   - `is_claim_bearing` - true for `name`/`description`/`text` and for any `create-comment` tool;
     false for a bare `workflow_state_id` or `owner_ids` move.
   - `is_release_only_mutation` - true for a lone Release custom-field write, false the moment any
     other key or field id is present.
   - `extract_story_ids` - each key in `STORY_ID_KEYS`, plus the fail-closed deny on a non-int.
   - `load_env_file` - **must** cover a BOM-prefixed file, since that is the bug that shipped.
2. Delete the unused `oldest_fresh_marker` import from `linear-update-guard.py`, or keep it and have
   the new/existing test use it. Pick one; do not leave it unreferenced.
3. For `shortcut-mutation-guard.py`, the new test should use `oldest_fresh_marker`, which resolves
   its import too.

## Acceptance

- `python hooks/test_shortcut_mutation_guard.py` passes and is included when the suite is run.
- A BOM-prefixed `.env` fixture parses correctly in the test, pinning the 2026-08-18 fix.
- No guard imports a name nothing references.
- All suites pass: `cd C:/Users/tecno/.claude/hooks; foreach ($t in Get-ChildItem -Filter "test_*.py") { python $t.FullName }`

## Notes

- **Do not let the test hit the Shortcut API.** The owner check calls `fetch_story`; test the pure
  helpers around it and leave the network path alone, the way the other guard tests do.
- Related: [[380-guard-hooks-duplicate-their-marker-constants]] and
  [[381-claim-bearing-field-list-has-three-sources-of-truth]] touch the same four files.
