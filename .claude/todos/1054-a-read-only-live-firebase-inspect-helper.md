<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=6, reconfirm-count=2, content-hash=1277c0e8 -->
# A read-only live Firebase inspect helper

**Type:** skill-improvement
**Origin:** ai

## Goal

One tool that reads a Firebase project's live state for debugging without hand-rolling `node -e`
fetch snippets every time. Read-only by default:

- the deployed rules releases (`updateTime`), and a diff of each deployed ruleset against the repo's
  `firestore.rules` / `storage.rules`
- index and field-override state (e.g. `collectionGroups/<cg>/fields/<field>` -> READY/CREATING)
- a collection-group query summarising documents (array lengths per field, timestamps, writerId)
- a single document dumped to a local JSON file as a backup

## Context

In the countoff session of 2026-09-30, Claude hand-wrote the same pattern six times: run
`firebase projects:list` to refresh the token, read `access_token` from
`~/.config/configstore/firebase-tools.json`, then `fetch` against `firebaserules.googleapis.com` or
`firestore.googleapis.com/v1/.../documents:runQuery`. That pattern is what found the root cause:
the live rules were three weeks older than the repo's, which is invisible from the code. It also
found and backed up the overwritten project data. Each snippet was rebuilt from scratch, and each
one carried the risk of an accidental write.

Other Firebase-backed projects (pomalo, and anything else with `firebase.json`) have the same blind
spot: CI rarely deploys rules, so "the repo says X" is not "production enforces X".

## Approach

A script under `~/.claude/tools/` (e.g. `firebase-live.cjs`) with subcommands `rules`, `index`,
`query <collectionGroup>` and `dump <docPath> <outFile>`, plus a line in a relevant ref or skill
pointing at it. It should never issue PATCH/DELETE. Writes to production stay a deliberate,
hand-built, dev-approved step. The auto-mode classifier also refuses `firebase deploy`, which is
the right default.

## Verify

Run each subcommand against countoff (`generic-sirbepy-project`). `rules` should report the
2026-09-30 release as matching the repo's `firestore.rules`.

## Notes

- Phase 0 answer (Joe): allow tools/firebase-live.cjs (read-only helper reading the firebase-tools token cache) for one builder run in this loop. (2026-10-07, /loop-todos Phase 0)
- /loop-todos 2026-10-05: BLOCKED. A builder's Write of tools/firebase-live.cjs (read-only GET/runQuery helper reading the firebase-tools configstore token) was denied by the auto-mode classifier as Credential Exploration; not retried. Needs Joe to allow that file kind, or to build it himself.
