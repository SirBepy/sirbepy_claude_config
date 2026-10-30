<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 8; pc-1263 is the memory byte cap, a different fix -->
# Clean up dead files, root clutter and stale memory entries

**Type:** task
**Origin:** dev
**Summary:** Leftover backups, junk files and memories that contradict current rules are removed or corrected.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. Untracked deletes are irreversible and memory edits go through the memory rubric, so this was left for an attended run.

## Goal

The repo root holds no stray files, no unreferenced agent or command lingers, and the `~/.claude` memory index stops contradicting the rules.

## Context

- Root clutter in `C:\Users\tecno\.claude` (untracked, so not recoverable from git; confirm with the dev): `nul`, `settings.json.bak`, `settings.json.orig`, `settings.json.bak-devguard`, `.caveman-active` (caveman plugin uninstalled), `COMMENTS_FOR_BEPY.md`, `TODO-for_bepy-structure-and-comments-cleanup.md`; `IDEAS.md` after moving its content to the Obsidian vault. NOT clutter: `.env.bak` (`skills/clockify-reconciliator/hubstaff.md:50`: `hs_get_token.ps1` rewrites it on each Hubstaff token rotation).
- `agents/design-review-agent.md` + `commands/design-review.md`: nothing references them and the Playwright/context7 MCPs they want are not configured for this config dir. But `/design-review` is a visible slash command the dev can type, so ask before deleting (panel split on this). If deleted, `context/design-principles.md` and `context/style-guide.md` lose their only reader; `context/design-principles.md` holds the web-guidelines rules salvaged in d67421e, so move those to `code-style/` first.
- NOT orphans: `refs/design-principles-fibo-draft.md` (the dev pushed back on deleting it), `refs/hook-reload-probe-464-findings.md` (a memory cites it by path). `refs/claude-md-rule-force-audit.md` is archive-at-most.
- Memory index `projects/C--Users-tecno--claude/memory/MEMORY.md` (19,983 bytes): delete `feedback_blockquote_tilde_dot_escaping` (superseded by the fenced-block rule in `refs/copy-paste-format.md:73`) and `feedback_for_bepy_scope` (duplicates CLAUDE.md); UPDATE, not delete, `feedback_git_commit_always_allowed` (holds a unique /autopilot-oracle trap), `feedback_no_work_with_messages` (vs CLAUDE.md "edit freely"), `project_superpowers_migration` (plugin still installed for dashboard-a); `reference_claude_roots_layout` still treats `.claude-fibo` as live. About 8 cross-project preferences there belong in the vault per CLAUDE.md's vault rule.
- `skills/sentry/SKILL.md:22,30` call `~/.claude/scripts/*.ps1`, and `scripts/` is entirely gitignored (`.gitignore:2` is `*` with no allowlist entry), so a fresh clone loses them; same for `aiusage-hook.ps1` wired at `settings.json:202,658`.
- `hooks/precompact-backup.py` writes a file nothing reads; the dev closed pc-0426 as a deliberate experiment. Low priority.

## Approach

Ask the dev once (one card) for the root deletes and the design-review command; delete the confirmed ones. Apply memory changes through `refs/memory-rubric.md`, index line and file together. Decide with the dev whether `scripts/` gets a `.gitignore` allowlist entry.

## Acceptance

- `Get-ChildItem C:\Users\tecno\.claude -File -Force` shows none of the confirmed clutter.
- Every memory change keeps index line and file in sync.
