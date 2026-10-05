<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-09-29; grepped backlog + done/ for "client-push-gate" and "client-repo", no hits (the hook was created 2026-09-29, commit eddcdc6). -->
# client-push-gate resolves the wrong repo for `cd X && git push` and chained `git -C`

**Type:** task
**Origin:** ai

## Goal
`hooks/client-push-gate.py` checks the repo that the `git push` in the command will actually run
in, including when the same command `cd`s first or has an unrelated `git -C` call before the push.

## Context
The gate resolves its target at `hooks/client-push-gate.py:63`:
`target = git_dash_c_path(command) or payload.get("cwd") or "."`. Two bypasses, both letting a
client-repo push through with no clearance marker:

1. **`cd` earlier in the same command.** From a personal cwd, `cd C:/Users/tecno/Desktop/Projects/zng-app && git push`
   is checked against the pre-`cd` cwd (payload `cwd`), finds a personal repo, and exits 0.
   `hooks/git-workdir-guard.py:17-19` already handles this shape ("A `cd`/Set-Location earlier in
   the SAME command ... pins the effective cwd") - reuse its approach rather than re-deriving.
2. **Chained `git -C`.** `git_dash_c_path` (`client-push-gate.py:39-54`) returns the `-C` of the
   FIRST `git` token in the command, not the one attached to `push`. So
   `git -C C:/personal status && git push` (run from a client cwd) resolves to the personal repo.

Not a finding, checked 2026-09-29: using payload `cwd` as the fallback is correct. Per
`git-workdir-guard.py:11-12` it is the live shell cwd, which is exactly where a bare `git push`
executes. The code-check reviewer flagged it as drift-unsafe; that reasoning is inverted.

## Approach
- Make `git_dash_c_path` return the `-C` value of the `git` invocation whose subcommand is `push`
  (walk each `git` token the way `push-read-gate.py`'s `is_git_push_invocation` does, and only
  return `-C` from the invocation that reaches `push`).
- Detect a leading `cd <path>` / `Set-Location <path>` segment before the push segment and use that
  path, mirroring `git-workdir-guard.py`.

## Acceptance
- New cases in `hooks/test_client_push_gate.py`: `cd "<client>" && git push` from a personal cwd
  is denied; `git -C "<personal>" status && git push` from a client cwd is denied;
  `git -C "<client>" status && git push` from a personal cwd passes.
- `python hooks/test_client_push_gate.py` prints ALL PASS.
