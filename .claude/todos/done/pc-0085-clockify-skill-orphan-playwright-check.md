<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=2056735b -->
# Add orphan-Playwright-process check to clockify-reconciliator's HubStaff steps

**Type:** skill-improvement

## Goal

`~/.claude/skills/clockify-reconciliator/SKILL.md` steps 2 (screenshot preflight) and 12 (weekly screenshot) launch a `chromium.launchPersistentContext` against a fixed profile dir (`C:/tmp/playwright-profiles/hubstaff`). The skill should defend against a prior run's browser still holding that profile dir, instead of relying on the executing session to improvise a diagnosis each time.

## Context

2026-07-20 session: a first preflight script hit the HubStaff login wall and was left open (backgrounded Bash task) waiting on manual login. Every subsequent `launchPersistentContext` attempt against the same profile dir failed with `browserType.launchPersistentContext: Target page, context or browser has been closed`, which looked like a launch failure but was actually Chrome refusing a second instance on the same `--user-data-dir`. Diagnosed via `Get-CimInstance Win32_Process -Filter "Name='chrome.exe'"` filtered on the profile path, found ~11 chrome.exe entries (one logical multi-process browser: main + gpu + utility + renderers + crashpad), killed the holding Node process (which released the tree), deleted the stale profile dir, and retried clean. Full diagnostic writeup: [[reference_playwright_orphan_profile_lock]].

Process hygiene is already a global CLAUDE.md rule ("Never leave orphan child processes... check via Get-CimInstance... kill orphans before claiming done") - this todo makes the clockify-reconciliator skill itself enforce it proactively for its own known launch point, rather than relying on the executing session to reinvent the diagnosis.

## Approach

Add a step (or a bullet under step 2's preflight) that runs BEFORE any `launchPersistentContext` call:

- Check for existing chrome.exe processes whose command line contains the profile dir path (`Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match '<profile-dir-regex>' }`).
- If any found: this is a stale/orphaned instance from a prior run (the skill never keeps a browser open across turns intentionally) - kill them (`Stop-Process -Force`), then it's safe to delete the profile dir if desired (or just proceed, letting Chrome recreate its lock files).
- Only then call `launchPersistentContext`.
- Every code path that opens the browser (steps 2 and 12) must call `context.close()` before returning/erroring, including the "leave open for manual login" branch - now less critical since auto-login (see [[reference_hubstaff_auto_login]]) makes the manual-login branch rare, but still worth tightening so a failed auto-login attempt doesn't leak a browser tree either.

Alternative considered: always use a fresh throwaway profile dir per run (no persistence). Rejected - the whole point of the persistent profile is to keep the login session across runs (avoids re-login every week), so a fixed path is intentional; the fix is defending that fixed path, not abandoning it.

## Acceptance

- Running the HubStaff preflight/screenshot steps twice in a row (second run started while first is still mid-flight, or right after an unclean exit) does not produce the "Target closed" error.
- No leftover chrome.exe processes referencing the hubstaff profile dir after the skill completes (verify via the same `Get-CimInstance` filter used above).

## Notes

This is specific to the `clockify-reconciliator` skill's own launch point; the general orphan-diagnosis knowledge lives in the memory file above for other Playwright-using skills (`/screenshot`, `/flutter-e2e`, etc.) to reference if they hit the same symptom.
- completed, commit 22b597a
