<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 1065 (flutter-bump client gate), 1070 (push-read-gate session marker), 222/368/465 (commit/autopilot push paths) are other surfaces; none covers a delete-only push -->
# push-gate blocks a remote branch deletion that pushes no commits

**Type:** skill-improvement
**Origin:** ai

## Goal

`hooks/push-gate.py` lets a push through without a `mark` when it only deletes remote refs
(`git push <remote> --delete <branch>`, `git push <remote> :<branch>`). A delete uploads no commits,
so the /code-check and /e2e gate has nothing to check.

## Context

2026-10-15, revaire-mobile session (REV-7300/7304 handoff): after squash-merging PR #1150, Claude
ran `git push "https://x-access-token:...@github.com/Revaire-Inc/revaire-mobile.git" --delete
rev-7300-member-app-keeps-an-abandoned-traveler-edit-after-back` from local `develop` (HEAD
f356c16, already on the remote). The hook denied it: "HEAD f356c16 of revaire-mobile has not been
cleared for push. Follow /commit's Push pipeline...". The hook asks for /code-check over `@{u}..HEAD`
and /e2e, which do not apply to a ref deletion. The recovery was to ask Joe through a question card,
then run `push-gate.py mark ... --reason "branch delete only..."`: one question card, and a
"pushable" mark on a HEAD that was never actually checked.

Cause, with a receipt: `_git_push_dash_c` (`hooks/push-gate.py:88-109`) returns `is_push=True` for
any `git ... push` and never looks at the push arguments. `main()` (from line 183) then gates on
`head_sha` / `is_pushable` with no regard for what the push sends.

Every remote branch cleanup after a squash merge hits this (`linear-ticket` §5 step 5 in Revaire
repos, and `isolated-build` land), because squash-merged branches always survive on the remote.

## Approach

1. In the push detection, gather the push's own arguments (the tokens after `push`). If the push
   only deletes, meaning every refspec has the `:<dst>` form or the args include
   `--delete`/`-d`, and it has no `--all`/`--mirror`/`--tags` and no non-delete refspec, allow it
   without a mark.
2. Anything mixed (a delete plus a normal refspec) stays gated.
3. Add tests next to the hook's existing tests, if it has any (check `hooks/` and `ci/` for a
   push-gate test file first). Cover: `--delete b`, `origin :b`, `-d b`, `--delete b` with a URL
   remote, a mixed `origin main :b` (still gated), and a plain `push` (still gated).

Rejected: allowing every push whose HEAD is already on the remote. That needs a network call and
would open the gate for a force push that rewrites a remote branch.

## Acceptance

- `git push origin --delete foo` and `git push <url> :foo` pass the hook on an unmarked HEAD.
- `git push`, `git push origin main`, `git push origin main :foo` are still denied on an unmarked
  HEAD.
- `push-read-gate.py` (first push of a session needs auto-commit.md read) keeps its own behaviour.
  Decide separately whether a delete-only push should count for it, and say which in the commit.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
