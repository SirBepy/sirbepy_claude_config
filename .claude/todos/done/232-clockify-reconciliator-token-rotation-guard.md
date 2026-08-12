<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=a046ace9 -->
# clockify-reconciliator: guard HUBSTAFF_REFRESH_TOKEN rotation writes with a .env.bak fallback

**Type:** skill-improvement

## Goal

`skills/clockify-reconciliator/hubstaff.md` Step 11 rotates `HUBSTAFF_REFRESH_TOKEN` on
every exchange and writes the new value straight into `~/.claude/.env` with no backup. A
failed/partial write (disk full, killed mid-write, concurrent edit) would corrupt or lose
the token with no recovery path, since HubStaff's refresh tokens are single-use - the OLD
token is already invalidated by the exchange that produced the new one. Add a
write-ahead backup: write the rotated value to `.env.bak` first, then to `.env`, abort
(and tell the dev) on any write failure rather than leaving `.env` partially written.

## Context

`skills/clockify-reconciliator/hubstaff.md`, Step 11 (as of 2026-08-01), lines 21-28:

```
## Step 11 â€” HubStaff comparison (skip if `hubstaff_org_id` not set or `HUBSTAFF_REFRESH_TOKEN` missing)

First exchange the refresh token for an access token - no client credentials needed:
POST https://account.hubstaff.com/access_tokens
Body (form-encoded): grant_type=refresh_token&refresh_token=<HUBSTAFF_REFRESH_TOKEN>

The response includes a new `refresh_token` - write it back to `HUBSTAFF_REFRESH_TOKEN`
in `~/.claude/.env` immediately (token rotates on each exchange).
```

No backup step exists today. Because HubStaff rotates the refresh token on every
exchange (the doc says so explicitly), the previous token in `.env` becomes worthless the
instant the exchange call succeeds - if the subsequent write to `.env` then fails or is
interrupted, the dev is locked out of HubStaff entirely until they manually re-auth
(there is no `HUBSTAFF_EMAIL`/`HUBSTAFF_PASSWORD` fallback for the API token flow the
way there is for the Step 2 Playwright screenshot flow at hubstaff.md lines 12-18).

## Approach

1. Read `skills/clockify-reconciliator/hubstaff.md` Step 11 in full before editing.
2. After the token exchange succeeds and the new `refresh_token` value is in hand, before
   overwriting `~/.claude/.env`:
   a. Write the CURRENT (about-to-be-replaced) full `.env` file content to
      `~/.claude/.env.bak` first (whole-file copy, not just the one line - simplest safe
      approach, avoids partial-line-replace bugs).
   b. Only after that write succeeds, apply the actual line replacement
      (`HUBSTAFF_REFRESH_TOKEN=<new value>`) to `~/.claude/.env`.
   c. If step (a) or (b) fails for any reason (permission error, disk full, etc.), STOP
      and tell the dev exactly what happened and that the new token (from the exchange
      response, still in memory/output) needs to be saved manually - do not silently
      retry or swallow the error, since retrying the exchange with the now-stale old
      token will fail (single-use rotation).
3. Add `.env.bak` to the ignore rules covering `~/.claude/.env` (check whether `.env` is
   already gitignored at the `~/.claude` repo root - it should be, since it holds live
   secrets - and add `.env.bak` alongside it if not already covered by the same pattern,
   e.g. a `.env*` glob).

## Acceptance

- Step 11's write sequence is backup-then-write, not write-only.
- A simulated write failure (e.g. read-only `.env` during a manual test) surfaces a clear
  error to the dev with the new token value included in the message, rather than
  silently losing it.
- `.env.bak` does not end up tracked by git (confirm via `git check-ignore
  ~/.claude/.env.bak` after the ignore-rule change, or `git status` showing it as
  ignored/untracked).

## Notes

- completed, commit 22b597a
