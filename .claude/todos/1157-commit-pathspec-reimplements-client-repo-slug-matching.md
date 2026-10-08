<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; no live todo covers origin-slug matching; done/1111 is commit-window-guard's tokenizer duplication, a different helper -->
# commit-pathspec.sh reimplements `_client_repo.py`'s origin-slug matching in bash

**Type:** task
**Origin:** ai

## Goal

One implementation of "does this repo's origin match a line in a `refs/*.txt` repo list", so `refs/client-repos.txt` and `refs/local-only-tests.txt` can never disagree about the same origin URL.

## Context

Found by the pre-push `/code-check` on 2026-10-08 (range 5a4b270..375c76d). Commit 375c76d added `origin_slug_bash` / `is_local_only_tests_repo` to `skills/commit/commit-pathspec.sh` to read the new `refs/local-only-tests.txt`. They mirror `hooks/_client_repo.py`'s slug algorithm (split on `/` or `:`, last two parts, strip `.git`, lowercase) because `_client_repo.py` was off limits to that builder and its CLI takes no list-path argument. The script's comment at the reimplementation states that tradeoff.

Two copies of a URL-parsing rule drift: an origin form one handles and the other does not (an `ssh://` URL with a port, a trailing slash) would make a repo count as a client repo but not as local-only-tests, or the reverse.

## Approach

Give `hooks/_client_repo.py` a `--list <path>` option (default `refs/client-repos.txt`), so `python hooks/_client_repo.py is-client <repo> --list refs/local-only-tests.txt` answers the second list. Replace the bash copy in `commit-pathspec.sh` with that call, keeping the script's existing fail-closed handling when python is missing. Add a `_client_repo.py` test for `--list`.

## Acceptance

- `commit-pathspec.sh` contains no origin-slug parsing of its own.
- `bash skills/commit/test_commit_pathspec.sh` passes, including the local-only-tests cases r53-r58.
- `python ci/run_all.py` passes.
