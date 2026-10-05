<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=6, reconfirm-count=1, content-hash=1fc28024 -->
<!-- duplicate-checked: no live todo covers a Shortcut fetch-dossier-panel pipeline (grep "triage" 2026-10-05) -->
# Shortcut "fetch, build dossiers, 3-judge panel, tally" pipeline was hand-built three times in one session

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-05

## Goal

Decide whether a reusable helper (a script under `skills/ticket/` or a small skill) should do the mechanical half of Shortcut panel work: pull stories with every comment, render dossiers, batch them, and tally a 3-judge workflow's votes.

## Context

- The 2026-10-05 zng-biller session built this from scratch in `C:\tmp\sc-triage\` (scratch): `sc.py` (API client; search caps at 1000 results, so it splits queries by story type), `fetch_helpers.py` (dossier renderer with comments, links, PRs, custom fields), batch writers, and `consensus.py` / `plan_tally.py` (vote tally). It ran three separate panels on top: FE triage over 541 stories, assign-to-Joe votes on 12 stories, and Biller Portal estimates over 11 work units.
- Joe now asks for 3-subagent panels as a matter of routine. See the vault note `Working with Claude - preferences.md` (2026-10-05 bullet) and zng-app memory `feedback_n_agent_verification_same_question`.

## Approach

1. Check whether `/ticket` or `/shortcut-done-audit` already has a fetch or dossier helper to extend.
2. If not, move the API client plus the dossier renderer into one script with `search` / `dossier <ids>` / `batch` subcommands. Keep the judging in Workflow scripts. The panel prompt should default to the identical forced-verdict form, not lenses.
3. Tallying (unanimous / disputed / median estimate) belongs in the same script, since its input is plain JSON.

## Acceptance

- A future session can run a Shortcut panel over N stories without rewriting the client, the dossier renderer or the tally.
- The 1000-result search cap and the token-file BOM gotcha are handled once, in that script.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): skills/ticket/scripts/shortcut_triage.py (search with per-type split past the 1000 cap, dossier JSON, render, batch, consensus vote/median), GET-only enforced in api_call, BOM-safe token read; 34 offline tests; pointers in /ticket and /shortcut-done-audit SKILL.md. Not yet run against the live API: smoke it with a small query on first real use.
