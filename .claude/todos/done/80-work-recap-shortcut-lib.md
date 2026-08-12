# Create ~/.claude/skills/_lib/ with shared Shortcut helpers

## Goal

Extract the repeated Shortcut JSON parsing logic from `/work-recap zirtue weekly` into a reusable Python script at `~/.claude/skills/_lib/api_helpers.py`. Update `weekly.md` to call the script instead of writing inline `python -c` one-liners each run.

## Context

Every run of `/work-recap zirtue weekly` re-writes the same inline Python logic for:
- Reading the Shortcut API token from `C:/Users/tecno/.claude/.env` (UTF-8 with BOM, requires `utf-8-sig`)
- Building a workflow state ID â†’ (name, type) map from the `/api/v3/workflows` response
- Parsing ticket JSON responses to extract id, name, state, epic, estimate, completed_at

The `curl` calls currently save responses to session-specific tool-result filenames (e.g. `bx60zsv2k.txt`) that can't be predicted. The correct pattern is for `curl` to write to fixed deterministic paths (`C:/tmp/sc/touched.json`, `C:/tmp/sc/open.json`) so the script has stable inputs.

This was converged to as the correct approach via `/iterate-it` in the 2026-05-19 session (P3: two-tier `_lib/` + per-skill scripts, with `_lib/README.md` as the primary gate and `# source: _lib/<module>` breadcrumbs on per-skill scripts that wrap lib functions).

## Approach

1. Create `~/.claude/skills/_lib/` directory.
2. Write `~/.claude/skills/_lib/api_helpers.py` with these functions:
   - `read_token()` â†’ reads `SHORTCUT_API_TOKEN` from `C:/Users/tecno/.claude/.env` using `utf-8-sig`
   - `build_state_map(workflows_json)` â†’ returns `{state_id: (name, type)}` dict
   - `fmt_ticket(ticket_json, state_map)` â†’ returns dict with id, name, state, state_type, epic, estimate, completed_at
3. Write `~/.claude/skills/_lib/README.md` with function registry and the instruction: "Read this file before writing any new script in a skill folder."
4. Update `weekly.md` curl calls to write to `C:/tmp/sc/touched.json`, `C:/tmp/sc/open.json`, `C:/tmp/sc/workflows.json`.
5. Add a `parse_shortcut.py` next to `weekly.md` that imports from `_lib/api_helpers.py`, reads the fixed temp paths, and prints structured ticket data. Add `# source: _lib/api_helpers.py` at the top.
6. Update `weekly.md` step 4 to call `python ~/.claude/skills/work-recap/zirtue/parse_shortcut.py` instead of inline `-c` calls.

## Acceptance

- `/work-recap zirtue weekly` runs without any inline `python -c` calls for JSON parsing.
- `_lib/README.md` exists and lists the function contract.
- `parse_shortcut.py` has `# source: _lib/api_helpers.py` comment at top.
- Running `parse_shortcut.py` directly (with temp files present) prints ticket data correctly.

## Notes

- Dropped via /cleanup-todos 2026-08-11: superseded - weekly.md was rewritten and the inline-python sprawl that justified _lib is gone. Confirmed by dev 2026-08-11.
