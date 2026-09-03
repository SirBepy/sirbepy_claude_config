<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: searched the backlog for claim-todo / batch-claim; this is a signature mismatch between auto-do-todos' Step 6 text and the script's own param type, not a duplicate of any open item. -->
# /auto-do-todos documents the batch-claim call in a form claim-todo.ps1 rejects

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the documented batch-claim invocation actually run, so every `/auto-do-todos` run stops
burning a failed tool call on it.

## Context

Hit on 2026-09-03 during an `/auto-do-todos` run in `C:\Users\tecno\Desktop\Projects\countoff`.

`~/.claude-personal/skills/auto-do-todos/SKILL.md`, Step 6, says:

> **Claim the whole AUTO queue in one call before grinding it**, per the contract's batch-claim
> form: `claim-todo.ps1 -Id <id1>,<id2>,...` for every id about to run in this pass

Written literally, that is PowerShell array syntax. `claim-todo.ps1` declares `-Id` as `[string]`,
so passing `01,02,03,07,12,13,18` fails argument binding before the script body runs:

```
claim-todo.ps1 : Cannot process argument transformation on parameter 'Id'.
Cannot convert value to type System.String.
    + FullyQualifiedErrorId : ParameterArgumentTransformationError,claim-todo.ps1
```

The form that works is a single QUOTED comma-separated string, which the script splits itself:

```powershell
& "C:\Users\tecno\.claude-personal\skills\close\claim-todo.ps1" -Id "01,02,03,07,12,13,18"
```

Verified working the same day - it claimed all seven ids in one call.

The wording is ambiguous rather than flatly wrong (`<id1>,<id2>,...` could be read either way), but
it reads as an array to anyone writing PowerShell, and the failure costs a round trip on every run
that claims more than one todo. Step 6 also calls this "the one remembered call the contract
requires", so it is on the hot path by design.

## Approach

Pick one, they are not equivalent:

1. **Fix the docs** - cheapest. Change Step 6's example to the quoted form, e.g.
   `claim-todo.ps1 -Id "<id1>,<id2>,..."`, and check whether
   `~/.claude/skills/close/ai-todos-format.md` states the batch form too; if so, fix it in both
   places so they cannot drift apart.
2. **Fix the script** - more forgiving. Change `claim-todo.ps1`'s `-Id` to `[string[]]` and join
   internally, so BOTH forms work. Check `complete-todo.ps1` for the same parameter shape while
   there, since it takes an `-Id` too and a caller will reasonably assume they match.

Recommended: **(2), plus the doc fix from (1)**. Accepting an array is what a PowerShell caller will
try first, and making the two scripts agree removes the trap rather than documenting around it.

## Acceptance

- `claim-todo.ps1 -Id 01,02,03` and `claim-todo.ps1 -Id "01,02,03"` both claim three todos.
- `/auto-do-todos` Step 6's example, pasted verbatim, runs without an argument-binding error.
- Whatever form ends up canonical is written the same way in every file that documents it.

## Notes

Found by `/close`'s Phase 1 retrospective, not by a review pass - it surfaced as a failed tool call
mid-run and was worked around at the time rather than filed, which is exactly the class of small
recurring friction that never gets fixed unless it is written down.
