<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=1, content-hash=e97d156e -->
# Two session-marker writes landed on malformed paths, leaving strays `git status` never stops showing

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the commit-guard session-marker write either land in `hooks/.session-markers/<session_id>` or
fail loudly, instead of silently creating a sibling file that looks like a marker, is never read,
and sits untracked in `git status` forever.

## Context

Observed 2026-08-17 in this repo, during a named-subset `/auto-do-todos` run. `git status --short`
carries two untracked files that are neither ignored nor readable by the guard:

```
?? hooks/.session-markers$CLAUDE_CODE_SESSION_ID
?? hooks/.session-markerseca89f66-3640-47df-8ea7-decea14d89cf
```

Both are the marker `/commit` step 0 writes, on a wrong path, in two different ways:

1. **Unexpanded variable.** `$CLAUDE_CODE_SESSION_ID` survived literally into the filename. That
   session wrote NO usable marker: there is no correspondingly-named entry in
   `hooks/.session-markers/`.
2. **Missing path separator.** `hooks/.session-markers` + the session id concatenated with no `/`.
   This one is less harmful than it looks: `eca89f66-3640-47df-8ea7-decea14d89cf` also exists
   correctly inside `hooks/.session-markers/`, so that session evidently wrote twice and only the
   stray survived as noise.

`hooks/commit-guard.py:43` reads `SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"`, so nothing
outside that directory is ever consulted. `.gitignore` ignores `hooks/.session-markers/` with a
trailing slash, which by design does not match either stray - hence the permanent `git status` noise.

UNVERIFIED: whether case 1's session went on to be blocked by the guard, or wrote a correct marker
later in some other way. The transcript for it is not in hand; the filename alone proves only that
one write went to the wrong path.

Why it is worth fixing rather than deleting the two files by hand: `/commit`'s own procedure commits
strictly by pathspec and requires checking the file list against `git status`, so permanent untracked
entries are noise in the one output meant to be scanned carefully. This is the same complaint todo
354 just closed for `hooks/.claude/`, arriving by a different route.

## Approach

1. Find the two writers. `/commit` step 0 and `~/.claude/skills/mega-todos/SKILL.md`'s injected
   commit block both hand a marker-write command to an agent; the doctrine's builder preamble may
   too. Grep for `.session-markers` and `.commit-marker` across `skills/` and `refs/`.
2. Case 1 is a shell mismatch: the documented recipe is PowerShell (`$env:CLAUDE_CODE_SESSION_ID`),
   and a literal `$CLAUDE_CODE_SESSION_ID` filename is what a Bash-side write of the PowerShell
   form produces. Decide whether the recipe should be shell-agnostic or explicitly PowerShell-only,
   and say which in the skill text rather than leaving it inferable from the syntax.
3. Case 2 argues for not building the path by string concatenation at the call site at all. Prefer
   a tiny script (`hooks/write-session-marker.ps1`, or a flag on an existing helper) that owns the
   directory and the separator, the same way `claim-todo.ps1` owns the claims mutex - the call site
   then cannot get the path wrong.
4. Delete the two existing strays once the writer is fixed. Do NOT add a `hooks/.session-marker*`
   glob to `.gitignore` as the fix: that hides the symptom, and a hidden malformed marker is worse
   than a visible one, since a session whose marker never landed is one that will be blocked from
   committing with no clue why.

## Acceptance

- A marker write from either shell lands in `hooks/.session-markers/<session_id>` or errors.
- `git status --short` in `~/.claude` shows no `hooks/.session-marker*` stray.
- `hooks/commit-guard.py` still blocks a raw `git commit` from a session that wrote no marker
  (verify deliberately, so the fix is not confused with disabling the guard).

## Notes

- Filed 2026-08-17 by `/auto-do-todos` as an out-of-scope finding from its own `git status`, per the
  delegation doctrine's rule that the orchestrator files these, not the builder.
- Related: [[341-builder-cleanup-deleted-a-live-commit-marker]] in `done/`, which moved markers into
  `hooks/.session-markers/` in the first place, and [[354-hooks-dot-claude-runtime-artifact-is-untracked-and-unignored]]
  in `done/`, the same `git status`-noise complaint from a different source.
