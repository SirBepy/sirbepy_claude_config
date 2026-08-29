<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=990b0959 -->
<!-- duplicate-checked -->
# /create-pr's base default is wrong for repos that document trunk policy outside GIT_FLOW.md

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/create-pr` pick the right base branch in a repo whose trunk convention is
documented somewhere other than a root `GIT_FLOW.md`.

## Context

`skills/create-pr/SKILL.md` step 1 says: *"Base = first positional arg, else
`main`."* Its only escape hatch is the GIT_FLOW gate, which fires only *"if
`GIT_FLOW.md` exists at repo root"*.

On revaire-mobile (2026-08-29) neither condition helped. There is no root
`GIT_FLOW.md`; the trunk policy lives in `docs/BRANCHING_STRATEGY.md`, which
states plainly that `develop` is where feature and bug-fix branches integrate and
that `main` is production. Following the skill literally would have opened a
feature PR against `main`, i.e. a production PR.

It was caught only because the orchestrator happened to read
`docs/BRANCHING_STRATEGY.md` and the harness's own git status line said *"Main
branch (you will usually use this for PRs): develop"*. That is luck, not
enforcement. A `main`-based PR in a develop-flow repo is a loud, embarrassing
mistake that also drags the wrong reviewers in.

## Approach

Widen the gate in `skills/create-pr/SKILL.md` step 1. Options, cheapest first:

1. **Detect the real default from the remote** rather than hardcoding `main`:
   `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`. One call,
   no file reading, and correct for most repos. (Verify this actually returns
   `develop` for Revaire-Inc/revaire-mobile before relying on it; the GitHub
   default branch and the team's integration branch are not always the same.)
2. **Broaden the doc gate** beyond a root `GIT_FLOW.md` to also check
   `docs/BRANCHING_STRATEGY.md`, `CONTRIBUTING.md`, and a `## Git`/`## Branching`
   section in root `CLAUDE.md`.
3. **Fail loud instead of defaulting.** If no arg was passed and the repo has more
   than one long-lived branch, ask via `AskUserQuestion` rather than silently
   assuming `main`.

Prefer 1 plus 3: cheap detection, and an explicit ask when detection is
ambiguous. Do NOT just add revaire-mobile as a special case; the gap is generic.
