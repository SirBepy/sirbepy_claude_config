<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The "never chain shell commands" rule has no enforcement and is routinely ignored

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether global CLAUDE.md's no-chaining rule should be enforced by a hook, narrowed to what
it actually means, or dropped. Right now it is stated as absolute, broken constantly, and nothing
notices.

## Context

Global `CLAUDE.md`, Shell Commands section, states:

> Never chain commands with `&&`, `;`, or `|` - one command per call, always, git included.

Found by /close's retrospective on 2026-08-09, in a `hubbub-game-split-opinions` session. That
session violated it roughly fifteen times with zero friction: `cd X && git log ... && echo ...`,
`pnpm typecheck; if ($?) { pnpm test }`, and several `| awk` pipelines. No hook fired, no warning,
nothing in the transcript flagged it.

The rule is not enforceable as literally written, which is probably why it erodes:

- **`/commit` itself mandates a pipeline.** Its step 5a comment-noise prefilter is a multi-stage
  `git diff | awk | sort` that cannot be expressed as one command per call. So the skill Joe uses
  most requires breaking the rule Joe wrote.
- `~/.claude/skills/commit/SKILL.md` separately repeats "Never chain commands. One command per
  Bash call. No `&&`, `;`, or `|`" while shipping that exact pipeline a few lines earlier.
- A pipe into `awk`/`sort`/`head` is one logical operation. `A && B` where B is destructive if A
  half-succeeded is a genuinely different risk. The rule currently treats them identically.

The real intent looks like: do not sequence independent, side-effecting commands in one call,
because a failure midway is invisible and the harness cannot show which step failed. Pipelines
that transform one command's output are not that.

## Approach

Pick one:

1. **Narrow the rule to match the intent.** Ban `&&`/`;` between side-effecting commands (git,
   installs, builds, file writes); explicitly allow `|` pipelines and allow chaining inside a
   single read-only query. Update both global `CLAUDE.md` and `skills/commit/SKILL.md` so they
   stop contradicting each other.
2. **Enforce the narrowed rule with a PreToolUse hook** on `Bash`/`PowerShell`, in the same shape
   as todo 59's no-em-dash hook. Must allowlist the `/commit` prefilter pipeline or it will block
   every commit. This is the only option that actually changes behaviour.
3. **Drop the rule.** If the pipelines were never the problem and `&&` has not actually caused an
   incident, the rule is costing attention for nothing.

Option 1 plus 2 is the coherent pair: a rule worth stating is worth enforcing, and one that cannot
be enforced because it is self-contradictory should be fixed first.

## Acceptance

- Global `CLAUDE.md` and `skills/commit/SKILL.md` agree with each other on what is banned.
- If a hook is added: it blocks a genuine `A && B` side-effecting chain, and does NOT block
  `/commit`'s own prefilter pipeline. Verify both by running them.

## Notes

- Related family, same shape (a stated global rule with no mechanism behind it): todo 59
  (no-em-dash hook), todo 54 (per-session screenshot folder).
- Do not "fix" this by adding a reminder to CLAUDE.md. The rule is already there in plain words
  and was still ignored fifteen times in one session; more prose is not the missing piece.
- Duplicate of 07 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
