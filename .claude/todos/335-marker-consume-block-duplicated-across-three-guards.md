<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=5, reconfirm-count=1, content-hash=5080bdbf -->
# The consume-marker-then-allow block is copy-pasted across three PreToolUse guards

**Type:** task
**Origin:** ai

## Goal

Extract the "find the oldest fresh marker, delete it, allow" block into `_hooklib.py`, which
already exists for exactly this and already owns `oldest_fresh_marker`.

## Context

Three guards carry the same six lines:

- `hooks/pr-guard.py:90-96`
- `hooks/commit-guard.py:93-99` (same shape, plus `exclude_prefix=SESSION_MARKER_PREFIX`)
- `hooks/shortcut-create-guard.py:77-83` (added 2026-08-14, commit `a7c09a6`)

Each is:

```python
marker = oldest_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS)
if marker is not None:
    try:
        marker.unlink()
    except OSError:
        pass
    sys.exit(0)
```

`_hooklib.py`'s own docstring states its scope: *"Only extracts pieces verified byte-identical
across the guards."* Three copies of an identical block clears that bar, and the third was added
by copying the second rather than by extending the shared module.

The `OSError` swallow is the part worth centralizing: an unlink that silently fails leaves a live
marker that the NEXT gated call will consume, so one failed delete can wave through a second
ungated action. That reasoning currently exists in no single place, because the code exists in
three.

## Approach

1. Add to `hooks/_hooklib.py`:
   ```python
   def consume_fresh_marker(marker_dir, glob_pattern, freshness_seconds, exclude_prefix=None) -> bool:
   ```
   Returns True when a fresh marker was found and unlinked (or found and the unlink failed, matching
   today's behaviour), False when none existed. Keep `oldest_fresh_marker` public: `commit-guard`
   may still want the path itself.
2. Replace the block in all three guards with `if consume_fresh_marker(...): sys.exit(0)`.
3. `commit-guard.py` passes `exclude_prefix=SESSION_MARKER_PREFIX`; the other two pass nothing.
4. Re-run `python hooks/test_shortcut_create_guard.py` (its marker cases call
   `oldest_fresh_marker` directly and must keep passing), plus any commit/pr guard tests.
5. Verify live afterwards, the same way the shortcut guard was verified on 2026-08-14: fire a
   real gated command and confirm it is still blocked without a marker and allowed with one.

## Acceptance

- `_hooklib.py` holds one copy of the consume logic; no guard repeats it.
- All three guards behave identically to before: blocked without a marker, allowed once with one,
  marker gone afterwards.
- `hooks/test_shortcut_create_guard.py` still reports ALL PASS.

## Notes

- Filed by `/code-check` on 2026-08-14 from this session's own commits.
- Low risk but touches every marker-gated hook at once. `_hooklib` is imported by 9 hooks through a
  fail-hard try/except, so a mistake here blocks commits, PRs and ticket creation simultaneously.
  Change it in one commit with the guards, never split across two.
