<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no backlog file mentions quotePath or non-ASCII file names in the prefilters -->
# em-dash and secret-scan prefilters skip a file whose name is non-ASCII

**Type:** bug
**Origin:** ai
**Priority:** High

## Goal

`skills/commit/em-dash.sh` and `skills/commit/secret-scan.sh` scan and name a changed file whose
path holds non-ASCII characters, exactly as they do an ASCII-named one.

## Context

Found 2026-10-23 by the Opus verify pass over the todo-1161 rewrite of `commit-pathspec.sh`
(loop-todos cycle 2). Pre-existing: the HEAD scripts before that rewrite behave the same.

With git's default `core.quotePath=true`, a non-ASCII path's diff header prints quoted
(`+++ "b/\303\244.txt"`). The awk in both scripts only matches `^\+\+\+ b/`, so it never switches
to the new file, and the previous file's name and skip state carry over. Reproduction from that
review: an untracked `a.pdf` holding plain text (exempt by extension) plus `ä.txt` holding an AWS
key and an em dash, run through the gate together: both the HEAD and the working-tree gates exit 0
having found nothing. Run on `ä.txt` alone, both are flagged, but under an empty file name (`:1`).

This is a fail-open in the secret scan, which is the one prefilter that must STOP a commit.

## Approach

Pass `-c core.quotePath=false` on every `git diff` call the prefilters make (in `_prefilter-lib.sh`
and the scripts), and also reset the current file and skip state on each `^diff --git` line so a
header the awk cannot parse never inherits the previous file's state. Check `comment-tense.sh` and
`todo-ref.sh` for the same header match.

## Acceptance

- A test in `skills/commit/test_prefilters.sh`: an exempt-by-extension file plus a non-ASCII-named
  text file holding a fake AWS key and an em dash, gated together, flags both findings under the
  non-ASCII file's real name. It fails on the current scripts.
- `bash skills/commit/test_prefilters.sh` and `bash skills/commit/test_commit_pathspec.sh` pass.

## Notes

- Done by /loop-todos cycle 2 on 2026-10-23: git_c and the range-mode diffs run with core.quotePath=false, and every scanner awk resets its file and skip state on each diff --git line, so a header it cannot read fails closed. New test_prefilters.sh cases (tracked and untracked cafe-accent file beside an exempt PDF) failed before, pass after; test_commit_pathspec.sh ALL PASS.
