<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits (222, 256, 420, 70, 806) cover push, lint-staged, guard timing, cherry-pick and foreign hunks; none covers a commit landed via commit-tree + update-ref -->
# split-hunks.py's commit-tree path skips the commit-guard hook

**Type:** task
**Origin:** ai

## Goal

Every commit Claude creates passes the same marker gate and prefilter backstop, whether it goes
through `git commit` or through `git commit-tree` + `git update-ref`.

## Context

Todo 1068 (done, f582722) added `skills/commit/split-hunks.py commit`, which builds a commit in a
private GIT_INDEX_FILE and lands it with a compare-and-swap `git update-ref`. `hooks/commit-guard.py`
only recognises a `git commit` token, so this path silently skips the session-marker requirement and
the hook's own prefilter re-run. The builder mitigated it by having split-hunks.py run
`prefilter-gate.sh` itself (fail-closed on a flag, fail-open only if the gate cannot run), but the
marker gate is still bypassed, and any other script that uses commit-tree gets no check at all.

## Approach

1. Decide whether commit-guard.py should also match `git commit-tree` and `git update-ref HEAD`
   (and `refs/heads/*`) invocations, requiring the same session marker.
2. If yes, extend the matcher with tests for each form, and confirm split-hunks.py still works
   with the marker present.
3. Keep split-hunks.py's own prefilter run either way; it covers callers outside Claude Code.

## Acceptance

- A raw `git commit-tree` + `git update-ref HEAD` from a session with no marker is blocked.
- `split-hunks.py commit` from a marked session still lands, verified in a scratch repo.
