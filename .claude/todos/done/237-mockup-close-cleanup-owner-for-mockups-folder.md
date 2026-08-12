<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=97727042 -->
# mockup + close: give .for_bepy/mockups/ and mockup-step.json a real cleanup owner

**Type:** skill-improvement

## Goal

`skills/mockup/SKILL.md` promises cleanup of its own scratch artifacts
(`.for_bepy/mockups/*.html` for the standalone-file branch, `.for_bepy/mockup-step.json`
for plan-mode runs) "at session end," but nothing currently actually deletes them -
neither `/mockup` itself nor `/close`'s purge phase owns this. Extend either `/close`'s
existing purge mechanism or `/mockup`'s own promised (but unbacked) step 7 cleanup to
actually remove these files.

## Context

`skills/mockup/SKILL.md` (as of 2026-08-01):

- Step 4 (standalone-file branch), line 24: `Save it to \`.for_bepy/mockups/\`
  (gitignored scratch, same convention as \`.for_bepy/screenshots/\`; create the folder
  if missing).` - the file is explicitly described as scratch, matching
  `.for_bepy/screenshots/`'s convention.
- Step 5's mockup-step.json handling, line 42: `When using \`--plan\`, write the plan
  JSON to the fixed path \`.for_bepy/mockup-step.json\`. Reuse and overwrite this same
  path every round of a session instead of naming a new file per round. Delete it once,
  at session end, alongside the rest of the \`.for_bepy\` scratch cleanup, not after each
  round.` - this explicitly promises deletion "at session end, alongside the rest of the
  `.for_bepy` scratch cleanup," implying `/close` is expected to own it, but `/close`'s
  own SKILL.md purge phase (Phase 0/3, referenced by `/screenshot` and `/mockup`'s own
  screenshot-output convention at mockup SKILL.md line 32: "matching `/close`'s purge
  scheme") is scoped to `.for_bepy/screenshots/<pid>-<start-ticks>/` per-session
  subfolders (per the global CLAUDE.md "Throwaway verification screenshots" rule) - it
  has no documented awareness of `.for_bepy/mockups/` (the standalone HTML output, NOT
  under a per-session screenshots subfolder) or the fixed-path `.for_bepy/mockup-step.json`
  file at all.
- Step 7, line 46, promises cleanup only for the REAL-COMPONENT branch's scratch route
  ("auto-delete the real-component branch's scratch route once the dev stops
  iterating") - it says nothing about the STANDALONE-file branch's `.for_bepy/mockups/`
  output or the plan-mode `.for_bepy/mockup-step.json` file, both of which are
  session-scoped scratch same as screenshots but currently orphaned by every existing
  cleanup mechanism.

## Approach

Two viable owners - pick one when this is picked up (don't do both, that risks a double-
delete race or divergent logic):

**Option A - extend `/close`'s purge phase.** Read `skills/close/SKILL.md`'s Phase 0/3
purge logic in full. Add `.for_bepy/mockups/*.html` (session-scoped, or ALL of them if
mockups aren't meant to persist across sessions - confirm this against how
`.for_bepy/screenshots/` scopes by pid+ticks, and decide whether mockups need the same
per-session subfolder treatment or can be treated as always-purge-on-close since they're
never portfolio keepers) and the fixed-path `.for_bepy/mockup-step.json` to whatever
`/close` already deletes. This keeps ONE cleanup owner for all `.for_bepy` scratch, which
`/mockup`'s own Step 5 language ("alongside the rest of the `.for_bepy` scratch cleanup")
already assumes.

**Option B - back `/mockup`'s own Step 7 promise.** Add an explicit cleanup action to
Step 7 (or a new final step) that deletes `.for_bepy/mockups/<idea>.html` and
`.for_bepy/mockup-step.json` directly, mirroring the existing real-component-branch
scratch-route deletion already in Step 7, rather than relying on `/close` running later
(the dev may never invoke `/close` in a given session, e.g. a short ad-hoc mockup check).

Whichever option is chosen, update the OTHER skill's docs to explicitly say "cleanup is
owned by X, not here" so the promise isn't left dangling in two places again.

## Acceptance

- `.for_bepy/mockups/*.html` and `.for_bepy/mockup-step.json` are actually deleted by
  SOME skill's real, executed logic (not just described as intended) - verify by running
  `/mockup` (standalone branch, plan mode) end to end, then triggering whichever cleanup
  path was chosen, and confirming the files are gone.
- The chosen skill's SKILL.md documents the mechanism concretely (exact path, exact
  trigger point), not just "at session end" prose.
- The non-owning skill's file is updated to point at the owner rather than repeating a
  vague promise.

## Notes

- completed, commit e6f2199
