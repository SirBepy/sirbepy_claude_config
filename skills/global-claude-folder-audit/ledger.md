# /global-claude-folder-audit ledger

Committed record across runs. `days_since.py` reads `## Runs` for the dashboard card; every auditor
gets `## Declined` as a do-not-re-report list. Append only; one line per entry.

A one-off audit on 2026-08-01, before this skill existed, rated all 75 skill folders and deleted
12 (night-run, trello, skills-help, archived-skills, explain-commit, git-init, decouple-file,
migrate-structure, web-design-guidelines, memory-trim, cron-run, schedule-once). Do not re-propose
them; the rationale is in commits d67421e and 8a39e46.

## Runs

- 2026-10-30 first run: 20 auditors + 5 refuters + 3-agent pre-change panel; 9 HIGH, ~45 MEDIUM after verification; all 9 bundles accepted (todos pc-1278..pc-1285, bundle 5 folded into pc-1270); safe doc fixes landed unattended (70a85d6, 4f0f768, 36032f0); no own skill deleted.

## Declined

- 2026-10-30 Deleting `/figma-tiles` and `/figma-pixel-diff`: the dev floated it, the panel showed they are not redundant with the Figma MCP (REST token, board sweeps, rate-limit backoff, offline export, token matching). Kept; see pc-1282.
- 2026-10-30 Hiding the figma plugin's 16 skills with `skillOverrides`: tested, it has no effect on plugin skills (either key form). Not a lever. Resolved instead by disabling the plugin at user scope (zero Figma MCP calls in the window) and enabling it per project where Figma work happens; see pc-1282.
- 2026-10-30 Deleting the `test-flow` and `obsidian-pickup-ticket` aliases: settled aliases from the 2026-08-01 audit. Kept.
- 2026-10-30 A single tracker-guard dispatcher hook: `hooks/linear-create-guard.py:10` keeps one guard per platform on purpose. Rejected by the refuter.
