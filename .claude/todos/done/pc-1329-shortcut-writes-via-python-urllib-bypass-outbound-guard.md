<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: recurrence after done pc-1095 (raw API bypass) and pc-0382 (shortcut mutation guard); pc-1302/1304/1305 are verifier-flow issues, not this bypass -->
# Shortcut writes through a python urllib one-liner skip the outbound guards

**Type:** skill-improvement
**Origin:** ai
**Summary:** A zng-app session posted, edited and created Shortcut items through `python -c` + `urllib.request` with the kickoff.py token, and no outbound or mutation guard fired, even after pc-1095 closed the raw-API bypass.

## Context

2026-11-06, zng-app session c8ea4996 (sc-56606 triage). Joe approved each exact text by card, then Claude ran Bash `python -I -c "... import kickoff; t=kickoff.env()['SHORTCUT_API_TOKEN'] ... urllib.request.Request(url, data=..., method='POST'|'PUT')"` to:

- edit comment 56609 on sc-56606,
- post comment 56642 on sc-56606, then edit it,
- create story sc-56643.

Global CLAUDE.md says tickets Claude posts are hook-enforced (ground-check guards + outbound-verify). None fired. The token came from `kickoff.env()`, not a literal env var, and the URL and verb sat inside a Python string, which is the likely miss.

## Approach

Read pc-1095 and pc-0382 (done) first to see what the guard matches today. Then either widen the matcher to Bash commands that reference `kickoff.env` / `SHORTCUT_API_TOKEN` / `api.app.shortcut.com` together with a write verb (`method='POST'`, `'PUT'`, `'DELETE'`, `-X POST`), or give kickoff.py first-class `comment` / `edit-comment` / `create-story` subcommands the guard knows, and refuse raw-token writes.

## Acceptance

- A Bash `python -c` that PUTs to `api.app.shortcut.com` with the kickoff token is blocked or routed through outbound-verify.
- GET-only reads stay unblocked (pc-1302 has the read-only false-positive history).

## Notes

- Fixed: hooks/_python_http_write.py reads the verb of an inline python/node HTTP call (method='POST', requests.post, urllib data=); shortcut-create-guard.py and outbound-verify-guard.py both use it, including URLs built from a base. GETs and id-only state PUTs stay open. Tests added to test_shortcut_create_guard.py and test_outbound_verify_guard.py, red-checked against HEAD. Script-file bodies remain the stated limit.
