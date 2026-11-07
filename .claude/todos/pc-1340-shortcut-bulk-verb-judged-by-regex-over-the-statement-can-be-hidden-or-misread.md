<!-- Claim before executing: .claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1339 is the push-gate boundary and the commit-memory residual, a different surface -->
# Shortcut guards: the verb of a /stories/bulk URL is read by regex over its statement and can still be hidden or misread

**Type:** task
**Origin:** ai
**Summary:** Residuals of the `/stories/bulk` handling added for review-unpushed item 10 (lane F3, 2026-11-07), found by fresh reviews of the fix and not closed.

## Why

`POST /stories/bulk` counts as a story create, while a PUT or DELETE there is a bulk update or delete. `hooks/_python_http_write.py` `bulk_is_not_a_post` decides which by searching the URL's own shell statement (quote-aware `_statement_bounds`) for `-X`/`--request`/`-Method` followed by PUT, PATCH, DELETE or GET. A regex over statement text cannot see command structure, so each shape below still goes wrong. The worst direction is a false allow: a real bulk create passes `hooks/shortcut-create-guard.py` with no ground-check marker.

## Goal

Each payload below behaves as listed, with a regression test that is red before the fix. U is the `/api/v3/stories` URL.

## Context

False allows (all return "not a create" today):

- `curl -X POST U/bulk -d @b # was curl -X PUT`: a trailing comment is not stripped.
- `curl -X POST U/bulk -H "X-Note: -X PUT" -d @b` and `curl -X POST U/bulk -d '{"description":"run curl -X GET"}'`: a verb inside a quoted header or payload (a real story description can name `-X GET`).
- `curl -X PUT U/bulk -d @a --next -X POST U/bulk -d @b`: `--next` starts a second request inside one statement.
- `curl -X PUT U/bulk -X POST U/bulk -d @b`: a later `-X POST` on the same line.
- `curl -X PUT U/bulk -d "$(curl -X POST U/bulk -d @b)"`, the unquoted `$(...)`, the backtick form, and a `( ... )` subshell: the POST nests inside the PUT's statement.
- `curl -X PUT U/bulk -d @a&curl -X POST U/bulk -d @b`: a `&` with no whitespace around it is not a statement break (`_statement_bounds` needs whitespace on both sides so `2>&1` and URL query strings stay whole); a bare `\r` separator likewise.

False deny (low, fails toward gated): `curl -s -X PUT "U/bulk?a=1;b=2" -d @a`, where a `;` inside the URL's own quote reads as a nested command line.

Fix idea: judge each bulk URL by the verb flag nearest before it (the last `-X`/`--request` ahead of the URL, bounded by `--next`), ignore verb text inside quotes and after a `#` comment, and treat `$(`, a backtick and a subshell `(` inside the statement as untrusted like the nested-quote case already is. Alternatively drop the PUT/DELETE exemption: gate every `/stories/bulk` call and accept a deny on a bulk update (rare in practice).

## Approach

Add the payloads to `hooks/test_shortcut_create_guard.py` and `hooks/test_outbound_verify_guard.py`, prove red with `skills/close/red-check.ps1`, then fix in `hooks/_python_http_write.py`.

## Acceptance

- Every false-allow payload above is a create (`posts_to_stories` True; `shortcut_requires_prose` True for the outbound guard).
- A quoted-URL bulk PUT with a plain query string is still not a create.
