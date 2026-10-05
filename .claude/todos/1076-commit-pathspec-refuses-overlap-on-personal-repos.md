<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=8eb1f9eb -->
<!-- duplicate-checked: 1004 covers the missing --expect-branch/--expect-sha flags in the documented line; no todo covers the personal-repo overlap mismatch -->
# commit-pathspec.sh refuses overlap hits on personal repos that SKILL.md says never to ask about

**Type:** skill-improvement
**Origin:** ai

## Goal
`commit-pathspec.sh` follows commit SKILL.md step 8's overlap policy, so a personal repo (origin under `SirBepy`, or no remote) proceeds on an overlap hit without needing `--force overlap`.

## Context
2026-10-03, mc_plugins_tag (origin `https://github.com/SirBepy/mc-plugins.git`): two pathspec commits hit `[overlap-check] REFUSED (judgement call ...)` because of old unpushed commits (cead211) on the same lines. SKILL.md step 8 "On exit 1" branch 2 says that on a personal repo Claude must never ask and must always take the genuinely-separate branch, so the refusal can only ever be overridden. Every personal-repo commit with an overlap costs an extra round trip. Also, the refusal prints the label `overlap-check`, but `--force overlap-check` errors with `unknown --force check name overlap-check (valid: head-guard, overlap, foreign-hunk, coverage)`, which cost a second retry.

## Approach
In `C:\Users\tecno\.claude\skills\commit\commit-pathspec.sh`, before refusing on an overlap exit 1, run the same personal-repo check `hooks/gh-account-switch.sh` uses (origin owner or no remote). If the repo is personal, print the hit lines as info plus `personal repo: proceeding (SKILL.md step 8 branch 2)`, then continue. Either accept `overlap-check` as an alias for `overlap` in `--force`, or print the exact `--force overlap` flag in the REFUSED message.

## Acceptance
- On a SirBepy-origin repo with an overlap hit, the script commits without `--force` and prints the info line.
- On a client repo, it still refuses by default.
- The REFUSED message names a `--force` value the script accepts.
