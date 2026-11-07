<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1297 is about pipes inside quotes, pc-1217 about ticket posting at night; neither covers a Git Bash cd path -->
# commit-window-guard lets commits and pushes through after a Git Bash `cd /c/...`

**Type:** skill-improvement
**Origin:** ai
**Summary:** The client-repo night window is not enforced when a Bash tool command starts with `cd /c/Users/...`, because the guard stops recognising the repo as a client repo.

## Why

Joe's rule is that nothing lands in a client repo from 23:00 to 10:59 without his OK. A command shape Claude uses routinely skips the check without any message.

## Goal

`hooks/commit-window-guard.py` gates a commit or push the same way whether the command reaches the repo through no `cd`, a Windows `cd C:/...`, or a Git Bash `cd /c/...`.

## Context

Found 2026-11-03 at 23:2x in a zng-admin gate chat. Four `git commit` calls of a `/commit fold`, each starting `cd /c/Users/tecno/Desktop/Projects/zng-admin;`, ran with `GIT_AUTHOR_DATE`/`--date` and no allow marker, and were not denied. The `git push` right after them through PowerShell, with no `cd`, was denied. Joe had waived the window for that session, so nothing shipped against his wishes, but the guard did not know that.

Probe that reproduces it: run the hook directly with `{"session_id":"probe-no-allow","cwd":"C:/Users/tecno/Desktop/Projects/zng-admin","tool_name":"Bash","tool_input":{"command":...}}` on stdin, inside the window. Results on 2026-11-03 at 23:26:

| Command | Exit |
| --- | --- |
| `git commit -q -m "x" -- a.txt` | 2 (denied) |
| `cd C:/Users/tecno/Desktop/Projects/zng-admin; git commit ...` | 2 (denied) |
| `cd /c/Users/tecno/Desktop/Projects/zng-admin; git commit ...` | 0 (allowed) |
| `cd /c/Users/tecno/Desktop/Projects/zng-admin; git push origin develop` | 0 (allowed) |

UNVERIFIED cause: the hook's docstring says a `cd` pins the cwd for later segments, and `ABS_PATH_RE` at `hooks/commit-window-guard.py:95` treats `/c/...` as absolute, so Windows Python probably fails to resolve it to a repo and the client check falls through. Would check by tracing the pinned cwd through `_client_repo.py`.

UNVERIFIED: the docstring says this pinning is the "same rule as push-gate.py", so `hooks/push-gate.py` and the other guards that pin a cwd may have the same gap. Would check by running the same probe against each.

Also a mismatch to settle at the same time: `/commit fold`'s recipe in `skills/commit/SKILL.md` keeps the original timestamps through `--date` and `GIT_*_DATE`, and the guard refuses those inside the window even with an allow marker ("an approved night commit still carries its real time"). A fold during an approved night session therefore has no path that satisfies both.

## Approach

1. Normalise a Git Bash drive path (`/c/...` to `C:/...`) wherever the guard resolves a pinned cwd, and fail towards gating when a pinned path cannot be resolved.
2. Add the four cases above to the guard's self-test.
3. Run the same probe against the other cwd-pinning hooks and fix any that match.
4. Decide the fold case: either the guard allows the original dates of a commit being replayed under an allow marker, or the recipe documents using real timestamps during the window.

## Acceptance

The `cd /c/...` commit and push cases exit 2 in the window without an allow marker, `python ci/run_all.py` passes, and `/commit fold` names one working path for a fold inside an approved window.

## Notes

- Root cause: _hooklib.git_repo_root could not resolve a Git Bash /c/... path on Windows, so commit-window-guard (and push-gate, git-workdir-guard) fell through as not-a-client-repo. Fixed with normalize_msys_path in git_repo_root/git_common_dir plus a cwd-repo fallback for unresolvable targets in commit-window-guard and push-gate. Tests: test_commit_window_guard.py 'Git Bash cd /c/...' cases (5 red on HEAD), test_push_gate.py unresolvable-target cases. Fold decision: guard keeps refusing dates in the window (Joe's rule); skills/commit/SKILL.md fold recipe now says wait for 11:00.
