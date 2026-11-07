<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 7 remainder; pc-1266 covers only close --light's missing steps 3-4 -->
# Fix the remaining broken skill steps: loop-todos claims, /close --light, clockify, web-setup templates and others

**Type:** task
**Origin:** dev
**Summary:** Skills that currently tell an agent to do something that fails or contradicts another skill get corrected.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. The safe doc fixes landed that night (36032f0, 4f0f768: /screenshot, /create-pr, /test, /e2e, `@{u}` quoting, character-creator, obsidian, add-git-account). These are the rest, which change shared scripts, deployed-site templates or need judgment.

## Goal

No skill gives an agent a step that fails, and `/close --light` agrees with `/close`.

## Context

- `skills/loop-todos/SKILL.md:96-102` + `skills/close/claim-todo.ps1:149-151`: a claim counts as stale only when it is over 4 h old AND its pid is dead; the stored `session:` is never compared, so a session's own live claim returns conflict. Nothing in loop-todos or respawn releases leftover claims, so a Phase 3.5 re-entry or the post-`/respawn` successor drops every leftover id. Runtime outcome UNVERIFIED; done pc-1147 fixed only auto-do's duplicate claim.
- `skills/close/light.md:13` passes `unpushed` scope where `skills/close/SKILL.md:157-177` requires `shas:`; light mode has no peer sweep or cross-repo routing. It backs `/respawn` unattended, `/auto-respawn` and `/loop-todos`. pc-1266 covers only the missing screenshot count and digest.
- `skills/clockify-reconciliator/SKILL.md`: step 12's header says to run the screenshot when auth failed (the opposite of `hubstaff.md`); step 10a contradicts itself on `weekly_target_hours`; step 4a globs memory files that moved to `memory/archive/` and `memory/rest/` (also `SKILL.md:101`, `hubstaff.md:27,130`, `skills/flutter-bump/SKILL.md:59`). 7.4k words; ~1.8k rare-path.
- Web-setup family: `skills/bepy-project-setup-web` runs `/readme` and `/meta-tags` (need the git remote and `.portfolio-data`) before `/github-pages-init` (step 5) and `/portfolio-data` (last); `/readme` fully rewrites and so overwrites a `/pretty-readme` result; `/pwa` service worker is cache-first with a fixed `v1` cache name, so edited CSS/JS never reaches returning users, and "run /pwa again" hits its "already complete" skip; `skills/update-workflow/templates/react.yml` uploads `build/` but `init-claude-md` defines react as "Vite or CRA"; `/deploy` needs `workflow_dispatch`, which none of the three templates has.
- `skills/flutter-bump`: pushes the whole unpushed stack with no `@{u}..HEAD` check. Hit live on the 3.47.9 bump, 2026-11-03: zng-app held `a4e8048b` and `a7012c9d`, and zng-biller held 4 commits waiting on a reword (its pc-0116). Followed literally, the skill would have shipped them; Joe chose commit without push for both repos. Fix: list `@{u}..HEAD` before the bump, and ask when it holds anything but the bump.
- `skills/code-check` Step 0 (description word count) duplicates `ci/check_skill_frontmatter.py` without its slash-only exemption (five of its findings were all dropped); it spawns a subagent before the cheap file-extension filter, so empty-scope pushes pay for a no-op.
- `skills/supply-chain-audit` tells its read-only fork to rename directories it has no tool for; `skills/isolated-build/SKILL.md:34-36` says `-NoDynamicPort` pins a port, which supervised-run does not support; `skills/isolated-build/land.ps1:19` comment keeps stale "helper skills never commit" wording.
- `skills/one-off`: step 2 says "do it instead of filing" but `/code-check` files by default; runs `/code-check` and `/test` twice.

## Approach

Claim, then fix in small commits per skill. The loop-todos fix: let `claim-todo.ps1` treat a claim whose `session:` matches the caller as owned (with a test in a scratch backlog), and have loop-todos release unfinished claims at cycle end. The web-setup template changes alter deployed sites: show the dev the diff first.

## Acceptance

- A double `claim-todo.ps1` call from one session in a scratch backlog succeeds the second time.
- `/close --light` uses the same review scope rule as `/close`.
- `python ci/run_all.py` passes.

## Notes

- Landed dc52ca2, a50cde6, 6d479bd, 6bf98cc, 0e109d2, c540a04; deferred template items in pc-1336.

## Decided

- 2026-11-07: loop-todos claim item covered by pc-1323 (c55090c); clockify glob item covered by pc-1269 (7b1db39).
- 2026-11-07: `/close --light` now uses the main Phase 2 scope rule plus the Phase 3 peer sweep and cross-repo routing (dc52ca2).
- 2026-11-07: deployed-site template changes (`/pwa` cache name, `react.yml` build dir, `workflow_dispatch`) deferred and filed as pc-1336; the docs now state the gaps (6d479bd).
- 2026-11-07: `isolated-build/land.ps1` stale "helper skills never commit" wording was already swept by 36b57b4; nothing left to change.