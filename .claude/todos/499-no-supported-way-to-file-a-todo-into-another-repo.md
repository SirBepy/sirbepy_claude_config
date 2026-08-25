<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Nothing supports filing a todo into a DIFFERENT repo, so the repo-ownership rule is hand-executed every time

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the "a todo belongs in the backlog of the repo it changes" rule a supported path, instead of a
four-step manual sequence that a session has to remember in full.

## Context

Surfaced 2026-08-22 during an `/auto-do-todos` run in `hubbub`. Joe's correction that day was
blunt: "if theres todos for a project they gotta be moved to the right project!!! cuz this is rly
annoying." Complying meant writing **six** todos into four sibling repos in one session
(`hubbub-game-{tap-race,music-guesser,split-opinions,template}`).

`create-todo/SKILL.md:16` is the whole of its cross-repo support: "If there's no project (no repo
root for `.claude/todos/` to live under), say so and stop." There is no target-repo parameter. So
each of the six was done by hand:

1. `reserve-todo-id.ps1 -RepoRoot <other repo>` (this one DOES take a root - the only piece that
   does).
2. `Write` the file at the right zero-padded path.
3. `rm` the `<id>-.reserved` marker.
4. Self-heal `<other repo>/.git/info/exclude` with the three git-policy lines.

Step 4 was nearly missed: `hubbub-game-tap-race` had no `.claude/todos/` at all and therefore none
of the exclude lines, while two others were missing only the `*-.reserved` line. A session that
forgets step 4 leaves todo files git-visible in someone else's repo, which is exactly the pollution
the git policy exists to prevent.

This is the ergonomics half of [[481-nothing-checks-a-todo-is-in-the-repo-it-changes]]. That one
asks for enforcement of correct placement; this one is why correct placement is laborious enough
that a session drifts from it under load. Fixing 481 without this makes the rule harder to follow,
not easier.

## Approach

1. Give `/create-todo` an explicit target-repo parameter, and make it own all four steps above
   including the exclude self-heal. `reserve-todo-id.ps1`'s existing `-RepoRoot` is the precedent
   for the parameter shape.
2. Decide and document what happens when the target repo has no `.claude/todos/` yet - creating it
   in another repo is a real side effect and should be stated, not silent.
3. Point `close/ai-todos-format.md`'s "a todo belongs in the repo it changes" text at the supported
   path once it exists, so the rule and the mechanism are named together.
4. Check whether `/code-check` and `/close` Phase 3 need the same capability - both can surface a
   finding about a file outside the current repo.

## Acceptance

- One invocation files a correctly-formatted, correctly-numbered todo into a named other repo.
- That repo's `.git/info/exclude` carries all three git-policy lines afterwards, whether or not it
  had a `.claude/todos/` before.
- No `*-.reserved` marker is left behind.
- Running it twice in a row into the same repo produces two distinct ids, no collision.

## Notes

- Read [[481-nothing-checks-a-todo-is-in-the-repo-it-changes]] before starting; these two want to
  be designed together even if they land separately.
- Do NOT extend this into cross-repo todo EXECUTION. Joe's correction was specifically that work
  belonging to another repo should not be done from this session; only the filing needs a path.
