<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 267 and 311 are about blocking shell command CHAINING, 316 is about hook TEST files duplicating a loader harness. None concern a runtime import failure or fail-closed blast radius. Shared vocabulary only. -->
# Editing a hook's shared module bricks Bash AND PowerShell for every live session

**Type:** task
**Origin:** dev

## Goal

Stop a mid-write `hooks/_*_shared.py` from failing every shell call in every
concurrent session. The guard failing closed is correct; the blast radius is not.

## Context

Observed 2026-09-04 ~10:01-10:03 from two independent Conductor sessions in the
`claude_usage_in_taskbar` project, simultaneously:

```
[destructive-command-guard] FATAL: cannot import _hooklib (cannot import name
'GIT_STASH_ANCHOR_RE' from '_destructive_guard_shared'); blocking to avoid
silently disabling this guard.
```

Both Bash and PowerShell were rejected, so a session had no shell at all for
roughly two minutes. One was mid-`/commit` and stalled with 11 verified files
uncommitted in a shared tree next to an active peer.

It self-cleared. Checked afterwards: `GIT_STASH_ANCHOR_RE` is defined at
`hooks/_destructive_guard_shared.py:29`, `destructive-command-guard.py:120`
imports only `verb_segments`, and running the guard directly exits 0. So the
window was a partially-written file, almost certainly a session editing
`_destructive_guard_shared.py` while others were running commands.

The misleading part is worth keeping: the error names a symbol the importing
file does not even import. That sends you hunting a broken import in
`destructive-command-guard.py` that was never there, and a `grep` during the
window finds the symbol nowhere, which reads as permanent breakage rather than a
half-written file. One session concluded exactly that and escalated to the dev.

## Approach

The guard must keep failing closed, so do not touch that. Cheapest first:

1. **Make the message say what it is.** On `ImportError` specifically, name the
   likely cause ("a shared hook module may be mid-write; retry once before
   treating this as broken"). Costs nothing, removes the wrong conclusion above.
2. **Retry once before failing.** On `ImportError` only, sleep ~150ms and
   re-import. A half-written file is gone within a second; a genuinely broken one
   still fails. Do NOT retry other exception types, which would mask real breakage.
3. **Write shared hook modules atomically.** Write to a temp file in the same
   directory then `os.replace()` onto the target, so no reader sees a partial
   file. The actual root fix, but it only binds writers that go through a helper,
   so it needs a documented rule too.

1 and 2 together are probably enough. 3 is more correct and less enforceable.

## Acceptance

- The guard still blocks when the module is genuinely broken (verify by
  temporarily breaking a symbol it really imports, then restoring).
- A transient partial read no longer surfaces as a hard block, or at minimum
  surfaces with a message naming retry as the first move.
- No path where an `ImportError` silently disables the guard. Failing closed
  stays the default; only the retry count and the wording change.

## Notes

- Do not "fix" this by removing the fail-closed behaviour. A guard that skips
  itself on import failure is worse than a two-minute outage.
- Same class, worth checking while here: any global `PreToolUse` hook edit is
  live for every running session the instant it is saved. Check whether other
  hooks import from shared modules and would fail identically.
- Joe authorised fixing the hook on 2026-09-04 in a project session, in response
  to this outage. The code turned out to need no fix, so the finding is filed
  here rather than edited in place.

- CAUSE IDENTIFIED, added by the `/mega-todos` run in `~/.claude` on 2026-09-04.
  This outage was that run's wave-2 lane for todo 911, which split
  `hooks/destructive-command-guard.py` into per-concern modules and CREATED
  `hooks/_destructive_guard_shared.py` in the process. Receipt:
  `git log --diff-filter=A -- hooks/_destructive_guard_shared.py` returns exactly
  one commit, `b3803ef` at 12:11:55, so the file did not exist before then and the
  import error could not have come from anything else.
  The `~10:01-10:03` timestamp above is therefore wrong; the real window is
  between that lane's first write and `b3803ef`. Trust the mechanism described
  above, not the clock reading.
  This makes the finding stronger, not weaker: a routine, fully-verified,
  green-CI refactor of a guard took every concurrent session's shell away for
  minutes, with no warning to anyone and no way for the affected sessions to tell
  a transient partial read from real breakage. Nothing about that lane was done
  wrong, which is exactly why the blast radius needs fixing rather than the
  process around it.
  Worth weighing while fixing: an orchestrator running a wide parallel wave could
  also serialise edits to shared hook modules, but that only binds runs that know
  to do it. Options 1 and 2 above bind everyone.
