<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /close's Phase 2 "unpushed" scope is silently empty when /commit already pushed first

**Type:** skill-improvement

## Goal

`~/.claude/skills/close/SKILL.md`'s Phase 2 scope rule ("if commits were made this session, pass
`unpushed`") should account for the common case where the session's own `/commit push*` already
pushed everything before `/close` runs - today that makes the "unpushed" scope resolve to nothing,
silently skipping the code-health review it was supposed to run.

## Context

2026-07-29, `claude_usage_in_taskbar`: session ran `/commit pushnbump` (committed + pushed two
commits), then `/close` afterward. Phase 2 correctly decided "commits were made this session" and
passed `unpushed` to `/code-check`, which resolves scope via
`git log @{u}..HEAD --name-only --diff-filter=ACM --format=`. Since the push already happened,
`@{u}` (upstream) now equals `HEAD`, so that range is empty - `code-check` printed "No code files
in scope" and the review silently did nothing, even though ~240 lines of real feature code had
just landed in the two commits from this exact session.

This isn't specific to this session - it'll happen every time `/close` is chained after (or run
in a session that already ran) a push-flavored `/commit`, which per this project's own
`feedback_auto_commit_full_auto_projects` / `feedback_deploy_via_pushnbump_always` memories is a
common, even default, pattern here. The "unpushed" scope silently degrading to empty in exactly
that common case defeats Phase 2's purpose most of the time it'd otherwise fire.

## Approach

`~/.claude/skills/close/SKILL.md`'s Phase 2 scope-resolution needs a fallback: when `unpushed`
scope resolves empty AND commits were made this session, fall back to reviewing those specific
commits directly - e.g. `git diff <session-start-sha>..HEAD --name-only --diff-filter=ACM` if the
session's starting HEAD is knowable/trackable, or at minimum the session's own commit shas (which
Claude does know, having just made them) passed as an explicit range to `/code-check` instead of
the string `"unpushed"`.

Simplest concrete fix: instead of passing the literal string `unpushed` to `/code-check`, have
`/close` compute the actual commit range itself (the shas of commits made this session, which it
already knows from having just run `/commit`) and pass that range directly - `/code-check` already
supports "looks like a hash or range" as a scope argument, so this reuses existing support rather
than adding new logic to `/code-check`.

## Acceptance

- A session that runs `/commit push*` (any push variant) followed by `/close` in the same session
  gets a real Phase 2 review of the commits it just pushed, not a silent "No code files in scope."
- A session that runs bare `/commit` (no push) still behaves as today (`unpushed` scope correctly
  finds the local-only commits).

## Notes

- Duplicate of 68 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
