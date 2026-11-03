<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1152 and 1227 (both in done/) built and fixed the main path's digest step; neither mentions light.md -->
# /close --light silently drops Phase 3's screenshot count and session digest

**Type:** skill-improvement
**Origin:** ai
**Summary:** A light close, and so every lite respawn, still counts the session's screenshots and saves its session digest like a normal close.

## Why

light.md never mentions the screenshot count or digest steps, so light closes print no real count and write no digest. Found 2026-10-28 while reading it for the respawn rework.

## Goal

A `/close --light` run (and therefore every `/respawn lite`) still counts this session's screenshots and saves its session digest, the same as a normal `/close`.

## Context

`skills/close/light.md` says it "overrides Phases 1-3", and its Phase 3 only covers memory writes and todo files through one write-subagent. The main path's `skills/close/SKILL.md` Phase 3 has five steps: 1 memory, 2 todos, 3 screenshot summary, 4 session digest (`recall.py digest-save`), 5 inherited respawn detail file. Commit 2e88313 (2026-10-28) added a line to light.md that runs step 5 inline, because `/respawn lite` now routes `/auto-respawn` and `/loop-todos` respawns through `--light`. Steps 3 and 4 are still never mentioned in light.md, so a light close prints no real screenshot count for Phase 4's counter and writes no digest, and `recall.py decisions` never sees those sessions. Found while reading light.md for the respawn rework. Left out of that commit to keep its scope to respawn.

## Approach

In `skills/close/light.md` Phase 3, after the write-subagent returns, run the main path's Phase 3 steps 3, 4 and 5 inline, in that order. They are cheap: a file count, one piped `digest-save` call, one delete. Fold the existing step-5 sentence into that one line instead of keeping two separate mentions.

## Acceptance

- light.md names main-path Phase 3 steps 3-5 as running inline after the subagent.
- A normal `/close` is unchanged.
- `python ci/run_all.py` stays green apart from failures that already exist.

## Notes

- Fixed in 713c7d8.
