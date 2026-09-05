<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 834 widened this same regex for the INLINE-reason case and is done; this is the wrapped-reason case that survived it -->
# `todo-duplicate-guard`'s override marker still rejects a wrapped reason

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `<!-- duplicate-checked: ... -->` work when the reason wraps onto a second line, the way every
other comment in a todo file does.

## Context

Hit 2026-09-05 in `windows_taskbar_widgets` while `/auto-do-todos` filed an out-of-scope finding
(its todo 78) that shared vocabulary with an already-done todo 75.

`hooks/todo-duplicate-guard.py:48`:

```python
OVERRIDE_MARKER_RE = re.compile(r"<!--\s*duplicate-checked\b[^\n>]*-->")
```

`[^\n>]*` forbids a newline, so this passes:

```md
<!-- duplicate-checked: short reason -->
```

and this is silently not recognised, producing the identical "Possible duplicate" rejection as
having no marker at all:

```md
<!-- duplicate-checked: a reason long enough that it wraps
     onto a second line like every other comment here -->
```

The reason files wrap: the backlog's own todos are hard-wrapped near 100 columns, and the guard's
error message actively invites a reason (`a reason can go inside the same comment`). A reason worth
writing is usually longer than one line, so the invitation and the regex disagree.

This is the SECOND iteration of the same defect. The comment directly above that line records todo
834 widening the check from a strict equality match to this regex, for exactly the reason that
applies again here: *"inlining the reason next to the marker is the natural move and the strict
equality match gave no signal that FORM, not content, was rejected."* Same diagnosis, one wrap
further out. The retry cost a full round trip to diagnose, because the rejection message is byte
identical whether the marker is absent or merely malformed.

## Approach

Two independent changes; do both, they fix different halves.

1. **Allow the newline.** `re.compile(r"<!--\s*duplicate-checked\b[^>]*-->", re.DOTALL)` - dropping
   `\n` from the negated class is enough, since `-->` still terminates the match and an HTML
   comment cannot nest. Check `hooks/test_todo_duplicate_guard.py` (if it exists) and add a case
   with a wrapped reason; if there is no test file, that is itself worth fixing, since this is now
   the second regression in one regex.
2. **Make a malformed marker distinguishable.** If the text contains `duplicate-checked` anywhere
   but `OVERRIDE_MARKER_RE` does not match, the message must say so - something like
   "found `duplicate-checked` but not as a well-formed HTML comment" - instead of the generic
   duplicate rejection. Change 1 fixes today's shape; change 2 is what stops the third iteration
   costing another round trip.

## Acceptance

- A todo whose `<!-- duplicate-checked: reason -->` wraps across two lines is accepted by the hook.
- A todo containing a mangled marker gets a message naming the marker as the problem, not a bare
  duplicate rejection.
- `python ci/run_all.py` clean.

## Notes

- Filed from a `windows_taskbar_widgets` session per root `CLAUDE.md`'s rule that a finding about
  the global `~/.claude` tree belongs in this repo's backlog. Not executed there.
