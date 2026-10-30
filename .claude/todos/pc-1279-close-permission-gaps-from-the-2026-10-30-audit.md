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
