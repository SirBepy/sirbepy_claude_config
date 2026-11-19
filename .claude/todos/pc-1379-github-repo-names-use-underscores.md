<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: pc-0247 repairs README/og-image/PWA on shipped web projects, unrelated to naming -->
# GitHub repo and project folder names use underscores

**Type:** task
**Origin:** dev
**Summary:** Record Joe's naming rule globally: new GitHub repos and project folders use underscores (asset_vault), not hyphens.

## Goal

When Claude creates or names a repo or project folder, it uses underscores wherever the name allows.

## Context

Joe said this on 2026-11-19 in the Asset Vault main chat (eaff2241), while asking to rename claude_usage_in_taskbar to claude_conductor and asset-vault to asset_vault:

> we should always use underscores when we can for github repos

The rule could not be recorded from that project session, because the global ~/.claude tree may only be edited when Joe says so in the session.

## Approach

Add one line to the right global place. That could be `code-style/` (a general naming file) or a project-creation step such as `create_project`, `/github-pages-init` or a repo-init skill, whichever is read when a repo is named. Keep it to one rule: underscores in repo and folder names; crate and package names follow their own ecosystem rules (Cargo crates and npm packages keep hyphens).

## Notes

- Existing repos are renamed one by one when Joe asks, not in bulk.
