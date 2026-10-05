<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-05; grepped backlog + done/ + dropped-findings.log for "resolve_bash" and "Resolve-BashExe", no hit. -->
# Decide whether the Git-for-Windows bash resolver gets one shared home

**Type:** task
**Origin:** ai

## Goal
A decision, recorded here, on whether the "find Git-for-Windows bash, not the WSL shim" logic
keeps living in three copies or moves to one shared module.

## Context
Found by the 2026-10-05 pre-push /code-check (class 3, judgment: never auto-applied).
- `skills/commit/split-hunks.py:67` `resolve_bash()` (new in f582722), whose own docstring says it
  is "duplicated narrowly rather than imported, since hooks/ is out of scope for this script to
  depend on".
- `hooks/commit-guard.py:156` `resolve_bash()`, the original, same candidate path list.
- `skills/close/archive-and-commit-todo.ps1:216` `Resolve-BashExe`, the same logic in PowerShell.

## Approach
Pick one:
1. Keep the copies and note the decision in each docstring, so the next review stops flagging it.
2. Extract a small Python module importable from both `skills/` and `hooks/` for the two Python
   copies; the PowerShell copy stays.

## Acceptance
- The chosen option is applied, and `python ci/run_all.py` passes.
