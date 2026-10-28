<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 833 allowed one Firebase key literal; this is a different value (the OAuth keyword Bearer) and its own allow row -->
# secret-scan flags the OAuth keyword `token_type: 'Bearer'`

**Type:** task
**Origin:** ai
**Summary:** The commit secret scan stops reporting the OAuth protocol word Bearer as a secret.

## Why

On 2026-10-28 in dashboard-a a builder stopped on token_type: 'Bearer' in a test file, and the controller had to rename a constant as a workaround.

## Goal

The commit secret scan stops reporting the OAuth protocol word `Bearer` as a secret.

## Context

- `hooks/secret-patterns.txt:10` (`generic_assignment`) matches any key containing `token` or `bearer` followed by
  a quoted value of 6+ characters, so `token_type: 'Bearer'` (RFC 6750, every OAuth token response and every fake
  issuer in a test) is a hit, and so is `const BEARER = 'Bearer'`.
- Seen 2026-10-28 in dashboard-a slice 1 Task 4b (`apps/server/src/test/fakeOidc.ts`): the builder stopped on it as
  the rules require; the controller renamed the constant to `AUTH_SCHEME` to get past it, which is a workaround, not
  a fix.

## Approach

Add an `allow` row for the exact value `bearer` (case-folded, the scan lowercases lines) applied to
`generic_assignment`, with a `test_prefilters.sh` case for `token_type: 'Bearer'` (no hit) and
`token: 'Bearer abcdef123456'` (still a hit).

## Acceptance

`bash skills/commit/test_prefilters.sh` passes with both cases.
