<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1249 (script hardening), 1250 (unsent drafts), 1256 (feed auth/pagination/git) cover other gaps; none adds a story reader -->
# 1262 - zng-kickoff: add a `story <id>...` subcommand that prints a ticket with its comments

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-28
**Summary:** /zng-kickoff can print a ticket with its comments in one call, so each run stops hand-rolling a Shortcut fetch.

## Why

The 2026-10-27 hub chat hand-wrote the same fetch snippet four times, and two earlier attempts were blocked by shell guard hooks.

## Goal

Give `/zng-kickoff` steps 3 and 5 a one-call way to read full tickets, so each run stops hand-rolling a Shortcut fetch.

## Context

The 2026-10-27 hub chat (zng-app session 9dee5a6f) read tickets four separate times (feed tickets, sc-53956, sc-56513, three pickup candidates) by hand-writing the same Python urllib snippet: load the token from `~/.claude/.env` with BOM stripping, `GET /api/v3/members` for a uuid-to-name map, `GET /stories/<id>`, then print state name, owners, links and comments. Two earlier attempts were blocked by hooks: `curl ... > file` tripped `shell-content-write-guard`, and `curl -o` tripped `outbound-verify-guard`, which reads it as a REST write.

## Approach

1. In `~/.claude/skills/zng-kickoff/scripts/kickoff.py`, add `story <id> [<id>...]`. It reuses the script's existing token loading, maps member uuids to names (`GET /members`), maps workflow state ids to names (ENG workflow table in `~/.claude/refs/shortcut-api.md`), and prints: title, state, owners, requester, epic, `story_links`, `blocked`, description (truncated) and every comment with its author and date.
2. GET only, through urllib, so neither hook fires.
3. In SKILL.md steps 3 and 5, change "read the ticket and comments" to call `kickoff.py story`.

## Acceptance

- `kickoff.py story 56503 56238` prints both tickets with named authors and states in one call.
- Neither shell guard hook fires.

## Notes

- Fixed in e4d4d4a (story subcommand; checked live against ticket 56503).
