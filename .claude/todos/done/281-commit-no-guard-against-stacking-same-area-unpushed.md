<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=c4c870b1 -->
# /commit has no guard against stacking a second unpushed commit on the same work

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` notice that an UNPUSHED commit already covers the same ticket/area before it creates
a second one, instead of relying on the model remembering the rule mid-session.

## Context

zng-app's `.claude/commit-style.md` states the rule plainly:

> **One ticket = one commit (when unpushed).** If you already committed work for ticket X and now
> have follow-up changes for the same ticket X that are still unpushed, do NOT create a second
> commit. Undo the previous commit (`git reset --soft HEAD~1`), restage everything together, and
> create a single fresh commit.

Violated twice in one session on 2026-08-11, both times through `/commit` itself, both times
unnoticed until Joe asked for a review:

- `0fe07a1` made the e2e workflow runnable.
- `779edbf` then added a TODO comment to the same `.github/workflows/e2e.yml`.
- `e0729a0` then fixed `e2e/fixtures.sql`, also part of the same e2e workflow work.

All three were the same unit of work and all three were unpushed. The correct action at commit 2
and 3 was `git reset --soft HEAD~1` and a single fresh commit. Fixing it afterwards cost a
`reset --soft` back four commits and a full re-commit, plus a diff against a checkpoint tag to
prove no content drift.

The rule is read (step 1 of `/commit` reads `.claude/commit-style.md`) but nothing acts on it. It
is purely advisory prose competing with the model's default "new change, new commit" instinct.

Related but distinct: `105-commit-skill-step1-enforcement-gap` is about step 1 not being READ at
all. This one is about the rule being read and still not applied.

## Approach

Add a step to `~/.claude/skills/commit/SKILL.md`, before step 8's pathspec commit:

1. Compute the unpushed set: `git log @{u}..HEAD --format='%h %s'` (skip silently if there is no
   upstream).
2. If any unpushed commit's touched paths overlap the pathspec about to be committed
   (`git show --name-only <sha>` intersected with the new pathspec), STOP and surface it:
   name the overlapping commit and ask whether this is follow-up work on the same unit (â†’ amend
   via `reset --soft`) or genuinely separate (â†’ new commit).
3. Path overlap is the cheap proxy; a ticket-number match in the message is a second signal worth
   checking when the project uses `<ticket>: <desc>` prefixes.

Prefer surfacing over auto-amending: silently rewriting a commit the dev may have deliberately
separated is worse than one question.

## Acceptance

- A second `/commit` touching a file already covered by an unpushed commit prompts instead of
  stacking silently.
- Committing an unrelated pathspec while unpushed commits exist does NOT prompt (no false
  positives on a normal multi-concern session).
- A repo with no upstream, or with everything already pushed, is unaffected.

## Notes

- Migrated on 2026-08-12 from the dead top-level `~/.claude/todos/` path (was #05 there). That location was superseded by the repo-relative backlog on 2026-08-11; nothing reads it, so these were invisible to the Conductor app.
- completed, commit 6660f6c
