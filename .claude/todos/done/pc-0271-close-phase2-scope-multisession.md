<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=065f72f2 -->
# /close Phase 2 picks the wrong review scope when sessions share a branch

**Type:** skill-improvement

## Goal

Make `/close`'s code-health review scope to what THIS session changed, rather than to everything unpushed, so it stays correct when several Claude sessions commit to the same branch.

## Context

Session 2026-08-01, claude_usage_in_taskbar. `/close` Phase 2 says: "if commits were made this session, pass `unpushed`; otherwise pass `uncommitted`."

That heuristic assumes one session per branch. This repo routinely runs several concurrent Conductor sessions plus at least one Claude Code instance outside Conductor, all committing to `master`, and `master` had not been pushed in a long time. At close time `git log origin/master..HEAD` was 36 commits, of which 6 were this session's:

- fe17399b, fdb49940, 5336a4b1, 32834810, deb2f376, 64d376d4

The other 30 belonged to other sessions (sidebar Ctrl+N fix, phone lightbox/gallery fixes, mobile auto-accept race, a 17-commit refactor batch, an out-of-channel usage-snapshot feature, and more).

Passing `unpushed` would have sent `/code-check` over all 36, producing findings against four other sessions' work and filing todos in their name. Phase 2 was therefore SKIPPED deliberately this session, with the reason stated to the dev, rather than followed literally.

This is a real gap, not a one-off: the same thing recurs on any long-lived unpushed branch or any multi-session repo.

**The same binary rule also fails in the opposite direction (merged from todo 68, 2026-08-09,
`windows_taskbar_widgets`).** `/commit pushnbump` was run standalone, committing and pushing
cleanly. A later `/close` in the same session saw "commits were made this session" and passed
`unpushed`, but `git log @{u}..HEAD` was already empty, so `/code-check` got zero files and never
reviewed the session's own ~150 new lines (`src/widgets/conductor.ts` and friends). So the rule
resolves TOO WIDE on a shared branch and TOTALLY EMPTY after an in-session push - one root cause,
two symptoms, one fix.

## Approach

1. In `~/.claude/skills/close/SKILL.md` Phase 2, replace the binary scope rule with one that identifies THIS session's commits. Options, cheapest first:
   - Record commit shas as `/commit` makes them during the session, then pass that explicit list. Most accurate, needs `/commit` to leave a breadcrumb.
   - Derive from committer timestamp since session start (`~/.claude/sessions/*.json` has `startedAt`). Cheap, but wrong when concurrent sessions commit in the same window - which is exactly the failing case here.
   - Union of files touched by this session's commits, passed as a pathspec. Loses commit boundaries but is safe.
2. Add an explicit escape hatch: if the session cannot determine its own commits, SKIP Phase 2 and say so, rather than reviewing everything. Silence here is worse than skipping, because findings filed against another session's code read as this session's verdict.
3. Check whether `/code-check` itself accepts a sha list or pathspec; if not, that is the enabling change.

## Acceptance

- On a branch with commits from multiple sessions, `/close` reviews only the invoking session's commits.
- When scope cannot be determined, `/close` prints why it skipped rather than silently over-reviewing.
- A single-session repo behaves exactly as it does today.
- Regression case from todo 68: run `/commit pushnbump` standalone, then `/close` with no chain -
  Phase 2 still reviews that session's diff instead of resolving to an empty scope.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #475) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Related coordination context: this repo has a `list_peers` / `post_message` channel that only sees Conductor-hosted sessions. At least one Claude Code instance runs outside it and is invisible to that channel, so "who committed what" cannot be answered from peers alone.
- completed, commit 9d14d73
