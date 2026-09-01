<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=9, reconfirm-count=2, content-hash=58ada033 -->
<!-- duplicate-checked -->
# Nothing checks a todo is filed in the repo it changes, and a whole autopilot run acted on the wrong ones

**Type:** skill-improvement
**Origin:** dev

## Goal

Make "a todo belongs in the backlog of the repo it changes" survive contact with a real session.
It is written down once, in prose, in one place, and nothing on the write path or the review path
looks at it - so mis-filed todos accumulate and then get EXECUTED from the wrong session.

## Context

Raised by Joe on 2026-08-22, in the hubbub session, unprompted and annoyed: "wait why did you work
on a game? shouldnt that be in the todos of that project? ... if theres todos for a project they
gotta be moved to the right project!!! cuz this is rly annoying".

**The rule exists.** `CLAUDE.md:94`:

> **A todo belongs in the backlog of the repo it changes.** A finding about the global `~/.claude`
> tree (a skill, a global rule, a hook, `CLAUDE.md` itself) goes in the `~/.claude` repo's own
> backlog ... NEVER in the surfacing project's `.claude/todos/`.

**Nothing enforces or even mentions it anywhere else.** Verified against the tree on 2026-08-22:

- `skills/close/ai-todos-format.md` has a `## What belongs in the backlog` section (line 286). It
  defines what KIND of item qualifies and never says which repo's backlog receives it. Its
  `## Git policy`, `## Backlog file: filename and id` and `## Off-limits content` sections are
  likewise silent.
- `hooks/todo-duplicate-guard.py` fires on `\.claude/todos/\d+-.*\.md$` and checks the DESTINATION
  backlog for content duplicates. It already has the write path and the file content in hand, and
  does not look at allocation at all.
- `skills/cleanup-todos/SKILL.md` re-verifies each todo's premise against the tree and scores it
  for staleness. It has no "is this even the right repo" pass.
- `skills/create-todo/SKILL.md` (this todo's own entry point) never asks the question either.

**The incident, in full, because the cost is the point.** hubbub is a platform repo with four
sibling game repos (`../hubbub-game-*`), each its own git repo. Two todos in hubbub's backlog were
entirely about the game repos:

- todo 60 - two game repos rendered `player.avatarId` as raw text
- todo 63 - the four game repos had drifted on Vite versions

An `/auto-do-todos` run on 2026-08-22 executed both from the hubbub session, because they were in
hubbub's queue and nothing in the flow questions placement. That produced four commits in four
other repos from a platform session. The run then FILED A NEW ONE THE SAME WAY (a todo whose whole
content was "edit four game repos' `CLAUDE.md`"), which is what Joe caught.

**And this is at least the second instance, not a one-off.** This backlog's own `PLAN.md` records
todo **479** as "re-filed here from zng-app's backlog 2026-08-22, it was global tooling sitting in a
project repo" - the same defect in the other direction (global work parked in a project) and caught
the same week, by hand, by whoever happened to notice.

Note two of the four game repos already have their own `.claude/todos/` backlogs
(`hubbub-game-music-guesser`, `hubbub-game-split-opinions`). So this is not a missing-destination
problem. The destination existed and was not used.

**Not a duplicate of [[404-nothing-stops-a-subagent-writing-into-the-todos-backlog]].** That one is
about WHO writes into a backlog (a subagent bypassing the orchestrator's report-back channel). This
one is about WHICH backlog, and applies equally to a main agent writing by hand. They do share a
likely mechanism, so decide them together rather than bolting on two hooks.

## Approach

Two halves, and the second is the one Joe actually asked for.

**1. Stop new mis-files.**

- Put the allocation rule in `skills/close/ai-todos-format.md` where every skill that writes a todo
  already reads, not only in global `CLAUDE.md`. `## What belongs in the backlog` is the section.
- Give it a decision procedure, since the rule alone is not operable: allocate by the files the
  todo's own Approach/Acceptance would change. Mixed todos SPLIT rather than pick a side (the
  2026-08-22 case split cleanly: the `/create-game` skill half is the platform's, the four
  `CLAUDE.md` files are the games').
- Weigh extending `hooks/todo-duplicate-guard.py`, or a sibling hook on the same matcher, to warn
  when a todo body's file paths point predominantly outside the repo being written to. Cheap
  signals available in the file itself: `../<other-repo>/` paths, and repo names that are
  directories beside the current root. Warn, never block - allocation needs judgment and a
  false positive that refuses a write is worse than a mis-file.

**2. Sweep and relocate what is already mis-filed.** This is the "they gotta be MOVED" half.

- Add a repo-allocation pass to `/cleanup-todos`, which already walks every todo and re-verifies
  premises: for each, name the repo its changes land in, and flag mismatches for relocation with
  the destination named. Relocating is a file move plus an id re-allocation in the destination
  backlog plus a `PLAN.md` line in each, so it needs the same care as filing.
- Decide whether relocation is automatic or dev-confirmed. Lean automatic for an unambiguous case
  (every path in the todo is under one other repo) and confirmed otherwise.

## Acceptance

- The allocation rule and its decision procedure are stated in `skills/close/ai-todos-format.md`,
  not only in `CLAUDE.md`.
- `/cleanup-todos` reports mis-allocated todos as a named category with their destination repo.
- Running that pass across Joe's active projects turns up the existing mis-files and relocates
  them, rather than only preventing new ones.

## Notes

- Already relocated by hand on 2026-08-22, as the worked example of what the sweep should do:
  hubbub's todo 65 was split into `hubbub/.claude/todos/65-create-game-skill-still-scaffolds-manifest-hand-edits.md`
  (platform half) and
  `hubbub-game-template/.claude/todos/01-claude-md-still-says-hand-edit-the-generated-manifest.md`
  (game half), and hubbub's todo 68 was re-scoped to stop reaching into the game repos.
- hubbub's closed todos 60 and 63 are left in its `done/` where they are. Rewriting completed
  history buys nothing; the point is the ones still open.
