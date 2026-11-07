<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1302 (live) is about the outbound guard blocking a curl GET loop, done/pc-1096 built shortcut_triage.py's search/dossier/render pipeline for panel triage; neither gives a one-shot "state of these ids" read, which is what every chat keeps hand-writing -->
# /ticket skill: a one-shot Shortcut state reader so chats stop hand-writing GET scripts

**Type:** skill-improvement
**Origin:** ai
**Summary:** Add a `states <ids>` subcommand (or a small sibling script) to `skills/ticket/scripts/shortcut_triage.py` that prints state, blocked flag, epic, owners, updated_at and the last comment for a list of story ids, and point the skill text at it as the way to read ticket state ad hoc.

## Goal

A session that needs "what state are sc-56598, 56551, 56595 in, and what was the last comment" runs one documented command instead of writing a fresh Python heredoc that re-implements token loading, workflow-state lookup and member-name lookup.

## Context

- 2026-11-03, zng-app hub session deb6d393: the same ~25-line `python -I - <<'EOF'` script (read `~/.claude/.env` for the Shortcut token, GET `/workflows` to map `workflow_state_id` to names, GET `/members` for mention names, then GET `/stories/{id}` per id and print state / blocked / epic / owners / updated / last comment) was written three separate times in one session. The 2026-11-03 handoffs pc-0254, pc-0256 and pc-0257 in zng-app each tell the next reader to "use a small Python GET script" for the same job, so other chats rewrote it too.
- Why not curl: `hooks/outbound-verify-guard.py` blocks a read-only curl GET inside a shell loop (live todo pc-1302, closed-then-recurred pc-1151). The Python heredoc is the workaround everyone converges on.
- What exists: `skills/ticket/scripts/shortcut_triage.py` has `search`, `dossier`, `render`, `batch`, `consensus` (SKILL.md:266-269). `dossier` reads pre-fetched `*.json` from `--story-dir` and needs `--refs` and `--out` (`dossier --help`, 2026-11-03), so it is a pipeline stage for panel triage, not a quick read. `read_token` (line 45) and `api_call` (line 59) in that file already do the token and HTTP part.
- Memory `reference_shortcut_api_token` (zng-app project memory) holds the token recipe; the skill text does not name an ad-hoc read path.
- 2026-11-03, zng-biller gate chat b457a79a: the same token-loading boilerplate was hand-written a fourth time, as three scripts in `.for_bepy/gate/` (`sc_get.py` read, `sc_put_state.py` for the post-push Testing move, `sc_comment.py` for the verified QA comment). The write half is the Post-push ticket move in `/commit`, which every push runs, so the `states` reader alone leaves two of three scripts still hand-rolled; consider `move <id> <state-name>` and `comment <id> <text>` subcommands in the same pass (the comment one must keep the text literal in the command line so `outbound-verify-guard.py` can match it).

## Approach

1. In `shortcut_triage.py`, add `cmd_states(args)`: positional `ids`, optional `--comments N` (default 1, the last comment), optional `--json`. Reuse `read_token` and `api_call`; fetch `/workflows` and `/members` once; print one line per story in the shape `sc-<id> | <state> | blocked=<bool> | epic=<id> | owners=<mentions> | upd=<ts> | <name>` followed by the last comment's timestamp, author mention and first ~120 chars. Unknown id: print the HTTP status, keep going, exit 1 at the end.
2. Register it in `build_parser()` (line 462) and add a test next to `test_shortcut_triage.py` with a stubbed `api_call`.
3. In `skills/ticket/SKILL.md` (near line 266) and `shortcut.md`, add two lines: ad-hoc reads go through `python -I ~/.claude/skills/ticket/scripts/shortcut_triage.py states <ids>`; never a curl loop (pc-1302) and never a fresh heredoc.
4. Optionally retire the "use a small Python GET script" advice in the zng-app handoff files once the command exists (they are archived handoffs; a note in pc-0258's Verify list is enough).

## Acceptance

- `python -I shortcut_triage.py states 56598 56595` prints both stories' state and last comment with member names resolved, in under 5 s, with no file writes.
- The test covers one story with comments, one without, and one 404.
- SKILL.md names the command; a fresh session reading only SKILL.md finds it without opening the script.
- Does not change `search`/`dossier`/`render`/`batch`/`consensus` behaviour (existing tests still pass).
