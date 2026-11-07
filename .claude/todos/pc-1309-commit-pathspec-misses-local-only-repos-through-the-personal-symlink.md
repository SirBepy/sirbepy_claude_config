<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# commit-pathspec misreads local-only-tests repos when called through the .claude-personal path

**Type:** skill-improvement
**Origin:** ai
**Summary:** `commit-pathspec.sh` should give the same verdict whichever skills path it is called through, so a local-only-tests repo is never refused for having no test in the pathspec.

## Why

Seen 2026-11-04 in zng-admin. `/commit`'s loaded skill header reports its base directory as `C:\Users\tecno\.claude-personal\skills\commit`, so Claude called `bash /c/Users/tecno/.claude-personal/skills/commit/commit-pathspec.sh`. It refused with `[coverage-tests-check] REFUSED` though zng-admin is in `refs/local-only-tests.txt` and a local test had just been written. The same command through `/c/Users/tecno/.claude/skills/commit/commit-pathspec.sh` printed `clean (local-only-tests repo: ...)` and committed `6a31bd2`.

`~/.claude-personal/skills` is a symlink to `~/.claude/skills`, and the script body is identical. The lookup is `local_only_tests_path="$dir/../../refs/local-only-tests.txt"` plus `python "$dir/../../hooks/_client_repo.py"` (`commit-pathspec.sh:1065-1069`). Called through the symlink, `$dir/../../hooks/_client_repo.py` may resolve to a `~/.claude-personal/hooks` that does not exist, which reads as "not local-only". UNVERIFIED: which of the two lookups failed; `~/.claude-personal/refs/local-only-tests.txt` exists and lists the zng repos, the hooks path was not checked.

The failure is quiet in the wrong direction: it invites `--force coverage-tests`, or committing a test the repo must not track.

## Goal

The script resolves its own real path before building `$dir`, so the verdict does not depend on the path it was called through. Check the other skills that derive paths the same way.

## Approach

1. Reproduce from a local-only repo with a recently touched untracked test, calling the script through both paths.
2. In `skills/commit/commit-pathspec.sh`, resolve `$dir` with `pwd -P` or `readlink -f` on `$0`.
3. Grep `skills/` for other `$dir/../../` lookups and fix the same way.
4. Add a case to the script's tests covering a symlinked call.

## Acceptance

- Both paths give the same `[coverage-tests-check]` verdict in a local-only repo.
- `python ci/run_all.py` passes.

## Verify

- [ ] Run the two commands from Approach 1 with a harmless pathspec and compare output up to the commit step.
