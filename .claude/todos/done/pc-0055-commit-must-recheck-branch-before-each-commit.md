<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=9, reconfirm-count=2, content-hash=4d19e3db -->
# /commit must re-check the current branch before EVERY commit, not once per run

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` fail loudly when the branch changed under it, instead of silently committing to
whatever branch HEAD now points at.

## Context

Real incident, 2026-08-08, `claude_usage_in_taskbar`. Across one session I made 16 commits. The
first 15 printed `[master ...]`. Between commit 15 and 16 a CONCURRENT session moved the shared
checkout's HEAD onto a feature branch (`563-iroh-logging`). Commit 16 printed
`[563-iroh-logging ...]`: same command, no error, no warning. It was only caught by reading the
branch name in git's own output afterwards.

Consequences: a 3-line, dev-approved build-config fix ended up buried in an unrelated feature branch
and is now at risk of being discarded with it. Recovery was NOT self-serve either, since resetting
or switching branches in a shared checkout can destroy another session's uncommitted work, so it
turned into a multi-message coordination problem across three sessions.

Why the skill does not currently catch this:

- Step 1a DOES read the branch (`git rev-parse --abbrev-ref HEAD`), but only as a protected-trunk
  gate, and only once at the start of a `/commit` run.
- Step 8's pathspec rule is explicitly about the INDEX. It guarantees which PATHS get committed and
  is immune to another session's staged files, which is a real and separate win. But it says nothing
  about which BRANCH receives the commit. The two hazards look similar and the skill only addresses
  one of them.
- A multi-commit sweep issues many `git commit` calls from a single Step 1a check, so the window
  between check and commit can be many minutes long.

Related project-side memory: `project_concurrent_autopilot_on_master` (this repo has multiple
concurrent sessions sharing one working tree by design).

## Approach

In `~/.claude-personal/skills/commit/SKILL.md`:

1. At Step 1a, after resolving the branch, record it as the run's EXPECTED branch.
2. Add to Step 8, as a precondition in the same style as the existing comment-noise precondition:
   run `git rev-parse --abbrev-ref HEAD` immediately before EVERY `git commit`. If it differs from
   the expected branch, STOP, do not commit, and surface it to the dev with both branch names.
3. Treat a literal `HEAD` result (detached) as a hard stop too. That also happened in the same repo
   the same day: a session committed onto a detached HEAD and the commit was left on no branch,
   reachable only via reflog and gc-eligible.
4. Recommend verifying after a multi-commit sweep with
   `git merge-base --is-ancestor <sha> <expected-branch>`.

Keep it cheap: one `rev-parse` per commit, no network, no extra round trip to the dev on the happy
path.

## Acceptance

- SKILL.md Step 8 names the pre-commit branch check as a precondition, phrased so it cannot be
  skimmed past (mirroring how the comment-noise precondition is worded).
- Detached HEAD is called out explicitly as a stop condition.
- A dry read of the skill by a cold session makes clear that pathspec commits protect the index, NOT
  the branch, so the two are not confused again.

## Notes

- Re-verified 2026-08-08: premise still holds.
- completed, commit 0796403
