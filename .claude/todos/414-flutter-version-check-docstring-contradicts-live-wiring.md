<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# flutter-version-check.sh's docstring says it is unwired, but settings.json wires it

**Type:** task
**Origin:** ai

## Goal

Make `hooks/flutter-version-check.sh`'s own leading comment agree with reality, so a future reader
does not conclude the hook is dead code and delete or ignore it.

## Context

Found 2026-08-19 during a full inventory sweep of `~/.claude` (the baseline pass of an open-source
`.claude` repo harvest). The hook's leading comment states it is a "SessionStart-style hook
(registration is a separate step; this file is not wired into settings.json yet)".

`settings.json` actually DOES wire it: `SessionStart` -> `matcher: startup` -> this script, with a
15s timeout. So the file's own documentation contradicts the live config.

This is the second instance of a stale-docstring class of problem in `hooks/` (see the EXPERIMENTAL
hook separation issue filed alongside this one). A docstring that lies about wiring is worse than no
docstring: it invites a cleanup pass to delete a live guard.

## Approach

1. Read `hooks/flutter-version-check.sh`'s leading comment block and `settings.json`'s `SessionStart`
   entry, and confirm the contradiction still holds (it may have been fixed since).
2. Rewrite the comment to state what is true: which event it is wired to, which matcher, the
   timeout, and what it does. Keep it inside the global comment budget (2 lines typical, 4 hard cap).
3. Sweep the other hooks for the same class of error while in there: any hook whose docstring claims
   a wiring state that `settings.json` contradicts, in either direction (claims wired but is not,
   claims unwired but is). Fix each one found, and report the count.

## Acceptance

- `hooks/flutter-version-check.sh`'s comment names its real event, matcher and timeout.
- A grep of every hook's docstring against `settings.json`'s wired entries produces no remaining
  contradictions.
- No behavior change: the hook itself is not edited, only its comment.

## Notes

Do not "fix" this by unwiring the hook. It is wired on purpose; the comment is what is wrong.
