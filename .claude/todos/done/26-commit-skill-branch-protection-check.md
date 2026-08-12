<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=44f15e00 -->
# Add branch-protection check to the global /commit skill

**Type:** skill-improvement

## Goal

`/commit` should refuse (or warn + require confirmation) before committing when the current
branch is a protected trunk branch (`main`/`develop` in this repo's GIT_FLOW; generically
`main`/`master` elsewhere), the same way `/create-pr` already does in its precondition step
("Refuse if on `main`/`master`").

## Context

On 2026-07-27, an entire session's work (5 commits, ~107 files across `frontend2` standup +
follow-on cleanup) landed directly on `develop` because no feature branch was ever created before
the first `/commit` invocation. This directly violates this repo's GIT_FLOW.md rule: "No one —
human or AI — commits or pushes directly to `[trunk]`." It went unnoticed for the whole session
because `/commit` (`~/.claude/skills/commit/SKILL.md`) has no branch check anywhere in its
procedure — it just runs `git commit -m "..." -- <pathspec>` regardless of the checked-out branch.

It was only caught when running `/create-pr` afterward, which DOES check this
("Refuse if on `main`/`master` - PRs come off a feature branch"). By that point 5 commits already
existed on trunk. Recovery was clean only because nothing had been pushed yet
(`git branch feature/<topic> HEAD` + `git branch -f develop origin/develop` moved the commits off
trunk with no data loss) — a session that pushed before running `/create-pr` would have no such
safety net and would need a force-push or a revert to fix it.

See memory `feedback-check-branch-before-commit` for the full incident writeup.

## Approach

Add a precondition step to `/commit`'s procedure (before step 2's `git status`), mirroring
`/create-pr`'s existing check:

- Run `git rev-parse --abbrev-ref HEAD`.
- If it matches a known-protected branch name (`main`, `master`, `develop` — the skill should
  probably check for a project override the way `.claude/commit-style.md` overrides commit-message
  rules, since not every repo's trunk is named the same thing) AND the repo has a remote (i.e.
  this isn't a solo local-only project with no branch discipline), stop and warn: name the branch,
  name the rule it would violate, and ask (AskUserQuestion) whether to create a feature branch
  first, commit anyway (explicit override), or abort.
- Repos with no branching convention at all (most of Joe's personal single-dev projects) should
  NOT be gated by this — the check needs to be conditional on the repo actually having a
  GIT_FLOW-style protected-trunk convention, not applied universally. Look for a `GIT_FLOW.md` (or
  equivalent) at the repo root, or a documented branch-protection rule in the root `CLAUDE.md`, as
  the signal that this repo cares.

## Acceptance

- On a repo with a `GIT_FLOW.md`/documented trunk-protection rule, running `/commit` while checked
  out on `main`/`master`/`develop` stops and asks before committing, instead of silently committing.
- On a repo with no such convention, `/commit`'s behavior is unchanged (no new prompt, no false
  positives on Joe's personal projects).
- `/create-pr`'s existing check is unaffected (this is additive, not a replacement).

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 150; renumbered to 26 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: Added step 1a to SKILL.md's `/commit` flow, before `git status`. Gates on protected-branch name AND remote AND a documented GIT_FLOW.md/CLAUDE.md convention at repo root; explicitly does not fire on `~/.claude` (master, no GIT_FLOW.md).
