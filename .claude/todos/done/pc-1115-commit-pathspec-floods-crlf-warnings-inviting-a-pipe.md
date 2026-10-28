<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=a2f5ee57 -->
<!-- duplicate-checked: no existing todo mentions CRLF or "LF will be replaced" -->
# 1115 - commit-pathspec.sh floods git's LF/CRLF warnings, which pushes callers into piping it

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-06

## Goal

Make `skills/commit/commit-pathspec.sh` output readable without a filter, so callers stop breaking
`/commit`'s "never pipe this script's output" rule.

## Context

On 2026-10-06, in zng-biller (Windows, `core.autocrlf` repo), every git call inside the script
printed `warning: in the working copy of '<file>', LF will be replaced by CRLF the next time Git
touches it` once per pathspec file, and several of the script's internal steps each repeated
the whole set. Even the 7-file `prefilter-gate.sh` call alone printed 20 of these lines. To read
the actual verdict lines, the session ran
`commit-pathspec.sh ... 2>&1 | grep -v "LF will be replaced"; echo "exit=${PIPESTATUS[0]}"`.
That pipe is exactly what `skills/commit/SKILL.md` step 8 forbids ("Never pipe this script's
output", todo 1080). It was saved only by reading `PIPESTATUS`. The rule is easy to break here
because the script's own output pushes the caller toward a filter.

## Approach

In `skills/commit/commit-pathspec.sh` (and `prefilter-gate.sh`, which shows the same flood), run
the internal git calls with `-c core.safecrlf=false`, or filter that single warning pattern
inside the script itself, keeping its exit codes unchanged. Prefer the narrowest suppression that
only drops the `LF will be replaced by CRLF` / `CRLF will be replaced by LF` lines. Never
suppress other warnings.

## Acceptance

- In a repo with LF files and `core.autocrlf=true`, a `commit-pathspec.sh` run prints no
  LF/CRLF warning lines, and every `[check]` verdict line still appears.
- Exit codes are unchanged. Add a case to the script's existing test harness if one exists
  (`hooks/test_*.py` or `skills/commit/` tests). `python ci/run_all.py` passes.

## Notes

- 2026-10-07: recurred in claude_usage_in_taskbar. A session piped commit-pathspec.sh through `grep` to cut the CRLF flood on a 1-file commit (it committed fine, 7d44da7d). Same trigger as above, second occurrence.
- Completed 2026-10-08 (loop-todos cycle 1): commit-pathspec.sh and prefilter-gate.sh export GIT_CONFIG_* core.safecrlf=false so child git calls stop printing the LF/CRLF warning; exit codes unchanged; tests in test_prefilters.sh and r35.
