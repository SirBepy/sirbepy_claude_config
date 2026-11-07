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

## Decided

Written by /loop-todos sub on 2026-11-07.

- The mechanism is built and committed; only the first real promotion is left (see Open questions). Pieces: `skills/cleanup-memory/lessons_sweep.py` (`scan`, `promote`, `index`; documented as `/cleanup-memory --global` in that SKILL.md), `hooks/lessons-index.py` (SessionStart, injects the 4 KB `lessons/INDEX.md`), the trigger hook scanning `~/.claude/lessons/`, a `.gitignore` allowlist for `lessons/`. Tests: `hooks/test_lessons.py`.
- Clustering is mechanical, no model call: same normalized name, or name+description token overlap of 0.35 or more, across 2+ distinct projects (a repo and its worktrees count once). 0.5 found 6 clusters and missed `feedback-auto-commit`; 0.35 finds 7 and still has no obvious false join.
- Client protection is two-layered: a cluster with any member from a project whose dir name contains a `refs/client-repos.txt` repo name is held back and never listed (5 held back at dry run), and `promote` refuses a client-project source outright.
- Proof that a promoted lesson loads where it was never learned: a nested `claude -p` run from a directory with no copy of it received the `INDEX.md` text at SessionStart and the lesson body (via its path trigger) on a Read of a matching path.

## Open questions

Written by /loop-todos sub on 2026-11-07. The next run opens with these.

- [ ] [DATA] First real promotion: the dry run over 831 feedback memories found 7 cross-project clusters, all from only two project pairs, so there is little to promote today. Which, if any, should become global lessons? `feedback-auto-commit` (server-supervisor + claude_usage_in_taskbar; CLAUDE.md already covers auto-commit, so likely a no). `local-gpu-runs-gentle-limits` and `reveal-minimum-in-outreach-emails` (dashboard-a + rodge; plausibly general). `design-review-in-demo`, `push-always-allowed`, `tell-dane-means-write-the-for-dane-doc`, `web-build-check-against-demo-per-task` name dashboard-a files or people, so they look repo-specific, not lessons. Promote with `python ~/.claude/skills/cleanup-memory/lessons_sweep.py promote ...` after Joe picks; re-run `scan` first, the corpus moves.
- [ ] [DATA] The corpus is 96 project dirs with only 7 text-level duplicates: most cross-project lessons were probably phrased differently each time and need a semantic pass, not token overlap. Wanted: a one-off panel read of the 831 feedback memory descriptions (a model call, so a spend decision for Joe) to find paraphrased duplicates, or accept the cheap scan as it is.

## Notes

- Deferred question (needs an attended session for its `hooks/`/`settings.json` writes) answered 2026-11-07: Joe said run it now, in the attended 2026-11-07 session; he approves each permission prompt as it appears.
