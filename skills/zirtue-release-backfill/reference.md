# zirtue-release-backfill: reference

Read on demand from `SKILL.md` (REST calls, edge cases, and never-does list — not needed for every run).

## Shortcut REST quick reference

Token loaded from `~/.claude/.env` (BOM in file, strip with `sed 's/^\xef\xbb\xbf//'`).

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')

# Get story
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN"

# Search (raw query-string form, not curl -G --data-urlencode - see refs/shortcut-api.md
# "Searching stories" for the canonical recipe, pagination, and query operators; the two
# encoding forms' equivalence is unverified, so this one stays as-is)
curl -s "https://api.app.shortcut.com/api/v3/search/stories?query=<urlencoded>&detail=full&page_size=25" -H "Shortcut-Token: $TOKEN"

# Update story
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"custom_fields":[...full merged array...],"workflow_state_id":500018258}'   # 500018257 for a Gate E move to Testing

# Get Release enum (uncached — use this if MCP returns stale data)
curl -s "https://api.app.shortcut.com/api/v3/custom-fields/68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb" \
  -H "Shortcut-Token: $TOKEN"
```

## Edge cases

- **Cross-repo fix (zng-app + zng-admin).** Status `multi-repo`. Ask dev which release is primary; Shortcut only allows one Release value per ticket.
- **No commit found.** Status `needs-human`. Don't guess from title alone unless dev opts in.
- **Tag naming drift.** If you see tags that don't match `v<major>.<minor>.<patch>+N` (app/admin) or `v<major>.<minor>.<patch>` (api), flag and stop. Update this skill before proceeding. A repo with zero tags matching that shape at all (zng-biller until 2026-11-05) is not drift - it's never-deployed; see the Repos section in SKILL.md.
- **Enum value missing.** Create it with `scripts/add_release_values.py` (SKILL.md step 10), only for a label taken from a real version tag. Never hand-roll the `PUT /custom-fields/{id}`: omitting an existing value from `values` deletes it.
- **Repo working tree dirty.** `git fetch` still works but never `checkout` anything. This skill only reads tags / log.
- **Estimate already set on ticket.** Never overwrite. Only fill if currently `None`.
- **Existing field already set to wrong value.** Do not "correct" silently. Other-field fills are insert-only — only touch fields that are currently empty.

## What this skill never does

- Never commits in any repo. (Sibling repo rule.)
- Never creates a Release enum value that isn't backed by a real version tag, and never edits or deletes an existing one.
- Never applies field updates without explicit approval at gates A/B/C. (Gate D moves are default-on but always announced in the report first, and nothing is applied before the gates are answered.)
- Never PUTs a partial `custom_fields` array (would wipe other fields).
- Never overwrites already-set scope fields (Pri/Skill/Prod/Tech/Estimate). Insert-only.
- Never moves a ticket to any state other than `Complete` (from `Ready for deploy` only, Gate D) or `Testing` (from Backlog / To Do / In Progress, Gate E), and never moves anything when the dev opted out. Both moves are announced in the report first, never hidden.
- Never touches another developer's ticket (a `BE:` ticket, Stevan's work), even one the dev owns on the card.
