<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todos 873, 874 and 893 all landed 2026-09-04 and are in done/. This is the REGRESSION found by /code-check immediately after them, not a refile of any of the three. -->
# _hooklib consolidation regressed in four places the same day it landed

**Type:** task
**Origin:** ai

## Goal

Finish the `hooks/_hooklib.py` consolidation that todos 873, 874 and 893 started, by removing the
private copies that either survived those passes or were reintroduced by hooks written in parallel
with them.

## Context

Found 2026-09-04 by `/code-check` over the `/mega-todos` run diff (`5d6b261..HEAD`). Three
consolidation todos landed that day, but several hooks were being written by other agents at the
same time and could not see each other's work, so the shared helpers were re-derived rather than
imported. This is the honest cost of a wide parallel run and it is worth one cleanup pass.

Confirmed instances, each verified at `file:line`:

1. **`hooks/git-workdir-guard.py:43,110-122`** hand-rolls `GIT_TIMEOUT_SECONDS = 10` and
   `repo_root()`, functionally identical to `_hooklib.git_repo_root()` at `_hooklib.py:124-143`.
   The file already imports `strip_quotes` from `_hooklib` at :37, so the import path is open. Both
   the todo-874 builder and the todo-880 builder independently flagged this in their reports.
2. **`hooks/shell-content-write-guard.py:102,111-126`** has `_repo_root()`, again the same shape,
   differing only in returning a resolved `Path` and using a **5-second** timeout against the
   shared 10. No reason for the divergence is stated anywhere; decide which is right rather than
   preserving both.
3. **`basename()` in four sibling guards** - `git-workdir-guard.py:63-64`,
   `flutter-workdir-guard.py:74-75`, `dev-backend-guard.py:95-96` are byte-identical
   (`re.split(r"[\\/]", tok)[-1].lower()`), while `dev-server-guard.py:43-44` differs: no
   case-folding, different split. That silent inconsistency is the real finding, not the
   duplication.
4. **The allow-with-warning JSON block** - `todo-duplicate-guard.py:257-269` (`allow()`) and
   `list-peers-pre-edit-guard.py:117-128` (`emit_warning()`) both hand-build the same
   `{hookSpecificOutput: {permissionDecision: "allow", permissionDecisionReason}}` payload. The
   newer file's own comment names the older one as the pattern it copied instead of importing.
   `_hooklib` already exports `ask()` and `deny()`, so the shape is established.

Lower severity, same class: `COMMAND_START_RE` is identical in `cargo-test-pipe-guard.py:78` and
`shell-content-write-guard.py:198`, and the former's comment says it was "not moved to _hooklib
since only this file needs it" - which the second copy disproves.

## Approach

1. Point 1, 2 and 4 at `_hooklib` directly. For 2, settle the 5s vs 10s timeout question and write
   the answer as a one-line reason next to the constant.
2. For 3, decide whether case-folding is wanted before centralising - `dev-server-guard.py` is the
   odd one out and it may be deliberate. Reconcile first, THEN extract one `basename()`.
3. Move `COMMAND_START_RE` into `_hooklib` and delete the comment that argues against doing so.
4. `ci/run_all.py`'s `check_hook_imports()` exec-loads every `_hooklib` importer, so a broken import
   fails loudly there. Each touched guard also has a `hooks/test_*.py` suite - run them all.

## Acceptance

- Each of the four helpers is defined exactly once in `hooks/`, verified by grep.
- Every touched guard's `hooks/test_*.py` suite passes unmodified, and `python ci/run_all.py`
  exits 0.
- The `basename()` case-folding divergence is either eliminated or documented as deliberate.

## Notes

- Filed by /mega-todos on 2026-09-04 from the run's own `/code-check` pass.
- Fixed in 80d9033: git_repo_root, basename, COMMAND_START_RE/is_command_position and a new allow_with_warning are now shared in _hooklib. Settled the two open divergences explicitly - the 5s timeout unified to the shared 10s, and dev-server-guard's missing .lower() judged NOT deliberate (both call sites already lowered the result).
