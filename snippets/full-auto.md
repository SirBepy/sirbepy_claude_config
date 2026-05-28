# Full-auto policy

Projects that `@import` this snippet opt into broad Claude autonomy: Claude proceeds on its own across the routine decisions listed below instead of stopping to ask. Joe uses this for personal projects only.

This file is a manifest. It imports the individual autonomy snippets so a repo opts into all of them with one line. Adding a new autonomy snippet later means editing this file alone: every importing repo inherits it with no per-repo change.

## What this grants
- Auto-commit on qualifying turns (see auto-commit).
- Skip the subagent-vs-inline question; pick the mode and go (see auto-execution-mode).
- Work directly on the default branch; skip branch-creation consent (see auto-branch-main).

## What this deliberately does NOT grant
Full-auto removes the routine "may I?" friction. It does not remove the hard stops. Each imported snippet keeps its own internal guardrails, and these always hold regardless of full-auto:
- Destructive or irreversible actions (force-push, hard reset, history rewrite, bulk delete, DB migration, publish/deploy) still require explicit confirmation.
- Secrets, credentials, and `.env` files are never committed or printed.
- Installing packages or new tooling still requires asking first.
- Anything touching production or a shared remote still requires asking first.

## Maintenance constraints
- One import per line. Put each snippet's description on a comment line ABOVE its import, never as a trailing `#` on the `@import` line (trailing text is parsed as part of the path and breaks the import).
- Snippets listed here must NOT themselves `@import` another snippet. Import depth is capped at 4 hops (CLAUDE.md -> full-auto.md -> snippet = 3, leaving no room for a 4th). A nested import would silently drop.
- A missing target file imports as a silent no-op. Before relying on full-auto in a new context, confirm Claude actually knows these rules (e.g. it cites the auto-commit policy). If it doesn't, an import target is missing.
- The visible "What this grants" list above is the single source of truth for what's imported. When you add or remove an `@import` line below, update that list in the same edit.

<!-- Active autonomy snippets. One import per line. Descriptions live in "What this grants" above, not here. -->
@~/.claude/snippets/auto-commit.md
@~/.claude/snippets/auto-execution-mode.md
@~/.claude/snippets/auto-branch-main.md
