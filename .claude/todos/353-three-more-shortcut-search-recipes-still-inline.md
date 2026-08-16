<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Three more `search/stories` recipes are still inline, outside todo 343's named scope

**Type:** skill-improvement
**Origin:** ai

## Goal

Finish the dedupe todo 343 started, so `refs/shortcut-api.md` is genuinely the only place the
`search/stories` mechanics live.

## Context

Todo 343 pointed the three call sites it named (`shortcut-pickup-ticket`, `shortcut-done-audit`,
`work-recap/zirtue/weekly.md`) at the shared recipe on 2026-08-16, commit `8abd412`. A grep of the
whole tree afterwards found three more that were outside that todo's scope and deliberately left:

- `skills/shortcut-create-ticket/ground-check.md:36` - a full inline curl recipe with `$TOKEN`, no
  page size, no pagination. This is the one that matters most: it runs inside the mandatory
  ground-check gate on every ticket creation.
- `skills/shortcut-create-ticket/SKILL.md:81` - a bare inline `search/stories?query=...` mention in
  a staleness-check note, not a runnable block. Cheapest of the three.
- `skills/zirtue-release-backfill/reference.md:16` - a full inline recipe.

## Approach

Same pointer refactor todo 343 used: keep only the query string, page size and client-side filters
at each call site, move everything mechanical to the ref, extend the ref first if a query shape is
not covered, and update the ref's header list.

One real difference to resolve rather than paper over: `work-recap/zirtue/weekly.md` builds its GET
as a raw query string with `+` for spaces, while the ref's canonical recipe uses
`curl -G --data-urlencode`. Todo 343's builder left the actual invocations untouched because
byte-for-byte equivalence was never verified, specifically whether Shortcut's API decodes a literal
`+` as a space. **Verify that against the live API before reconciling the two shapes.** If they are
equivalent, say so in the ref so nobody re-opens it; if not, the ref needs to document both.

## Acceptance

- A tree-wide grep for `search/stories` finds one full recipe, in `refs/shortcut-api.md`, plus
  references to it.
- The `+` versus `--data-urlencode` question is answered with evidence, not assumed.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` from todo 343's builder report.
- Related: [[343-shortcut-call-sites-still-hand-roll-search]] in `done/`, and
  [[351-unify-ticket-skills-behind-one-platform-inferring-entrypoint]], which would subsume this if
  it lands first.
