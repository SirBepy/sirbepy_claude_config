<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=6, reconfirm-count=1, content-hash=f81b337d -->
<!-- duplicate-checked -->
# commit-guard's bypass message tells you a variable to set but not where to set it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `hooks/commit-guard.py`'s rejection message say WHERE `CLAUDE_COMMIT_HOOK_BYPASS=1` has to be
set, since the obvious reading of it does not work.

## Context

Found 2026-08-21 while building todo 419's guard, which copied commit-guard's bypass pattern and
inherited the same ambiguity before it was caught and fixed there.

`commit-guard.py`'s deny message ends:

> If /commit itself is broken, set CLAUDE_COMMIT_HOOK_BYPASS=1 to bypass.

The natural reading is an inline prefix on the blocked command, `CLAUDE_COMMIT_HOOK_BYPASS=1 git
commit -m "..."`. **That cannot work**, and it was proven empirically for the equivalent variable in
todo 419's guard: a nested `claude -p` ran
`CLAUDE_DESTRUCTIVE_HOOK_BYPASS=1 chmod 777 throwaway-probe.txt` and the guard fired anyway. The
mechanism is structural rather than a bug: a `PreToolUse` hook reads the command STRING before any
shell parses it, so an inline assignment has not been evaluated yet and the hook process never
receives it. The variable has to be in the SESSION's environment: `settings.json`'s `env` block, or
exported before launching `claude`.

So the message names a real escape hatch and simultaneously points at the one way of using it that
fails. Someone hitting a genuine false positive under time pressure tries the inline form, sees the
guard fire again, and concludes the bypass is broken.

419's own message was reworded to fix this:

> To bypass a false positive, set CLAUDE_DESTRUCTIVE_HOOK_BYPASS=1 in this session's environment
> (settings.json "env", or exported before launching claude) - an inline prefix on the command itself
> does not reach this hook.

## Approach

1. Read `hooks/commit-guard.py`'s deny message and its module docstring. Both mention the variable.
2. Reword both to name the two places the variable actually works, and to say plainly that an inline
   prefix does not reach the hook. Match 419's wording so the two guards read the same way.
3. Sweep for the same shape in any other guard that offers an env-var override, and fix each. At
   least `hooks/pr-guard.py` is worth checking, since it is commit-guard's sibling.
4. No test is needed for a message change, but `python ci/run_all.py` must still exit 0, since
   several suites assert on guard output substrings and a reword can break one.

## Acceptance

- `commit-guard.py`'s message names `settings.json` `env` or a pre-launch export explicitly.
- Any other guard with an env-var override says the same thing.
- `python ci/run_all.py` exits 0.

## Notes

Do not add the inline form as a supported path by reading the variable out of the command string.
That would let the model bypass its own guard by typing a prefix, which is exactly the property that
makes the current behaviour correct. The bug is the wording, not the mechanism.
