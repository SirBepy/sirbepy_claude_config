<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 101 is the memory-rubric read gate, a different surface that only shares the words recall/phase/session -->
# Recall phase 2: per-session digests and the decision ledger

**Type:** task
**Origin:** dev

## Goal

Old chats get a short cached digest (what was done, decisions taken, options rejected and why),
and `recall.py decisions <topic>` lets any session find a past decision before re-proposing a
rejected option.

## Context

Designed in `refs/permanent-memory.md` ("Digests and the decision ledger"), scope picked by Joe on
2026-10-08 in todo 95's brainstorm (recall design "Index + search, then digests"; extra area
"Decision ledger"). Phase 1 (`skills/recall/recall.py`) is built: `show` already prints one
session's extracted conversation. Evidence for the ledger: on 2026-08-01 the whole vault design
was re-derived while the committed design sat in that session's context
(`feedback_context_loaded_is_not_applied`). Digests are the one recall output that is not
rebuildable from transcripts (design D9), so they must never live under `index/`, which is
disposable.

## Approach

- Digest store: `~/.claude/memory-archive/digests/<sessionId>.md`, one file per session (no
  shared file, so concurrent sessions never contend). Sections: Done, Decided, Rejected (option +
  reason), Open. Header cites date, repo, scope, session id.
- `recall.py digest-save <sessionId>` reads the digest on stdin and writes it atomically, refusing
  to overwrite unless `--replace`. `show` prints the cached digest above the conversation when one
  exists, and a one-line nudge to write one when it does not.
- `SKILL.md`: after reading an old session through `show` with no digest, write one. No extra
  model call: the session already read the chat.
- `/close`: write the same digest for its own session (it already reads its own transcript).
- `recall.py decisions <terms>` searches only the Decided and Rejected sections, newest first,
  with citations, inside the same RECALLED DATA fence.
- `/brainstorm` step 1: run `recall.py decisions <feature keywords>` next to the existing todo
  grep.

## Acceptance

- `test_recall.py` covers digest-save (atomic, no silent overwrite), show printing a cached digest,
  and decisions matching only decision sections.
- A brainstorm on a topic with a recorded rejected option surfaces it in step 1.
- Deleting `index/` and rebuilding leaves every digest intact.
