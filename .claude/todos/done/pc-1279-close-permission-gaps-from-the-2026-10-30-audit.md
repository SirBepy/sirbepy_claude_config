<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 2; pc-0438 created the deny list but missed the dotfile -->
# Close permission gaps: .credentials.json reads, Shortcut raw-write exemption, Linear ownership gate, broad allow rules

**Type:** task
**Origin:** dev
**Summary:** Claude can no longer read its own OAuth credentials file, and tracker-write and broad shell permissions match what the rules say.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. The settings.json part was held that night because another session had uncommitted hunks in `settings.json` (cleanupPeriodDays reorder, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), and a pathspec commit would have swept them in.

## Goal

Credential files are unreadable by tools, tracker mutations are gated as the rules describe, and broad allow rules are deliberate.

## Context

- `settings.json:137` has `Read(**/credentials.json)`, which does not match the dotfile `.credentials.json` (gitignore glob semantics). Both `~/.claude/.credentials.json` and `~/.claude-personal/.credentials.json` exist. `Read(C:/Users/tecno/.claude/**)` is allowed and transcripts are kept forever (`cleanupPeriodDays: 36500`). `hooks/sensitive-file-guard.py:26` has the same gap (it guards writes only). The deny list already holds dotfile patterns like `Read(**/.env)`, so `Read(**/.credentials.json)` follows precedent. UNVERIFIED: whether Claude Code protects its own credentials file natively. Note `cat` via Bash still bypasses a Read deny.
- `hooks/shortcut-raw-write-guard.py:125-126` exempts any session whose transcript contains "/shortcut-done-audit" or "/zirtue-release-backfill", and that exemption runs before the Testing-ceiling check at `:128`. `skills/ticket/shortcut.md:21-22` says only the backfill closes stories, but done-audit step 7 PUTs Complete.
- `skills/linear/SKILL.md:92-133` states an ownership gate that no hook enforces; `issueDelete`, priority and label changes match no guard (`hooks/linear-update-guard.py`).
- Broad allows (`npx*`, `curl*`, `gh api*`, `find*`, `xargs*`) skip the auto-mode classifier; about 45 of 119 allow rules are Mac paths, one-off pastes, redundant, or residue of the uninstalled caveman plugin.

## Approach

1. When `settings.json` has no foreign hunks (check `git diff -- settings.json`), add `Read(**/.credentials.json)` next to the existing rule; extend `sensitive-file-guard.py:26` the same way with a test.
2. Narrow the raw-write exemption to the active skill invocation (not a transcript substring) and run the ceiling check first; align `shortcut.md:21-22` with what done-audit actually does.
3. Decide with the dev whether the Linear gate needs a hook or stays prose; at minimum cover `issueDelete`.
4. Walk the allow list with the dev: drop dead/Mac/caveman rules, and decide each broad pattern.

## Acceptance

- A Read of `~/.claude/.credentials.json` is denied (prove with a canary file of the same name in a scratch dir).
- `python ci/run_all.py` passes with new guard tests.
- Allow-list changes listed in the commit body with the dev's decision per broad rule.

## Notes

- Objective fixes landed in 98193b9 and f41865c, the errored-Skill exemption hole closed in 07af7f9, done-audit exemption documented in 9b1af43 per Joe 2026-11-08.

## Decided

- Landed 2026-11-07 (objective fixes only, per the loop triage): `Read(**/.credentials.json)` added to the settings.json deny list next to the existing credentials rule; `hooks/sensitive-file-guard.py` now asks on the dotfile `.credentials.json` too; `hooks/shortcut-raw-write-guard.py` exempts a session only when `/zirtue-release-backfill` or `/shortcut-done-audit` was actually invoked (a user turn starting with the command, its command-name block, or a Skill tool call), not when the name appears anywhere in a user message; `hooks/linear-update-guard.py` asks on every `issueDelete` and on MCP delete_issue tools, since the ownership gate (creator == dev) cannot be proven from a command string. Tests are in the matching `hooks/test_*.py`.
- Broad allows (`npx*`, `curl*`, `gh api*`, `find*`, `xargs*`) left alone, as decided in the triage. The dead/Mac/caveman allow-rule walk was not done.
- Live proof of the credentials deny rule is UNVERIFIED: a nested `claude -p` canary run refused to attempt the reads (its own classifier), so nothing was proven either way. The rule has the same shape as the existing `Read(**/.env)` deny, and a settings.json deny only loads after `/respawn`.

## Decided

- [x] [SEC] done-audit vs the Testing ceiling - Joe decided 2026-11-08: keep shortcut-done-audit exempt (it PUTs Complete only on his per-ticket inline confirm). skills/ticket/shortcut.md now names it as the second exception (9b1af43).
- [x] [SEC] Walking the remaining broad allow list - Joe chose objective fixes only on 2026-11-07; the broad allows stay.

