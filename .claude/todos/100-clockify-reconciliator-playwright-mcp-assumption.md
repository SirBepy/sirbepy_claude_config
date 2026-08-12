<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=07e8d142 -->
# clockify-reconciliator assumes a Playwright MCP that isn't in the session

**Type:** skill-improvement

## Goal

Make `/clockify-reconciliator` steps 2 and 12 executable as written, so the HubStaff
preflight and weekly screenshot stop depending on an MCP server that is not connected
in a normal zng-app session.

## Context

`C:\Users\tecno\.claude\skills\clockify-reconciliator\SKILL.md` step 2 (screenshot
preflight) and step 12 (weekly screenshot) are written against Playwright MCP tool names:
`browser_wait_for`, `browser_take_screenshot`, and a "playwright MCP can only write under
its allowed roots" caveat that drives a screenshot-then-Move-Item dance.

On the 2026-08-01 run those tools did not exist. The session's MCP servers were
`chrome-devtools`, `claude.ai Google Drive`, and `mobbin` (unauthenticated). There is no
Playwright MCP. As a result:

- Step 2's preflight was skipped entirely and the run went straight to data fetching.
  No harm that time (the persistent profile at `C:/tmp/hs-profile` still held a valid
  session), but the whole point of the preflight is to surface an auth failure BEFORE
  the reconciliation work, and it silently did not run.
- Step 12's screenshot had to be hand-written as a local Playwright `.cjs` script
  (`C:/tmp/hs_weekshot.cjs`) at the end of the run.

The working mechanism is already documented in the memory
`reference_hubstaff_ui_time_edit`: local Playwright at
`C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright`,
driven via `chromium.launchPersistentContext('C:/tmp/hs-profile', { headless: false })`.
Headless is blocked by Cloudflare on `account.hubstaff.com`; headed plus the persistent
profile passes and keeps the clearance cookie between runs.

Sibling scripts that already work and should be treated as the reference implementation:
`C:/tmp/hs_edit_entry.cjs`, `C:/tmp/hs_add_entry.cjs`, `C:/tmp/hs_probe_fri.cjs`,
`C:/tmp/hs_weekshot.cjs`. These live in scratch and will not survive a `C:/tmp` clean,
which is the second half of the problem.

## Approach

1. Rewrite SKILL.md steps 2 and 12 to call a local Playwright script instead of MCP tools.
   Drop the "allowed roots" workaround: a local script writes straight to
   `C:\Users\tecno\Desktop\` and the Move-Item step disappears.
2. Move the scripts out of scratch into the skill folder so they persist, e.g.
   `~/.claude/skills/clockify-reconciliator/scripts/hs_weekshot.cjs` and
   `hs_preflight.cjs`. Parameterize org id, user id and the profile path from the project
   config rather than hardcoding 410414 / 4023312 as the current scratch copies do.
3. Keep the existing auto-login fallback contract from step 2 (fill `HUBSTAFF_EMAIL` /
   `HUBSTAFF_PASSWORD`, fall back to a manual wait, mark the screenshot step skipped on
   failure) - only the driving mechanism changes, not the behavior.
4. Keep the <50 KB size validation on the saved screenshot; it correctly catches a login
   page rendered instead of the weekly grid.

Rejected: adding a Playwright MCP server to the session config. The local-script path is
already proven here and in `reference_local_playwright_fallback`, needs no server
lifecycle, and avoids the orphan-profile-lock failure mode documented in
`reference_playwright_orphan_profile_lock`.

## Acceptance

- A fresh `/clockify-reconciliator zirtue` run executes step 2 without the operator
  noticing any missing tool, and reports either "auth OK" or a concrete auth failure.
- Step 12 writes `hubstaff-weekly-<mon>_to_<sun>.png` to the Desktop directly, over
  50 KB, showing the weekly grid rather than a login page.
- Scripts referenced by SKILL.md live under the skill folder, not `C:/tmp`.
- Must NOT regress: headed mode and the persistent profile stay (headless re-triggers the
  Cloudflare challenge), and no orphan chrome/node process is left behind after a run.

## Notes

Related memories worth reading before starting: `reference_hubstaff_ui_time_edit`,
`reference_hubstaff_api`, `reference_hubstaff_auto_login`,
`reference_playwright_orphan_profile_lock`, `reference_local_playwright_fallback`.

`~/.claude-personal/skills/clockify-reconciliator/SKILL.md` and
`~/.claude/skills/clockify-reconciliator/SKILL.md` are hardlinked - editing one edits both.
