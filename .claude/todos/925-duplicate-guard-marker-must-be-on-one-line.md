<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog and done/ for "duplicate-guard", "duplicate-checked" and "OVERRIDE_MARKER" before filing. -->
# The duplicate-guard's override marker silently requires one line, and its error message doesn't say so

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop a correctly-written `<!-- duplicate-checked: reason -->` from being rejected just because the
reason wrapped onto a second line, so filing a legitimately-distinct todo takes one attempt.

## Context

Hit 2026-09-04 in the hubbub repo while filing a todo whose duplicate-check reason ran to four
lines. The guard rejected the write.

`hooks/todo-duplicate-guard.py:48`:

```python
OVERRIDE_MARKER_RE = re.compile(r"<!--\s*duplicate-checked\b[^\n>]*-->")
```

The `[^\n>]*` class excludes `\n`, so the whole marker must sit on ONE line. That is a deliberate
choice, not a bug - a greedy multi-line match could swallow unrelated content - so the fix is not
to loosen the regex blindly.

The problem is the error message at `hooks/todo-duplicate-guard.py:310`, which says only:

> add `<!-- duplicate-checked -->` anywhere in the new file's content to proceed - a reason can go
> inside the same comment, e.g. `<!-- duplicate-checked: the two hits are different surfaces -->`

"Anywhere in the content" plus an invitation to write a reason reads as "wrap freely". A multi-line
reason is the natural thing to write when there are two hits to distinguish, and it fails with the
identical message the second time, giving no signal about what changed.

`ai-todos-format.md`'s Content-duplicate guard section has the same gap: it shows the marker inline
without stating the one-line constraint.

## Approach

Pick one, they are not exclusive:

1. **Cheapest, do this regardless:** add the constraint to the error message - "the marker must be
   on a SINGLE line; a wrapped reason will not match". Same sentence into `ai-todos-format.md`.
2. Detect the near-miss and say so specifically: if the content matches
   `<!--\s*duplicate-checked\b` but the full `OVERRIDE_MARKER_RE` does not, the author clearly
   intended the override and wrapped it. Emit a distinct message naming that, instead of the
   generic "possible duplicate" block.

Option 2 is the one that actually fixes the retry loop; option 1 alone still costs one failed write
for anyone who has not read the hook source.

## Acceptance

- A todo whose `<!-- duplicate-checked: ... -->` wraps across lines is either accepted, or rejected
  with a message that names the one-line requirement explicitly.
- `python ci/run_all.py` green, including `hooks/test_todo_duplicate_guard.py` if it exists (add a
  case for the wrapped marker if it does).
- `skills/close/ai-todos-format.md` states the constraint where the marker is introduced.

## Notes

- Do not widen the regex to `[\s\S]*?` without bounding it. The `>`-exclusion and the newline
  exclusion together are what stop the marker matching across an unrelated comment.
