<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "complete-todo", "done/", "prefix-less", "stem". done/794
     deduped the fallback and confirmed this bug predates it; nothing else covers it. -->
# complete-todo.ps1 reports "no todo file found" for a prefix-less todo already in done/

**Type:** task
**Origin:** ai

## Goal

Make `skills/close/complete-todo.ps1` report "already completed" for a prefix-less-stem todo that
has already been archived, instead of failing as if the todo never existed.

## Context

Found 2026-09-02 by todo `794`'s builder while verifying its dedupe, and explicitly confirmed as
**pre-existing, not introduced by that refactor** - reproduced against `git show HEAD` of the
pre-refactor script in a scratch repo, where the inline fallback block had the same scoping.

A todo with no numeric prefix (e.g. `orphan-note.md`, the shape `ai-todos-format.md` calls malformed
but still archivable) archives fine the first time. Re-run `complete-todo.ps1` with that same id
afterwards and it fails:

```
No todo file matching id ... found in <todos> or <done>
```

The correct answer is "already completed", which is what the script reports for a normally-prefixed
todo in the same situation.

**Cause**, per 794's builder: `Resolve-TodoFile`'s fallback-to-stem search only runs against the
backlog directory. Once the file has moved to `done/`, the fallback never fires, so the returned
pattern stays at the id-shaped `^0*<id>-.*\.md$`, which can never match a plain `<id>.md` filename
sitting in `done/`.

**Low urgency, and the todo says so.** Prefix-less todos are rare by design and the failure is loud
rather than silent. What makes it worth filing is that the message actively misleads: it says the
todo does not exist when it does, in `done/`, which invites someone to re-create it.

## Approach

1. Reproduce in a scratch repo under `C:/tmp` first, with a prefix-less todo, both before and after
   archiving. Do not fix before seeing the second run fail.
2. The fix belongs in `skills/close/_shared.ps1`'s `Resolve-TodoFile` (created by `794`), not in
   either caller: either let it search a second directory, or have it return enough information for
   the caller to run the same fallback against `done/`. It already returns `Pattern` for exactly
   this reuse - the gap is that `Pattern` is the non-fallback shape when the fallback never fired.
3. Check `claim-todo.ps1` shares the corrected behaviour, since it dot-sources the same helper. It
   has no `done/` search today, so most likely it needs nothing - confirm rather than assume.

## Acceptance

- A prefix-less todo already in `done/` is reported as already completed, not as missing.
- A normally-prefixed todo already in `done/` still reports already completed (no regression).
- A prefix-less todo still in the backlog still archives, with its existing malformed-name warning.
- Both scripts still resolve: a plain numeric id, a leading-zero id, and a full `<id>-<slug>` stem.

## Notes

- Worth roughly a 4. Real, reproduced, and narrow.
- There is no test suite for `skills/close/*.ps1` (no `test_*.ps1` exists anywhere), so the
  acceptance above is manual in a scratch repo. `810` proposes the fixture harness that would make
  this kind of proof cheap.
