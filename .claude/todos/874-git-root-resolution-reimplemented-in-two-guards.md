<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Git-root resolution is reimplemented in two guards instead of living in hooklib

**Type:** task
**Origin:** ai

## Goal

Give `hooks/_hooklib.py` a single git-root resolver and have both guards use it, instead of two
independent `git rev-parse --show-toplevel` wrappers with their own timeout constants.

## Context

Found 2026-09-01 by `/code-check` over `0b471f0..HEAD`, Step 2 DRY pass, in an isolated review
subagent.

- `hooks/list-peers-pre-edit-guard.py:51` defines `repo_root()`.
- `hooks/ui-screenshot-reminder.py:145` defines `resolve_repo_root()`.

Both shell out to `git rev-parse --show-toplevel`, both wrap it in try/except with a subprocess
timeout, and each declares its own `GIT_TIMEOUT_SECONDS = 10`. `_hooklib.py` offers no such helper,
so the second one was added in this same range as an independent implementation rather than a
reuse.

Two constants that must agree and are declared separately is the drift mechanism worth naming here:
raising the timeout in one hook because a large repo was slow leaves the other one still failing at
ten seconds, and a hook that cannot resolve its repo root fails open silently by design.

## Approach

1. Read both implementations and diff their behaviour, not just their shape. Confirm they agree on
   what to do when the command fails, when cwd is not a repo, and when it times out. If they
   disagree, decide which behaviour is correct before merging them; a silent merge would pick one
   at random.
2. Add one resolver to `hooks/_hooklib.py` with a single timeout constant, and point both guards at
   it.
3. `_hooklib.py` is imported by 19 hooks; `ci/run_all.py`'s hook-import smoke check must stay green.

## Acceptance

- One git-root resolver exists in the repo, in `hooks/_hooklib.py`, with one timeout constant.
- Both guards use it and neither declares its own.
- `hooks/test_list_peers_pre_edit_guard.py` and `hooks/test_ui_screenshot_reminder.py` pass
  unmodified.
- `python ci/run_all.py` exits 0, hook-import smoke included.

## Notes

Pairs with todo 873, which moves a different duplicated pair out of the same two files.
