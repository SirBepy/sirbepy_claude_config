<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Add a pre-stage git status sanity check to /commit for concurrent-session safety

**Type:** skill-improvement

## Goal

Prevent a repeat of an accidental commingled commit: `/commit` should verify it's about to stage
exactly the file(s) it was asked to commit, not whatever else happens to be dirty/staged at that
moment, before running `git add`.

## Context

`~/.claude/skills/commit/SKILL.md` step 8 says "Stage all relevant files by name" but has no
instruction to verify the staging area's actual contents match intent before committing.

Hit live on 2026-07-20/21 during a rate-it-and-commit sweep across 18 individually-committed
files in this same repo (`.claude` dotfiles). Another Claude Code session/process was
concurrently editing and committing to the same working tree. One `/commit skills/disk-doctor/windows.md`
call landed a commit (`38227b2`) that unexpectedly also included unrelated,
not-yet-reviewed changes to `skills/supervised-run/SKILL.md` - the other session had apparently
staged that file at the exact moment this session's `git add <path>` + `git commit` ran. No data
was lost (the swept-in content was legitimate, just landed in a differently-labeled commit), but
it broke the "one purpose per commit" rule and could have been worse (e.g. committing a WIP file
mid-edit).

After discovering this, the agent adopted an ad hoc habit for the rest of the session: run
`git status --porcelain` immediately before staging, confirm only the intended file(s) are dirty,
and after `git add`, run `git diff --cached --stat` to confirm only the intended file(s) are
actually staged before committing. This worked but was improvised, not spec - a fresh session
executing `/commit` from the file alone wouldn't know to do this.

## Approach

Add a step to `commit/SKILL.md` between "Stage files by name" (step 8) and "Commit" (step 9):

- After `git add <path(s)>`, run `git diff --cached --stat` (or `git status --porcelain` with
  staged-column check) and confirm the staged file list matches exactly what was intended to
  stage. If anything unexpected is staged (a file the dev didn't ask to commit), stop before
  committing, tell the dev what showed up unexpectedly, and ask whether to unstage it
  (`git reset <path>`) or fold it into this commit deliberately - never commit silently past a
  mismatch.
- This is cheap (one extra read-only git call) and directly prevents the exact failure mode hit
  above. Worth doing unconditionally, not just when concurrency is suspected, since there's no
  reliable way to detect "another session might be active" ahead of time.

Rejected alternative: only running the check when multiple Claude sessions are known to be active
- there's no reliable signal for that from inside a single session, so the check should just
  always run; the cost is negligible.

## Acceptance

- `/commit`'s documented flow includes a staged-content verification step before every commit.
- The verification catches a staging mismatch (extra or missing files) and surfaces it to the
  dev instead of committing past it silently.

## Notes

This is a process-hygiene concern specific to environments where the same working tree may have
more than one active Claude Code session/process (this dotfiles repo, and potentially others the
dev works in with multiple terminals open). Low cost, real payoff given it already happened once.
- Dropped via /cleanup-todos 2026-08-11: already done - commit e1f7ca62 made shared-index staging structurally impossible, a stronger fix. Confirmed by dev 2026-08-11.
