<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Enforce the global "never chain shell commands" rule

**Type:** skill-improvement
**Origin:** ai

## Goal

Global `CLAUDE.md` says *"Never chain commands with `&&`, `;`, or `|` - one command per call,
always, git included."* It is currently advisory only, and gets violated silently and constantly.
Make it enforced rather than remembered.

## Context

Surfaced by the 2026-08-10 zng-app session retrospective. Across roughly forty Bash calls the rule
was broken in the large majority of them - `&&` to chain `cd` with a command, `;` to run several
inspections in one call, `|` into `head`/`grep`. No hook fired, nothing flagged it, and the
violations only became visible when the session was reviewed at close.

Notably the rule WAS respected where it mattered most: every state-changing git command
(`reset`, `commit`, `push`, `stash`) went one per call. So the failure is concentrated in
read-only inspection calls, which is also where the rule's value is lowest.

That asymmetry is the real question this todo has to answer: the rule as written is absolute, but
behaviour has settled into "strict for mutations, loose for reads". Either the rule should say
that, or enforcement should be absolute. Right now it says one thing and practice does another,
which is the worst of both.

Related: `~/.claude/hooks/` already hosts a `PreToolUse` hook for gh account switching and a
commit-guard hook, so the mechanism exists.

## Approach

Decide the intent first, with Joe, then implement one of:

1. **Narrow the rule to mutations.** Rewrite the `CLAUDE.md` line to forbid chaining only for
   state-changing commands (git writes, installs, deletes, migrations) and explicitly allow it for
   read-only inspection. Cheapest, and matches what actually happens.
2. **Enforce absolutely.** Add a `PreToolUse` hook that rejects any Bash `command` containing a
   top-level `&&`, `;` or `|`. Needs care: it must not trip on those characters inside quoted
   strings, heredocs, awk/sed programs, or regex - a naive substring match would block a lot of
   legitimate single commands.

Option 2 is the literal reading of the rule but has real false-positive risk; option 1 is honest
about current practice. Do not implement both.

## Acceptance

- Global `CLAUDE.md` and actual behaviour agree, whichever way it is resolved.
- If a hook is added: it blocks a chained `git commit -m x && git push`, and does NOT block
  `grep -oE 'a|b' file` or an awk program containing `;`.
- Existing hooks keep working (`gh-account-switch.sh`, commit guard).

## Notes

Do not action this from inside a project session. Per global `CLAUDE.md`, editing the `~/.claude`
tree from a project repo needs Joe to say so explicitly in that session; filing this todo is the
allowed part.
- Duplicate of 07 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
