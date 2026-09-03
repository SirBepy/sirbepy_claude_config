<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 98 (done) shipped hooks/flutter-workdir-guard.py for fvm/flutter/dart only; 504 is complete-todo.ps1's own repo resolution; 277 is sv.ps1's -Root default. None of them cover git, which is the one command here that publishes to a remote. -->
# Guard git against running in the wrong repo when the shell cwd drifted

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop a bare `git push` / `git commit` from silently targeting whichever repo the Bash cwd happens
to be in, the way `hooks/flutter-workdir-guard.py` already does for `fvm`/`flutter`/`dart`.

## Context

Happened on 2026-09-02 in a zng-app session. A memory file was read with
`cd /c/Users/tecno/.claude-personal/projects/<project>/memory && cat ...`, which leaves the Bash
cwd inside the `~/.claude` config repo (`.claude-personal` resolves to `C:/Users/tecno/.claude`).
The very next call was a bare `git push` intended for zng-app's `develop`. It pushed
`sirbepy_claude_config` `master` instead: `f707e2d..5910374`, two DOCS commits written by a
different session, published without a prompt, an error, or any output naming the wrong repo until
the push summary itself.

Nothing caught it:

- `hooks/flutter-workdir-guard.py` only inspects `fvm`/`flutter`/`dart` as the leading command
  (shipped under todo 98, now in `done/`).
- `/commit`'s own rule ("Never use `cd` before git commands. Use `git -C /absolute/path`") is
  procedure the model has to remember, with no enforcement.
- `git rev-list --count @{u}..HEAD` returned `0` straight after, which reads as "nothing to push"
  for the intended repo rather than as a signal the command ran somewhere else.

Undoing a wrong push needs a force-push, so this is one-way: the guard has to fire BEFORE the
command, which is what makes it a hook rather than a checklist line.

## Approach

1. Read `hooks/flutter-workdir-guard.py` and reuse its shape; todo
   `874-git-root-resolution-reimplemented-in-two-guards.md` covers the same repo-root helper, so
   check whether that consolidation lands first and build on it.
2. New `PreToolUse` hook on Bash (and PowerShell) that, for a command whose leading token is `git`:
   - resolves the git repo root of the tool call's cwd,
   - compares it against the session's primary project root (the harness cwd),
   - blocks with a plain-English message when they differ AND the command is a WRITE
     (`push`, `commit`, `reset`, `checkout`, `restore`, `update-ref`, `rebase`, `stash`), telling
     the caller to re-run with `git -C <intended-root>`.
3. Read-only git (`status`, `log`, `diff`, `show`, `rev-parse`, `ls-remote`) must NOT be blocked:
   cross-repo reads are routine and CLAUDE.md explicitly allows reading sibling repos.
4. Allow the deliberate case: a command that already carries an explicit `-C <path>` passes
   untouched, and so does one whose resolved root matches the harness cwd.
5. Add `hooks/test_git_workdir_guard.py` covering: wrong-root push blocked, wrong-root `git status`
   allowed, `git -C` push allowed, same-root push allowed. `python ci/run_all.py` picks it up.

## Acceptance

- [ ] A bare `git push` issued from a Bash cwd inside a different repo than the harness cwd is
      blocked, and the message names both roots.
- [ ] `git -C <other-repo> push` still runs, and read-only git in any repo still runs.
- [ ] `hooks/test_git_workdir_guard.py` passes under `python ci/run_all.py`.
