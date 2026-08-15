<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=538ea39a -->
# No skill covers querying/searching Shortcut, only creating and updating stories

**Type:** skill-improvement
**Origin:** ai

## Goal

Give Shortcut READ/SEARCH operations (fetch a story with comments, sweep a backlog column, search
by title precisely) the same skill support that create (`shortcut-create-ticket`) and update
(sc-97, completed commit `fa3723a`) already have, so sessions stop hand-rolling one-off Node/Python
scripts against the REST API every time.

## Context

On 2026-08-13/14 (zng-admin, cross-referencing 7 AI todos against Shortcut) a single session
hand-wrote four throwaway Node scripts to `C:/tmp/`: `fetch_sc.js` (single story + comments),
`search_sc.js` / `search_sc2.js` (search with pagination), `sc_workflows.js` (list workflows/
states). Each re-derived the same boilerplate:

- BOM-safe token read from `~/.claude/.env` (recurs every few sessions - see
  `reference_shortcut_api_token` memory and zng-admin's `feedback_shortcut_ticket_transitions` -
  the BOM comes and goes between sessions, most recently back on 2026-08-14 after being reported
  gone on 2026-08-11).
- Pagination handling for `/api/v3/search/stories` (`next` cursor).
- Discovering, by trial and error in-session, that the search API's free-text `query` param is
  fuzzy/relevance-ranked even combined with `state:"X"` - it returns unrelated stories ranked in,
  not a real AND filter. `title:"exact phrase"` scopes correctly, except a colon inside the quoted
  phrase (`title:"AP:"`) gets dropped and matches the bare token as a substring of unrelated words
  (`"Web App"` contains `AP`), so a punctuated phrase still needs local post-filtering.

None of this is captured anywhere reusable - the precision gotcha in particular is a real trap
that costs a full round of noisy, low-signal results before it's diagnosed.

## Approach

Extend `~/.claude/skills/shortcut-create-ticket/` (or add a sibling `shortcut-search`/
`shortcut-query`) with:

1. A shared token-read helper with BOM handling already solved (same ask as sc-97's update skill -
   check whether that skill already has one and reuse it rather than re-deriving a second helper).
2. A `search(query, opts)` wrapper that documents the `title:"..."` precision requirement and the
   colon/punctuation gotcha above, with pagination handled internally.
3. A `getStory(id)` wrapper that returns the full story including `comments`, for provenance-
   checking claims found in ai-todos (see `feedback_todo_decision_citations_unverified` memory,
   zng-admin, 2026-08-14 - a todo's own "Product decision" citation turned out to have zero backing
   anywhere in Shortcut, only found by actually reading ticket comments).
4. The workflow-state id table already captured in `reference_shortcut_workflow_states` memory,
   pinned in the skill instead of memory-only (mirrors sc-97's ask for the same table).

## Acceptance

- Fetching a story with comments, and searching a backlog column by title, both work through the
  skill without writing a throwaway script.
- The `title:` precision requirement and colon-substring gotcha are documented somewhere a cold
  session actually reads before writing its own search query.
- No path in it posts a comment or mutates a story - read-only.
