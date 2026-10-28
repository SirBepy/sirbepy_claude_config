# Configure Playwright MCP to use existing Chrome profile

## Goal
Set up the Playwright MCP server to launch with Joe's actual Chrome user profile so HubStaff (and other sites) stays logged in between sessions.

## Context
Every time /clockify-reconciliator runs the HubStaff screenshot step, Playwright opens a fresh browser with no cookies, landing on the login page. Joe has to log in manually each time. The Playwright MCP supports `--user-data-dir` to reuse an existing Chrome profile.

Chrome profile path on this machine: `C:\Users\tecno\AppData\Local\Google\Chrome\User Data`

## Approach
In Claude Code settings (`.claude/settings.json` or user settings), update the Playwright MCP server config to pass `--user-data-dir "C:\\Users\\tecno\\AppData\\Local\\Google\\Chrome\\User Data"` (and `--channel chrome` to use the installed Chrome rather than Playwright's bundled Chromium). Use the `update-config` skill to make this change safely.

Note: Chrome must be fully closed before Playwright launches, or Chrome will block the profile lock. A dedicated profile copy or `--profile-directory` flag avoids this conflict.

## Acceptance
- /clockify-reconciliator runs HubStaff screenshot step without a login redirect
- No manual login required

## Notes

- Relocated from `09` in `zng-admin` via /cleanup-todos 2026-08-13: this targets global MCP server config and the `/clockify-reconciliator` skill, no zng-admin file is involved.
- Re-verified 2026-08-13: the live config in `C:\Users\tecno\.claude.json` has since moved to a **different** approach, `--cdp-endpoint http://127.0.0.1:9222`, rather than `--user-data-dir`. Whether that already solves the login-persistence problem was not verified. Check that before implementing the `--user-data-dir` approach as written; it may be moot.
- Archived 2026-08-13 as ALREADY SOLVED, no code change needed, but not by the mechanism the todo assumed. The todo wanted Playwright MCP's --user-data-dir pointed at Joe's real Chrome profile. That is moot: hubstaff.md line 9-13 states outright that the HubStaff flow depends on local Playwright and NOT on a Playwright MCP server, so the MCP config (now --cdp-endpoint http://127.0.0.1:9222, and currently unreachable, TcpTestSucceeded False) is not in that path at all. The real fix already shipped in commit 8d83c754: hs_preflight.cjs uses launchPersistentContext against a dedicated on-disk profile at skills/clockify-reconciliator/playwright-profiles/hubstaff, which retains cookies across runs by itself. That directory does not exist yet only because the script has never been run, not because persistence is broken, and HUBSTAFF_EMAIL/PASSWORD in ~/.claude/.env cover the first-run auto-login. No credentials touched, no browser launched against Joe's live profile.
