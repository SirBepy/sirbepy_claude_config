<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /preview skill: reduce the 4-step manual push dance to one command

**Type:** skill-improvement
**Origin:** ai

## Goal

`/preview`'s SKILL.md is read once, then every subsequent push in the same session is hand-executed: `Write` the HTML file, a `node -e` one-liner to build the JSON body, a `curl.exe` POST, then `rm` the scratch file. Cut that to one reusable command/script so a session iterating on a mockup doesn't reassemble the same 4-step dance by hand each time.

## Context

Observed 2026-08-19 in `claude_usage_in_taskbar`: pushed 7 mockup revisions in one session (AUQ padding, composer background, thinking-bar seam x3, connected-container, bugfix), each requiring the full Write+node+curl+rm sequence by hand. No functional problem - the iterate-in-place `slug` mechanic worked correctly every time - but it's pure repeated boilerplate a script could absorb.

## Approach

Add a small helper script alongside `SKILL.md` (e.g. `push-preview.ps1`/`push-preview.sh`) that takes a file path, title, and optional slug, and does the JSON-build + curl POST + (optionally) leaves cleanup to the caller. Update `SKILL.md`'s primary/fallback recipe to call the script instead of hand-rolling `node -e`/`ConvertTo-Json` inline. Keep the existing manual recipe as a documented fallback for when the script itself isn't present (matches the "Primary" / "No-Node fallback" structure already in the skill).
