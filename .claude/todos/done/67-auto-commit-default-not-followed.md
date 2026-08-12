<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Reinforce the auto-commit-is-default rule - a session reported "done" repeatedly without ever committing

**Type:** skill-improvement
**Origin:** ai

## Goal

Find why the auto-commit default (`~/.claude/snippets/auto-commit.md`, referenced from global
`CLAUDE.md`'s Git Commits section) didn't fire, and close the gap so a session can't report a
feature "done" multiple times while the working tree is still fully uncommitted.

## Context

Session in `windows_taskbar_widgets` (2026-08-09, redesigning the Claude usage widget): the
session called `report_turn_status` with `status: "done"` and told Joe "All done" / "Yep, all done"
**twice**, across a real multi-round feature (typecheck/tests/build all green, dev app verified
live) - and never once ran `/commit`. Joe had to ask directly: "wait, i dont see any commits, did
you already commit and do /commit pushnbump or?" Only then did the session invoke `/commit`.

Global `CLAUDE.md` already states plainly: "Auto-commit is a universal default, not opt-in... If
you catch yourself about to ask 'should I commit this?', that snippet already answered it - just
run `/commit`." The rule exists and is unambiguous; it simply wasn't consulted at any of the
"done" points in that session. This isn't a missing rule, it's an enforcement gap - the rule has
no trigger tied to the specific moment (reporting/declaring a task done) where it needs to fire.

## Approach

Consider one or more of:
- A `PreToolUse`/turn-status hook that checks `git status --short` when `report_turn_status` is
  called with `status: "done"` in a git repo, and nudges (or blocks) if the working tree has
  uncommitted changes matching files touched this session.
- Strengthening `auto-commit.md`'s own wording to explicitly tie "done" declarations to committing
  first, not just "after a task".
- A `send_message`-time check with the same logic, since that's the user-visible "done" signal.

Read `~/.claude/snippets/auto-commit.md` in full first - the fix should close whatever gap let a
"done" status/message go out uncommitted, not just restate the existing rule text.

## Acceptance

- A session that finishes a feature and reports/announces "done" with uncommitted changes either
  gets blocked, auto-corrected, or visibly nudged before the turn ends.
- No regression to sessions that are legitimately not ready to commit yet (e.g. mid-task, or the
  dev explicitly deferred committing).

## Notes

Origin is `ai`: Claude noticed this via Joe's correction, but Joe didn't ask for a skill fix in
these words - he asked a direct question ("did you already commit") and Claude then ran `/commit`
reactively. This todo is Claude's own follow-up observation from that exchange.
- Duplicate of 02 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
