<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=5, reconfirm-count=1, content-hash=60ea96ee -->
# Check for Google's WebDriver-login block before launching an automated browser for a Google sign-in

**Type:** skill-improvement
**Origin:** ai

## Goal

Avoid wasting a full browser-launch cycle when a task needs the dev to log into a real Google
account (OAuth client setup, "sign in with Google" flows, etc.) through a Claude-launched
automated browser.

## Context

2026-08-27, odysseus session: Claude launched an isolated Playwright/Chromium window (fresh
profile, `--remote-debugging-port`) for Joe to log into his real Google account as part of
setting up Google OAuth credentials. Google blocked the login outright ("this browser isn't
secure"), a known, deliberate Google anti-automation measure that flags ANY WebDriver-controlled
browser attempting to sign in to ANY Google account, regardless of which account or how fresh the
profile is. The whole launch (script + background process + waiting for Joe) was wasted, and the
actual fix was simpler than the automated approach: have the dev log in through his own regular,
non-automation-flagged browser instead, with Claude only handling the mechanical parts around it
(the target URL, the resulting credentials, file/config writes).

There isn't a dedicated "browser automation" skill in this global config yet (the closest is the
project-level `/screenshot` skill and the ad-hoc Playwright usage pattern referenced in
`~/.claude/skills/_shared/playwright-resolve.cjs`), so this gap doesn't live in one obvious file
today.

## Approach

Wherever browser-automation guidance for interactive human logins lives (or gets created):
before spinning up a Claude-launched/WebDriver-controlled browser specifically to have the dev
log into an account, check first whether the target service is known to block automated
sign-in (Google is confirmed; likely true of other major identity providers such as Microsoft
and Apple, unconfirmed). If so, skip straight to "the dev logs in via their own regular browser,
Claude handles everything else" instead of launching an automated browser first and discovering
the block live.

Natural homes to consider: a note in `~/.claude/skills/_shared/playwright-resolve.cjs`'s
surrounding docs, or wherever a future browser-automation skill consolidates this kind of
guidance. Don't invent a whole new skill just for this: a one-paragraph caveat wherever
Playwright-driven login flows already get discussed is enough.

## Acceptance

- A future session facing "log into Google via an automated browser" checks this first and skips
  straight to the dev-does-it-in-their-own-browser approach, rather than launching a
  WebDriver-controlled browser and hitting the block live.

## Notes

Low-frequency issue (only comes up when a task needs an actual human login inside an
automated/testing browser), but the failure mode (a fully wasted browser-launch round trip) is
clean and easy to prevent once known.
