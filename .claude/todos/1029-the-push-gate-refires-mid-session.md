<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=bf99d142 -->
<!-- duplicate-checked: read 1005 in full. It owns the "a shell cat does not satisfy the gate" half and I folded today's second sighting into its Notes. This is the other half: the gate firing TWICE in one session, which 1005's own last acceptance line assumes cannot happen. Different symptom, different suspected cause (marker files disappearing, not read detection). 467 created the gate and is about the missing check. 365 is about malformed marker paths from bad call sites, not about markers being deleted. -->
# The push-read gate refires mid-session, and its markers are missing from disk

**Type:** bug
**Origin:** ai

## Goal

`hooks/push-read-gate.py` should gate the FIRST `git push` of a session and then stay out of the
way, which is what its own docstring promises. Today it gated twice in one session.

## Context

Observed 2026-09-26 from a `countoff` session (`57678915-3e08-4468-8a2d-7c1704da3989`).

`push-read-gate.py`'s module docstring states the contract:

> Once a push is allowed, a second marker is written so every later push in the session is
> unguarded - this is a FIRST-push gate only, never a per-push one.

What actually happened, in one unbroken session:

1. `git push` blocked with the "this session's first `git push`" message.
2. Read `snippets/auto-commit.md` with the `Read` tool. Push succeeded.
3. Hours later, **same session**, `git push` blocked again with the identical "first `git push`"
   message.
4. Read it with the `Read` tool again. Push succeeded again.

(Step 1 was preceded by a `cat` of the same file that did not satisfy the gate. That part is
[[1005-push-read-gate-only-counts-read-tool-reads]], not this todo.)

**The disk state is the lead.** After two successful pushes in that session,
`hooks/.session-markers/` contained no `read-auto-commit-*` and no `push-gate-passed-*` file at
all, for any session. Nine bare `<session-id>` files and two `silent-turns-<session-id>` files,
nothing else.

Two candidate causes, both **unverified**, listed so whoever picks this up tests rather than
assumes:

- **A prune collision.** `hooks/write-session-marker.ps1` prunes "every OTHER session marker whose
  session is provably gone", keyed on the filename being a session id. A file named
  `read-auto-commit-<uuid>` has no registry record under that literal name, so a liveness lookup
  finds nothing and deletes it. That session ran `write-session-marker.ps1` between the first and
  second push and its output said `Pruned 2 dead session marker(s)`. Suggestive, not proof: nobody
  captured a directory listing immediately before and after that call.
- **The markers are never written.** The allow path may simply not reach its marker write, in which
  case the docstring describes an intention rather than the code.

Both are testable in minutes; neither has been tested.

## Approach

1. **Identify the cause before changing anything.** In a scratch session: read
   `snippets/auto-commit.md` via the `Read` tool, list `hooks/.session-markers/`, push, list again.
   If the two prefixed markers appear, the write works and the prune is the suspect; then run
   `write-session-marker.ps1` and list a third time to see whether they vanish.
2. If it is the prune, the fix belongs in `write-session-marker.ps1`, not in the gate: it should
   only consider files whose name is a bare session id and leave any prefixed marker to its owner.
   Note `silent-turns-*` has the same exposure and may already be losing state quietly, so check
   whether anything depends on it surviving.
3. If it is the write, fix the allow path in `push-read-gate.py`.

Do not "fix" this by widening the gate to fire once per process, and do not remove it. It caught
nothing wrong today, it just charged twice for the same toll, and the incident behind it (todo 467,
six commits pushed unasked) is still live.

## Acceptance

- The cause named, with the before/after directory listings that identify it.
- Two pushes in one session with the file read once: the second is not gated. Paste both.
- If the prune was the cause: a prefixed marker demonstrably survives a `write-session-marker.ps1`
  call, shown by listing the directory either side of it.
- `python ci/run_all.py` passes.

## Notes

- Root cause confirmed by code read (/cleanup-todos 2026-10-05, folded from archived duplicate 1070): `hooks/write-session-marker.ps1` Remove-DeadSessionMarkers lists every file in `.session-markers/` and keys liveness on the bare filename, so any prefixed marker (`push-gate-passed-<id>`, `read-auto-commit-<id>`) never matches a live session id and is pruned on the next marker write, the session's own included.
