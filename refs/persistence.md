# Persistence Reference

The trigger rule lives in `~/.claude/CLAUDE.md` under "Persistence". This file holds the expanded rule + the past incident.

## The rule, expanded

Default to in-memory state (Riverpod / context / useState / module-scope). Persist (localStorage, sessionStorage, cookies, IndexedDB, disk, DB) ONLY when you can state, *before writing the code*, the specific user-facing behavior it preserves across tab close or refresh. If you cannot name that behavior, do not persist.

When extending an existing persistence layer (e.g. adding a field to a storage class), re-check whether the underlying pattern still matches the current UX. Existing code is not evidence the pattern is right.

## Past incident

A pending-login email was persisted to localStorage in a flow whose UX is "refresh redirects to login." Persistence was contradictory by definition and introduced a race between in-memory and persisted state. It should have stayed in Riverpod (`keepAlive: true`) with zero disk.
