<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=4, content-hash=6ded35f0 -->
# Move the Clockify Playwright browser profile out of skills/ into per-machine storage

**Type:** task
**Origin:** dev

## Goal

Get 419 files / 54 MB of Chrome profile runtime state out of `skills/`, which is a tracked config
repo, and into a per-machine location where runtime state belongs. Joe asked for this on
2026-08-18 during the todo 58 audit, right after approving the stopgap.

## Context

`skills/clockify-reconciliator/playwright-profiles/hubstaff/` holds a persistent Chrome profile so
the HubStaff flow stays logged in between runs. Measured 2026-08-18: **419 files, ~54 MB**.

**The location was deliberate, not an accident.** Do not "fix" it as if it were spill.
`done/302-playwright-chrome-profile.md` records that commit `8d83c754` chose it on purpose:
`hs_preflight.cjs` uses `launchPersistentContext` against a dedicated on-disk profile there, which
retains cookies by itself, replacing an earlier `--user-data-dir` / Playwright-MCP approach that
was moot. So the persistence mechanism is correct; only its address is wrong.

The problem it caused: `.gitignore` line 9 is `!skills/**`, which re-included all 419 files, so
they showed up as untracked in every `git status` in this repo. **Todo 58 mis-described this as
"untracked runtime spill" of unknown origin; it is not, it is one deliberate directory.**

**A stopgap already shipped 2026-08-18** (this session): `.gitignore` now carries
`skills/*/playwright-profiles/`, verified to take the untracked count under `skills/` from 419 to
0. That means this todo is a cleanliness improvement, NOT a bug fix, and nothing is broken while
it waits.

## Approach

1. Pick the destination. `%LOCALAPPDATA%\claude-clockify\playwright-profiles\hubstaff` matches how
   the rest of Windows stores per-machine browser state. Note `refs/` and CLAUDE.md have no
   existing convention for this, so this is a genuinely new choice - confirm it with Joe.
2. Update the two call sites, both in `skills/clockify-reconciliator/hubstaff.md`:
   - line 22 and line 132, each passing `--profile skills/clockify-reconciliator/playwright-profiles/hubstaff`
   - line 18's orphan-kill matcher greps the command line for `playwright-profiles.hubstaff`; it
     keeps working if the new path still contains that substring, and breaks if it does not.
3. Check the scripts under `skills/clockify-reconciliator/scripts/` for a hardcoded default profile
   path before assuming the two markdown call sites are the only ones.
4. Move the existing profile directory rather than deleting it, so the HubStaff login survives.
   Deleting it costs a re-login, not data.
5. Once nothing writes under `skills/` any more, decide whether the `skills/*/playwright-profiles/`
   .gitignore line stays as a safety net (recommended: keep it) or goes.

## Acceptance

- No Playwright profile data is written anywhere under `C:\Users\tecno\.claude\skills\`.
- A HubStaff run still starts logged in, with no manual login, from the new location.
- The orphan-kill matcher at `hubstaff.md:18` still matches the relocated Chrome process.
- `git status` in this repo stays clean of profile files.

## Notes

- Another session had `skills/clockify-reconciliator/scripts/hs_weekshot.cjs` modified and
  `hs_addtime.cjs` untracked while this was filed. Re-read both before editing; they may have
  landed since.
- Related history: `done/85-clockify-skill-orphan-playwright-check.md` shows the profile once lived
  at `C:/tmp/playwright-profiles/hubstaff`, so this directory has already moved once. Whatever
  destination gets picked, put it somewhere a future audit will not read as spill again.
- Fixed in 6c11c56: the Hubstaff Playwright profile now lives at %LOCALAPPDATA%\claude-clockify\playwright-profiles\hubstaff, with the file count verified at the destination before the source was removed. Three call sites updated, not the two the todo named.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [ARCH] Where should the per-machine Playwright profile for Hubstaff live, now that it sits inside the skills tree? Options: `%LOCALAPPDATA%\claude-clockify\playwright-profiles\hubstaff` / `C:\tmp\playwright-profiles\hubstaff` (its pre-302 home) / leave it under `skills/`. Recommended: `%LOCALAPPDATA%`, because it matches the Windows per-machine-state convention and keeps machine state out of a git-tracked skills dir.
