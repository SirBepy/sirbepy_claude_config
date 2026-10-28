<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=5dc4a2af -->
<!-- duplicate-checked: 210 (done) was manual multi-account wrappers, 235 (done) was create-pr image upload; neither covers repo creation with no origin -->
# gh-account-switch hook can't pick the account for `gh repo create` in a repo with no origin yet

**Type:** skill-improvement
**Origin:** ai

## Goal

`gh repo create` from a fresh personal repo never lands on a work account.

## Context

2026-10-02, project mc_plugins_tag (personal): Claude ran `gh repo create mc-plugins --private --source <dir> --push` right after `git init`. `hooks/gh-account-switch.sh` maps the account from the repo's `origin` remote, but a fresh repo has none, so gh used whichever account was active (JosipMuzicZirtue, a work account) and created `JosipMuzicZirtue/mc-plugins`. Claude had to recreate it as `SirBepy/mc-plugins` and Joe had to delete the stray repo by hand (Claude's token lacked `delete_repo`).

## Approach

In `hooks/gh-account-switch.sh`: when the command is `gh repo create` and there is no origin, either default to the personal account (SirBepy) unless the repo name/owner argument names an org from the mapping, or block with a message telling Claude to pass an explicit `OWNER/NAME` and switch accounts first. Mirror in CLAUDE.md's gh CLI section only if the hook can't cover it.

## Acceptance

- Hook self-test: `gh repo create foo --private --source .` in a repo without origin resolves to SirBepy (or is blocked with guidance).
- Existing origin-based switching unchanged.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), lane D2, test-first (RED against HEAD, then GREEN).
