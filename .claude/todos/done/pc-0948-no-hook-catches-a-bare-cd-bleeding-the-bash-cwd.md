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

**DECLINED 2026-09-10, do not build.** Measured against a real corpus instead of guessing: 695
session transcripts under `~/.claude-personal/projects` (every project, every session this machine
has run), 32766 Bash tool calls total.

- A bare leading `cd` (first word of the first chain segment) appears in 17362 of those calls,
  53 percent of every Bash command ever run. It is not an edge case to catch - it is the dominant
  idiom for scoping a series of commands to a directory (`cd X && cmd1 && cmd2`), used precisely
  because the Bash tool's cwd persists across a whole command string but not across separate tool
  calls, the same fact that makes the drift possible in the first place.
- The one-shot subshell form `(cd X && ...)`, the Approach's proposed escape hatch, is used only
  21 times in the same corpus - an 800:1 ratio against the bare form. Steering toward it as the
  sanctioned pattern would fight the idiom actually in use, not accommodate it.
- Of the 17204 leading-cd calls with an absolute target, comparing the target against each
  session's own top-level project directory (derived from the transcript's own project folder, not
  the drifting per-message `cwd`) put 1839 (10.7 percent) into a genuinely different project tree -
  the closest reachable proxy for "what this guard would flag." A random sample of 25 of those 1839
  was read in full: 25/25 were deliberate, correct navigation - reading this repo's own
  backlog/hooks/CI output from a sibling session, a cross-repo prefilter/CI check in a related repo,
  reading a Conductor daemon log, reading an already-neutralized harvested repo (see todo 417), or
  reopening the session's own project after the per-message `cwd` had already drifted elsewhere.
  Zero of 25 were the wrong-repo-write failure mode the 2026-09-02 incident actually caused.
- That incident (the only one of three recurrences with real damage) was caught by
  `hooks/git-workdir-guard.py` at the point of actual consequence (`git push`), not by anything that
  would need to inspect the `cd` itself. The other two recurrences (2026-09-05, four drifts) caused
  no damage and were all reads of declared additional working directories - which the hook payload
  has no field for. The plugin-dev `hook-development` skill documents the full PreToolUse payload as
  `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `tool_name`,
  `tool_input`, `tool_result` - no additional-directories list - so this todo's own Acceptance
  criterion ("a cd into a declared additional working directory is not blocked") has nothing to
  check against and cannot be built honestly today.

This is exactly the shape `PLAN.md`'s Hook doctrine already names and kills: a heuristic detector
with a high false-positive rate against the dominant real idiom (compare the killed command-chaining
detector's 55 percent false-positive rate on 30047 commands, `done/311`). Here the number is worse
in the direction that matters - the closest true-positive proxy found zero real wrong-repo-write
attempts in a random sample of its candidate set, while the candidate set itself is built from the
ordinary, necessary way this environment navigates between related repos and its own nested
subdirectories.

**Conclusion: the two consequence guards (`hooks/git-workdir-guard.py`,
`hooks/flutter-workdir-guard.py`) are the right layer. A `cd`-detecting guard would be noise on
roughly 11 percent of an idiom used in the majority of all commands, in exchange for catching a risk
already caught downstream. Not building it. This question is closed; do not re-open without a new
incident the consequence guards demonstrably missed.**
- CLOSED AS DECLINED 2026-09-10 via /loop-todos cycle 4, on measurement rather than judgement. The builder scanned all 695 session transcripts on this machine, 32766 Bash calls, and the numbers killed the idea: a leading cd is the first word of 53 percent of every Bash command ever run here, so it is the dominant directory-scoping idiom, not an edge case. Of the 17204 with an absolute target, 1839 (10.7 percent) resolved to a different project tree, which is the closest proxy for what this guard would flag; a random sample of 25 read in full came back 25 of 25 legitimate deliberate navigation, and none was the wrong-repo-write failure mode from the single real incident. The subshell escape hatch this todo Approach recommends allowing is used 21 times in the entire corpus against 17362 bare forms, an 800 to 1 ratio, so the recommended mitigation is not a pattern anyone actually uses. A blocker was also found: the PreToolUse payload carries no field for a session declared additional working directories, so this todo own Acceptance criterion about not blocking those has nothing to check against and could not be satisfied honestly today. That last fact blocks ANY future cwd-allowlist guard, not just this one, and is recorded because it was not documented anywhere. Verdict: the consequence guards, git-workdir-guard.py and flutter-workdir-guard.py, are the right layer. This matches the doctrine precedent exactly, the killed command-chaining detector that flagged 55 percent of 30047 real commands.
