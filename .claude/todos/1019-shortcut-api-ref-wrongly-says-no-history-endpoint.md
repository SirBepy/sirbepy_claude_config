# refs/shortcut-api.md wrongly says there is no story history endpoint

`GET /api/v3/stories/<id>/history` exists and returns real workflow-state transitions with
timestamps and the member who made each one. Verified live 2026-09-25 against story 55411:
HTTP 200, 4 entries, including

    2026-09-22T14:39:41Z  workflow_state_id {'old': 500018254, 'new': 500018257}   # To Do -> Testing
    2026-09-23T18:25:49Z  workflow_state_id {'old': 500018257, 'new': 500018254}   # Testing -> To Do (QA bounce)

Two places currently assert the opposite, so every caller infers board-lag from commit dates
instead of reading it:

- `refs/shortcut-api.md` documents `GET /stories/<id>` and `search/stories` but never mentions
  `/history`.
- `skills/shortcut-done-audit/investigation-prompt.md` states outright: "There is no separate
  history endpoint; infer state-lag from these fields plus git." That sentence is wrong and is
  pasted into every per-ticket dispatch, so each subagent is told not to look.

Why it matters: question 4 of the audit ("was it just done and never moved?") is exactly a
state-transition question. On 55411 the history proved the ticket had gone To Do -> Testing on
push and been bounced back to To Do by QA 2 seconds after their comment, which turns an
ambiguous "board might be lagging" into a certain "QA actively rejected this". Guessing from
commit timestamps cannot produce that.

## What to change

1. Add a `## Fetching a story's history` section to `refs/shortcut-api.md` with the curl and the
   response shape (top-level list, each entry `{changed_at, actions[]}`, each action carrying
   `entity_type` and a `changes` map keyed by field name with `{old, new}`).
2. Replace the "There is no separate history endpoint" sentence in
   `skills/shortcut-done-audit/investigation-prompt.md` with an instruction to fetch the history
   and quote the actual transitions when answering question 4.
3. Check the other Shortcut callers named at the top of `refs/shortcut-api.md`
   (`/ticket`, `shortcut-priorities`, `work-recap`, `zirtue-release-backfill`) for the same
   stale claim or for a workaround that the endpoint now makes unnecessary.

Found while running `/shortcut-done-audit` in zng-app; a sonnet investigation subagent tried the
endpoint despite the prompt saying it did not exist.
