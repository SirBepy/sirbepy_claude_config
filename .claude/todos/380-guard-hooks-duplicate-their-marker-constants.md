<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=5, reconfirm-count=1, content-hash=1448a771 -->
# Six guard hooks each redefine FRESHNESS_SECONDS and the marker-glob constants

**Type:** task
**Origin:** ai

## Goal

Move the marker constants every PreToolUse guard shares into `hooks/_hooklib.py`, so the freshness
window has one definition instead of six.

## Context

Found by `/code-check` during the 2026-08-18 `/close`. `FRESHNESS_SECONDS = 120` is declared
identically in **six** files:

- `hooks/commit-guard.py:45`
- `hooks/pr-guard.py:39`
- `hooks/shortcut-create-guard.py:38`
- `hooks/shortcut-mutation-guard.py:38`
- `hooks/linear-create-guard.py:42`
- `hooks/linear-update-guard.py:37`

Three of those six were added on 2026-08-18 while building the outbound gate, so this session
tripled an existing duplication rather than creating it.

`.outbound-marker*` is likewise repeated in four files (`shortcut-create-guard.py:37`,
`shortcut-mutation-guard.py:37`, `linear-create-guard.py:41`, `linear-update-guard.py:36`).

Why it matters: the 120-second window is a real coupling. `refs/outbound-ground-check.md` documents
it and tells callers to write the marker "immediately before the write call, not earlier in the
flow". Changing it in five files and missing the sixth produces a guard that silently disagrees with
the documented contract, and the symptom would be an intermittent false deny, which is exactly the
kind of thing nobody traces back to a constant.

**`_hooklib.py` is already the right home.** Its docstring says it holds "pieces verified
byte-identical across the guards", which these are.

## Approach

1. Add `FRESHNESS_SECONDS = 120` to `hooks/_hooklib.py` and import it in all six guards.
2. Add `OUTBOUND_MARKER_GLOB = ".outbound-marker*"` there too, and use it in the four outbound guards.
3. **Do NOT centralise the per-guard glob tuples themselves.** `commit-guard` uses `.commit-marker*`,
   `pr-guard` uses `.pr-marker*`, and the Shortcut guards use a two-name tuple including the legacy
   `.shortcut-marker*`. Those differences are deliberate; only the shared pieces move.
4. Watch the import style: every guard imports `_hooklib` behind a loud `try/except` that exits 2 on
   failure, on purpose, so a broken import blocks rather than silently disabling the guard. Keep that.

## Acceptance

- `FRESHNESS_SECONDS` appears once in `hooks/`, in `_hooklib.py`.
- All 11 suites still pass: `cd C:/Users/tecno/.claude/hooks; foreach ($t in Get-ChildItem -Filter "test_*.py") { python $t.FullName }`
- Each guard still blocks with no marker and allows with a fresh one. The tests cover this for four
  of them; `shortcut-mutation-guard.py` has no test yet, see [[382-shortcut-mutation-guard-has-no-test-file]].

## Notes

- Low urgency: nothing is broken today, all six values agree. This is about the next edit, not this one.
