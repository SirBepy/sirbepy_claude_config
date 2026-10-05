<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=a67f26bc -->
<!-- duplicate-checked: 2026-09-29; grepped backlog + done/ for "client-push-gate" and "client-repo", no hits (the hook was created 2026-09-29, commit eddcdc6). -->
# client-push-gate resolves the wrong repo for `cd X && git push` and chained `git -C`

**Type:** task
**Origin:** ai

## Goal
`hooks/push-gate.py` checks the repo that the `git push` in the command will actually run
in, including when the same command `cd`s first or has an unrelated `git -C` call before the push.

## Context
Updated 2026-10-05: the gate was renamed from `client-push-gate.py` and now gates every repo, not
only listed client repos. The bypass survives the change in a narrower form: it now needs the
wrongly resolved repo to have a cleared HEAD, rather than merely being personal.

The gate resolves its target at `hooks/push-gate.py:113`:
`target = git_dash_c_path(command) or payload.get("cwd") or "."`. Two bypasses, both letting a
push through with no clearance marker for the repo actually pushed:

1. **`cd` earlier in the same command.** From a cwd whose HEAD is already cleared, `cd C:/Users/tecno/Desktop/Projects/zng-app && git push`
   is checked against the pre-`cd` cwd (payload `cwd`), finds that cleared HEAD, and exits 0.
   `hooks/git-workdir-guard.py:17-19` already handles this shape ("A `cd`/Set-Location earlier in
   the SAME command ... pins the effective cwd") - reuse its approach rather than re-deriving.
2. **Chained `git -C`.** `git_dash_c_path` (`push-gate.py:48`) returns the `-C` of the
   FIRST `git` token in the command, not the one attached to `push`. So
   `git -C C:/cleared status && git push` (run from an uncleared cwd) resolves to the cleared repo.

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
- New cases in `hooks/test_push_gate.py`: `cd "<uncleared>" && git push` from a cleared cwd
  is denied; `git -C "<cleared>" status && git push` from an uncleared cwd is denied;
  `git -C "<uncleared>" status && git push` from a cleared cwd passes.
- `python hooks/test_push_gate.py` prints ALL PASS.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), lane D2, test-first (RED against HEAD, then GREEN).
