<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=4da2395b -->
<!-- duplicate-checked -->
<!-- Searched this backlog and done/ for "CRLF", "line ending", "patch", "sed", "heredoc".
     478 is about skill-eval mutate/restore, 505 is about the shell-write ban. Neither covers a
     reusable exact-string patcher that preserves a file's existing line endings. -->
# CRLF-safe file patching gets hand-rolled from scratch every session

**Type:** skill-improvement
**Origin:** ai

## Goal

Provide one small, sanctioned helper for "replace this exact string in this file, preserving its
existing line endings", so sessions stop writing the same throwaway Python script.

## Context

In a single zng-app session on 2026-08-27 the identical ~12-line Python patcher was written **five
times** (`c:\tmp\edit_addr.py`, `edit_fields.py`, `edit_doc.py`, `lift1.py`, `lift2.py`). Every copy
did the same three things: read bytes, detect `\r\n`, normalise to `\n`, assert each `old` string
occurs exactly once, apply, re-encode with the original ending.

Two standing constraints force this shape and neither is going away:

- zng-app's Dart files are CRLF on disk, so a naive LF-normalising write produces a whole-file diff.
  The project memory `reference_dart_files_are_crlf_on_disk` already records this.
- `hooks/shell-content-write-guard.py` blocks `>` redirects, so the script itself has to be created
  with the `Write` tool - which is exactly the friction that makes people re-type it rather than
  keep one around.

Auto mode's "make file changes with sed, heredocs, or short scripts" instruction pushes toward this
path in the first place, and `sed -i` mangles CRLF, so the Python detour is correct - it is just
uncached.

The exactly-once assertion is the load-bearing part, not the line endings: it is what turns a silent
wrong-match edit into a loud failure.

## Approach

1. Add `~/.claude/skills/<some-home>/patch-file.py` taking `<path>` plus one or more
   `--replace <old-file> <new-file>` pairs (files, not argv, so multi-line and quote-heavy content
   survives), or a single JSON payload on stdin.
2. It must: preserve the file's dominant line ending, refuse and exit non-zero when an `old` string
   matches zero times or more than once, and report which pair failed.
3. Decide where it belongs - it is not really a skill, more a shared script. Check whether
   `~/.claude/hooks/_hooklib.py`'s neighbours already have a home for this kind of utility.
4. Reference it from the auto-mode guidance and from `code-style/` so it gets found instead of
   re-derived.

## Acceptance

- A session can patch a CRLF Dart file with one command and no scratch script.
- Passing an `old` string that appears twice exits non-zero and names it.
- The file's line endings are byte-identical to before, verified on a CRLF and an LF file.

## Notes

- Done via mega-todos batch 2, 2026-09-01 (bca2bf9): patch-file.py plus its 7-case self-test now live in tools/, not scripts/. The builder finished the code but could not commit: scripts/ is git-ignored by the repo allowlist gitignore, so it is the convention for untracked machine-local tooling. The orchestrator relocated it to tools/, the tracked home with the skill_eval.py precedent, where ci/run_tool_tests.py auto-discovers the test (now 2/2 tool suites).
