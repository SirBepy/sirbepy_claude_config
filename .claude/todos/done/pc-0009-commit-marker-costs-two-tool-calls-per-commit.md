<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=13c054d3 -->
# Every commit costs two tool calls because the guard marker cannot be written in the same call

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` cost one tool call per commit instead of two, without weakening what
`commit-guard.py` protects.

## Context

`~/.claude/skills/commit/SKILL.md` step 13 requires writing a uniquely-suffixed marker file to
`~/.claude/hooks/` immediately before every `git commit`, because a global `PreToolUse` hook blocks
raw `git commit` otherwise.

The marker cannot be written in the same tool call as the commit. The hook fires `PreToolUse`, so it
evaluates the whole command string BEFORE any of it runs - the marker does not exist yet at the
moment the hook checks. Confirmed 2026-08-07: `Set-Content -Path ...marker...; git commit -m "..."`
in one PowerShell call was rejected outright, and neither statement executed.

So every single commit is: one call to write the marker, one call to commit. A `/auto-do-todos` run
on 2026-08-07 made 19 commits in `windows_taskbar_widgets` plus 4 in `~/.claude`, which is 23 wasted
tool calls in one session purely on marker plumbing.

Secondary consequence, already recorded in `07-no-chaining-rule-is-unworkable-in-powershell.md`: the
same hook eats a preceding `git add` when someone tries to chain them, with no indication in the
error that anything besides the commit was skipped.

## Approach

Options, pick one:

1. **Let the hook accept a marker written earlier in the same session** rather than within the last
   2 minutes, keyed to the session id instead of freshness. Removes the per-commit write entirely;
   one marker per session. Weakens the guard the least if the marker is session-scoped, since a
   stray `git commit` from a session that never ran `/commit` still gets blocked.
2. **Have the hook recognise the `/commit` skill being active** (if the harness exposes that to a
   `PreToolUse` hook) and drop the marker mechanism altogether.
3. **Ship a `commit.ps1` helper** that writes the marker and commits in one process, so the skill
   calls one script instead of two commands. Simplest, but keeps the marker concept.

Whichever is chosen, `commit-guard.py`'s rejection message should also state plainly that NO part of
the call executed, per the finding in todo 07.

## Acceptance

- A normal `/commit` costs one tool call, not two.
- A raw `git commit` from a session that never invoked `/commit` is still blocked.
- Two concurrent sessions committing at the same time cannot consume each other's authorisation.
- The rejection message says nothing in the call ran.

## Notes

Found by `/close` on 2026-08-07 after a session that made 23 commits. Filed here rather than in the
project backlog per the rule added to global CLAUDE.md the same day: todos about the global
`~/.claude` tree belong in this backlog, never a project's.

- Re-verified 2026-08-08: premise holds, but the todo points at "step 13" of `skills/commit/SKILL.md`.
  That instruction is no longer numbered: it now lives in an unnumbered callout above step 1. Same
  mechanism, stale pointer. `FRESHNESS_SECONDS = 120` in `hooks/commit-guard.py` and the per-commit
  marker requirement are both unchanged.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: change `hooks/commit-guard.py` from a 120-second marker-freshness window to a
  session-scoped marker keyed on `payload["session_id"]`. Hook payloads already expose that field,
  confirmed by `schedulewakeup-guard.py`'s use of `transcript_path` from the same payload shape.
  Then drop the "redo the marker before each commit" instruction from `commit/SKILL.md`, so the
  marker is written once per session. This was produced by a strict second-pass re-triage that
  specifically asked whether a defensible answer exists without the dev; it concluded yes. Not
  executed only because the session ended.

- **Reconfirmed 2026-08-08.** A single `/auto-do-todos` run wrote 13 separate commit markers, so 26
  tool calls where 13 would do. Sharper point worth recording: the marker is written with
  `Set-Content`, which global CLAUDE.md's Shell Commands section bans outright as a file-content
  write. So `/commit`'s own mandated mechanism currently violates a global rule, and this todo's fix
  removes the need for it.

- **Conflicts with 265, resolved by ordering (2026-08-12).** Todo 265 hardens the CURRENT two-call
  design by documenting that the marker must be its own tool call; this todo removes the per-commit
  write entirely. Do this one FIRST - a session-scoped marker leaves at most one chainable write per
  session, which shrinks 265 to a footnote instead of a rule. Executing 265 first means rewriting it
  afterwards. Four other copies of the 265 ask were archived as duplicates on 2026-08-12.
- completed, commit 0796403
