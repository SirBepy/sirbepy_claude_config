<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Cross-project lessons: promote feedback memories learned in one repo to all of them

**Type:** task
**Origin:** dev
**Summary:** A lesson about how Claude should work, learned in one project, reaches every project without growing CLAUDE.md.

## Why

Joe picked this design on 2026-10-08. At that date 803 feedback memories across 86 project memory dirs each loaded only in their own project.

## Goal

A lesson about how Claude should work, learned in one project, reaches every project, without
growing `CLAUDE.md`.

## Context

Designed in `refs/permanent-memory.md` ("Cross-project lessons"), picked by Joe on 2026-10-08 in
todo 95's brainstorm. On that date the 86 project memory dirs held 803 feedback memories, each
loading only in its own project. `CLAUDE.md` has 0 tokens of headroom. Works best after 1153
(trigger-keyed memory), since most promoted lessons should load through triggers rather than an
always-on index.

## Approach

- An explicit command (e.g. a `--global` mode of `/cleanup-memory`, or its own skill), run by one
  session, never a hook, so concurrent sessions cannot race on it.
- Read feedback memories across every project, cluster the same lesson appearing in 2+ projects,
  and propose promotions in one question card.
- Global store: a tracked folder in `~/.claude` (needs a `.gitignore` allowlist line) with a small
  byte-capped index injected by a SessionStart hook; individual lessons mostly load via 1153's
  triggers. Client-specific facts never get promoted.
- Writes go through `refs/memory-rubric.md`'s ADD/UPDATE/DELETE/NONE gate, re-reading each file
  right before editing; the per-project originals are marked superseded (see 1156), not deleted.

## Acceptance

- A dry run over the real corpus lists candidate clusters with their source files.
- Promoted lessons load in a project that never had them (prove with a nested `claude -p` run).
- No client-repo content lands in the tracked global folder.

## Notes

- Deferred question (needs an attended session for its `hooks/`/`settings.json` writes) answered 2026-11-07: Joe said run it now, in the attended 2026-11-07 session; he approves each permission prompt as it appears.
