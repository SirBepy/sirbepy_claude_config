<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=1bd991c1 -->
# `/commit` skill's marker-gate flow doesn't mention `git cherry-pick`

**Type:** skill-improvement

**Origin:** ai

## Goal

`~/.claude/skills/commit/SKILL.md` and `edge-cases.md` explicitly cover `git merge` as a commit
path that needs the same commit-marker treatment as `git commit` ("never a raw `git merge` + push
that lands an unreviewed merge commit, and never `git commit` directly"). `git cherry-pick` creates
a commit the exact same way (bypassing the literal `git commit` subcommand the PreToolUse hook
watches for) but isn't named anywhere in either file, so it's easy to run one thinking it's a
read-only/safe operation and only realize afterward it needed the marker + review treatment too.

## Context

Hit 2026-08-09/10 in `claude_usage_in_taskbar`: ran `git cherry-pick 08a115bf` directly onto
`master` to pull in an isolated CI fix from a stale branch, without writing a commit-marker first
and without going through `/commit`. Caught it a few steps later, invoked `/commit` for the
following work, but the cherry-pick itself was a raw, ungated commit - exactly the failure mode
the global "NEVER commit directly" rule exists to prevent.

## Approach

Add `git cherry-pick` to the same sentence in `skills/commit/edge-cases.md`'s "Merge commits"
section (or a new short section right next to it) that already says "never a raw `git merge` +
push... and never `git commit` directly" - cherry-pick belongs in that list. Note that unlike a
merge, a cherry-pick's message usually shouldn't get a `MERGE:` prefix rewrite (it's carrying an
existing, already-reviewed commit's message forward) - the marker-write step is what's missing,
not a message-format concern.

## Acceptance

- `edge-cases.md` (or `SKILL.md`) names `git cherry-pick` alongside `git merge` as a commit-style
  operation requiring the fresh commit-marker before it runs, not just literal `git commit`.

## Verify

- [ ] Read the updated file back and confirm cherry-pick is mentioned in the same breath as merge.

## Notes

- Surfaced by `/close` in `claude_usage_in_taskbar` (project session) 2026-08-10, but this is a
  global-tooling fix per that project's own "app-specific AI guidance location" rule - filed here,
  not in that project's backlog.
- completed, commit 0796403
