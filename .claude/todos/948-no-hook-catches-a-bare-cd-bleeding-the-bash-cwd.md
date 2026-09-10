<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=5, reconfirm-count=1, content-hash=aaa4e7ac -->
<!-- duplicate-checked: grepped the backlog for "bleeds", "session cwd" and cd-shaped filenames - nothing. hooks/git-workdir-guard.py and hooks/flutter-workdir-guard.py both exist but guard the CONSEQUENCES of drift, not the drift itself. -->
# Two hooks guard the consequences of a drifting Bash cwd, none guards the drift

**Type:** skill-improvement
**Origin:** ai

## Goal

Catch a bare `cd` that silently moves the Bash tool's cwd out of the session's project, at the
moment it happens, instead of only catching the dangerous things that follow.

## Context

The Bash tool's working directory persists across calls, so a single `cd` in one command changes
where every later command runs. Two hooks already exist because of what that has caused:

- `hooks/git-workdir-guard.py` - blocks git WRITE ops when the shell cwd and
  `$CLAUDE_PROJECT_DIR` resolve to different repo roots. Its own docstring cites the 2026-09-02
  incident: a zng-app session `cd`'d into `~/.claude` to read a memory file, the cwd stayed there,
  and a bare `git push` published `sirbepy_claude_config` master instead of zng-app's develop.
- `hooks/flutter-workdir-guard.py` - the same shape for fvm/flutter/dart.

Neither fires on the `cd` itself, so the drift is invisible until something downstream breaks. The
project memory `feedback_shell_discipline` in `server_supervisor` records a third symptom class
("could not resolve index.html") that no hook covers at all.

**It recurred on 2026-09-05**, in a `server_supervisor` `/mega-todos` session, on the FIRST tool call
of the run: `cd /c/Users/tecno/.claude-personal/projects/.../memory 2>/dev/null; cat ...`. The
session cwd silently became the memory folder, and the harness printed an environment-update notice
only after the fact. It was caught and restored immediately with no damage, but note the conditions:
the project carried an explicit memory saying never to do this, AND the invoking handoff prompt
carried a verbatim correction from Joe saying the previous session had done it three times despite
that memory. A rule stated twice in-context still did not hold, which is the same shape as todo 290.

## Approach

- A `PreToolUse` hook on the Bash tool that inspects the command string for a leading `cd`
  (or a `cd` as the first segment of a `;`/`&&` chain) whose target resolves outside
  `$CLAUDE_PROJECT_DIR`, and blocks it with a message naming the alternatives that do not drift:
  `git -C <path>`, absolute paths, `npm --prefix <path>`, `cargo --manifest-path <path>`,
  `python` run from an absolute script path, and a parenthesised subshell `(cd X && cmd)` which
  contains the change to a child process.
- Decide deliberately whether the subshell form is allowed through. It genuinely does not bleed, and
  banning it removes the one clean escape hatch for a tool that has no `-C` equivalent (this session
  used `(cd ~/.claude && python ci/run_all.py)` for exactly that reason and the cwd was verifiably
  unchanged afterwards). Recommendation: allow it explicitly, and say so in the block message so the
  hook teaches the fix rather than just refusing.
- Check `hooks/_hooklib.py` for how the other two guards read `payload["cwd"]` versus
  `$CLAUDE_PROJECT_DIR` and reuse that, rather than re-deriving it.
- A hook is the right shape here specifically BECAUSE prose did not work: this is not a
  "be more careful" fix, it is the missing mechanical catch the other two hooks already imply.

## Acceptance

- A bare `cd` to a path outside the project is blocked, with a message naming `git -C`, `--prefix`,
  `--manifest-path` and the subshell form.
- A `cd` to a path INSIDE the project is not blocked, and neither is `(cd X && cmd)` if that is the
  decision taken above.
- A `hooks/test_<name>.py` suite covers both the blocked and the allowed cases, and
  `python ci/run_all.py` picks it up (it auto-discovers `hooks/test_*.py`).
- **A `cd` into one of the session's declared additional working directories is not blocked.**
  See the 2026-09-05 head_soccer datapoint below; without this the hook is a false-positive machine.

## The "outside `$CLAUDE_PROJECT_DIR`" test is too blunt - 2026-09-05, head_soccer_v_fable_oneshot

Recurred a third time, four separate drifts in one session (`C:\Users\tecno` ->
`...\claude_usage_in_taskbar` -> `...\.claude\.claude\todos` -> `...\.claude`), every one from a
`cd X && ...` chain, every one silent until the harness printed an environment-update after the fact.
No damage: the session made no commits, and later calls used absolute paths.

**The design-relevant part, which is new:** every one of those targets was *legitimate*. They were
reads of Conductor's source and of the `~/.claude` backlog, and both are declared **additional
working directories** for that session. The Approach above blocks any `cd` resolving outside
`$CLAUDE_PROJECT_DIR`, which would have blocked all four correct reads while still not being what
kept the session safe.

So the check needs the session's additional working directories in its allowlist, not just
`$CLAUDE_PROJECT_DIR`. Worth confirming how `hooks/_hooklib.py` can see them (the hook payload's
`cwd` alone will not reveal them) before building the guard, otherwise the first real test drive
blocks ordinary cross-repo reads and the hook gets disabled rather than fixed.

Note this also weakens the "block it" framing generally: in all three recorded recurrences the drift
was harmless in itself, and the 2026-09-02 zng-app incident was caused by the *downstream* bare
`git push`, which `hooks/git-workdir-guard.py` already catches. Consider whether a warn-and-continue
hook (the `todo-duplicate-guard.py` shape, per `PLAN.md`'s note that this repo has already killed
three guess-based hard-blocking hooks in one day) is the better trade here.

## Notes

Filed 2026-09-05 by `/respawn`'s Phase 1 retrospective, from a violation the same session committed.
Related: `hooks/git-workdir-guard.py`, `hooks/flutter-workdir-guard.py`, and the `server_supervisor`
memory `feedback_shell_discipline`.
