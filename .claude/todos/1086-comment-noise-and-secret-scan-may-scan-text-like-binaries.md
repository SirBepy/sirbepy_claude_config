<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits (290, 293, 319, 356, 38) are about creating or wiring the prefilters; this is a shared binary-file check after 986 fixed only em-dash.sh -->
# comment-noise and secret-scan may scan text-like binaries the em-dash gate now skips

**Type:** task
**Origin:** ai

## Goal

All commit prefilters agree on which files are binary, so a text-heavy PDF never trips one of them
after em-dash.sh learned to skip it.

## Context

Todo 986 (done, 5d6f7b2) added `is_binary_path()` to `skills/commit/em-dash.sh`: an extension list,
then git's `--numstat` binary flag, then a NUL sniff, because a real wedding-invitation PDF had no NUL
in its first 8KB and git's own heuristic treated it as text. UNVERIFIED: `skills/commit/secret-scan.sh`
and `comment-noise.sh` (both sharing `_prefilter-lib.sh`) have the same gap; would check by running
both over the scratch PDF case from `skills/commit/test_prefilters.sh`. secret-scan is the one that
matters, since it blocks a commit and is never auto-fixed.

## Approach

1. Reproduce: run secret-scan.sh and comment-noise.sh over a text-like PDF fixture.
2. If either scans it, move `is_binary_path()` into `_prefilter-lib.sh` and call it from all three.
3. Add the fixture case for each script to `test_prefilters.sh`.

## Acceptance

- One shared binary check, used by every prefilter.
- test_prefilters.sh covers the PDF fixture for each script.
