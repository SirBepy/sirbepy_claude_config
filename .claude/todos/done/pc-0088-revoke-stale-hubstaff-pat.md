<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=2, reconfirm-count=2, content-hash=d4f33ce9 -->
# Revoke the stale "My token" HubStaff personal access token

**Type:** task

## Goal

Leave exactly one active HubStaff personal access token, the one actually referenced by `HUBSTAFF_REFRESH_TOKEN` in `~/.claude/.env`.

## Context

On 2026-07-26 the HubStaff refresh-token exchange started returning `403 error code: 1010`, which looked like a revoked token. On that (wrong) assumption a second PAT named `claude-clockify-reconciliator` was created through the developer portal with scopes `openid profile hubstaff:read tasks:read`.

The real cause was Cloudflare blocking python-urllib's default User-Agent, not a dead token - see [[hubstaff-api---working-endpoints-and-auth]]. The original token, named **"My token"** (same scopes, "Last used 7/20/2026"), was therefore probably fine the whole time and is now redundant.

`.env` currently holds the NEW token (`claude-clockify-reconciliator`). Nothing references "My token" anymore.

Deferred because it is pure housekeeping with zero functional impact, and revoking the wrong one would break the reconciliator.

## Approach

1. Open `https://developer.hubstaff.com/account/personal-access-tokens/` in a headed Playwright persistent context (headless hits a Cloudflare challenge). Recipe in [[reference-hubstaff-ui-time-edit]].
2. The portal needs its own OAuth hop: click **Sign in**, then in the popup click the button with text **Authorize** (Cancel is first in the DOM - a generic submit-button click picks Cancel and returns `access_denied`).
3. Confirm which token `.env` holds before touching anything: decode the JWT payload of `HUBSTAFF_REFRESH_TOKEN` and compare against the portal list.
4. Click **Revoke** on the row named **"My token"** only.
5. Re-run a token exchange to confirm the remaining token still works.

Rejected alternative: revoking both and minting a fresh one. Unnecessary churn, and each mint burns a refresh-rate-limit window.

## Acceptance

- Portal lists exactly one token: `claude-clockify-reconciliator`.
- `python c:/tmp/hubstaff_week.py 2026-07-20`-style exchange still returns an access token (with a browser User-Agent header set).
- `/clockify-reconciliator zirtue` completes its HubStaff comparison step without auth errors.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] Physical action, yours only: revoke the stale HubStaff personal access token in the HubStaff portal. Claude cannot do this, it needs a browser login. Note the `HUBSTAFF_REFRESH_TOKEN` entry in `~/.claude/.env` is a DIFFERENT credential and is still in use, do not delete it. Scored 2/10 on worth and kept only because it is credential hygiene.

## Notes

Do NOT retry the exchange repeatedly while verifying - HubStaff returns `400 rate_limit` after a few refreshes in quick succession and locks you out for several minutes.
- Archived on Joe's call 2026-08-12 during /auto-do-todos: a redundant read-scope HubStaff PAT on his own account, zero functional impact, rated 2/10 worth. Not worth tracking as a standing todo.
