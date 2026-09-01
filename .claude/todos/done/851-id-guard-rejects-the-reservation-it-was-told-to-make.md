<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=8, reconfirm-count=1, content-hash=b09a7261 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for reserve-todo-id / id uniqueness / duplicate guard: done/492 is the parent that introduced this, no live match. -->
# The new id guard rejects the very reservation it tells you to make

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `hooks/todo-duplicate-guard.py`'s new id-uniqueness check ignore the `<id>-.reserved` marker
for the id currently being written, so the documented reserve-then-write flow stops being blocked by
the guard that recommends it.

## Context

Reproduced 2026-08-31, minutes after todo `492` shipped the check, by the `/mega-todos` orchestrator
that had just archived `492`.

The contract in `skills/close/ai-todos-format.md` is: call `reserve-todo-id.ps1`, which atomically
writes `.claude/todos/<id>-.reserved` to hold the id, then write the real
`.claude/todos/<id>-<slug>.md`, then delete the marker. `492` correctly made a `*-.reserved` marker
count as a taken id, so two concurrent sessions cannot both land on max+1.

It does not exclude the marker for the id being written. So the exact sequence the contract
prescribes fails on step 2:

```
> reserve-todo-id.ps1 -RepoRoot C:\Users\tecno\.claude
Reserved todo id 850 -> .claude\todos\850-.reserved
> Write .claude/todos/850-hooklib-strip-quotes-deletion-blocks-every-shell-call.md
[todo-duplicate-guard] Id 850 is already claimed by 850-.reserved. Ids must be unique across
.claude/todos/, done/, and *-.reserved markers - run `skills/close/reserve-todo-id.ps1 ...`
to reserve a free one instead of picking by hand.
```

The advice in the denial is what produced the collision, so following it loops.

The workaround, which is what unblocked this session, is to delete the marker BEFORE writing the real
file. That is strictly worse than the contract: it reopens the max+1 race the reservation exists to
close, for exactly the window in which the file is being written.

`492`'s own test cases cover "a `*-.reserved` marker counts as taken" but not "the reserver's own
marker does not block its own write", which is why this got through green.

## The mechanism, and why a test is protecting it

Confirmed by an independent `/code-check` reviewer on 2026-08-31 and verified again by hand. Two
separate things are wrong, and the second one will fight whoever fixes the first.

**1. The exclusion cannot fire for a reservation marker.** `hooks/todo-duplicate-guard.py:181` reads:

```python
if f.parent == todos_dir and f.name.lower() == target_name:
    continue
```

`f.name` for a marker is `850-.reserved`. `target_name` is `850-<slug>.md`. Those strings can never
be equal, so the in-place-rewrite carve-out never applies to a marker, and every reservation the
caller just made is treated as a foreign collision.

**2. `hooks/test_todo_duplicate_guard.py:193-196` encodes the bug as the expected behaviour.** The
case creates `260-.reserved`, writes `260-another-fresh-topic-someone-reserved.md`, and asserts
**exit 2**, labelled "id already claimed by a `*-.reserved` marker blocks". That is precisely the
sanctioned reserve-then-write sequence. Anyone who fixes the guard will see that test go red and may
reasonably conclude they broke something and revert.

So the fix is two files, not one, and the test change is not optional.

## Approach

1. Reproduce it first, the same way above. It is a two-command reproduction, do not skip it.
2. In the id-uniqueness check, when the colliding entry is a `<id>-.reserved` marker AND the path
   being written is `<same id>-<slug>.md` in the same backlog directory, allow the write. A marker
   for a DIFFERENT id, and a real `.md` file for the same id, both still block.
3. Consider whether the guard should also delete the marker on a successful write, so the caller
   cannot forget step 3. Probably not: the hook is advisory and a PreToolUse hook deleting files is a
   surprising side effect. Decide explicitly and record the reasoning either way.
4. **Invert the existing test case at `hooks/test_todo_duplicate_guard.py`:193-196** so it asserts
   exit 0 for reserve-then-write, and keep a separate case asserting exit 2 for a write whose id
   collides with a DIFFERENT id's marker. Do not merely add a new case beside the old one; the old
   one currently states the opposite and both cannot pass.
5. The invariant to lean on: `reserve-todo-id.ps1` uses an atomic no-overwrite rename, so at most one
   reservation marker can exist per id at any moment. Any marker sharing `target_id` is therefore
   provably the caller's own reservation, never a genuine second claimant. That is what makes the
   carve-out safe rather than a hole.

## Acceptance

- [ ] The reserve-then-write flow from `ai-todos-format.md` completes without a denial
- [ ] A genuine id collision (real `.md`, or another id's marker) still blocks
- [ ] An in-place rewrite of an existing todo still passes, no regression on `492`'s cases
- [ ] The new case is in `hooks/test_todo_duplicate_guard.py` and `python ci/run_all.py` exits 0
- [ ] The delete-on-write question from step 3 has a recorded answer

## Notes

- Worth 8: it fires on the single most common backlog write path, the denial message actively
  misleads by recommending the thing that caused it, and the only workaround reopens the race
  `reserve-todo-id.ps1` exists to close. Cheap to fix.
- Parent: `done/492-todo-duplicate-guard-checks-content-but-not-id-uniqueness.md`. The check itself is
  correct and worth keeping; this is a missing carve-out, not a reason to revert it.
- Done via /mega-todos 2026-09-01 (32a66cd): the id guard now accepts the reserved id it issued while still blocking a genuine two-todo collision, both directions covered by tests.
