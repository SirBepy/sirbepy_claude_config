<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=1, content-hash=36a1ef48 -->
<!-- duplicate-checked -->
# CLAUDE.md's `pnpm --workspace-concurrency=5` rule errors out on `pnpm install`

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix a global rule that cannot be followed as written, so sessions stop hitting a hard error while
trying to comply with it.

## Context

Hit 2026-08-22 in `hubbub` (pnpm 10.33.4). Global `CLAUDE.md`'s Process Hygiene section says:

> **Cap concurrency at 5** for all Node commands: turbo `--concurrency=5`, vitest
> `poolOptions.threads.maxThreads: 5` ..., pnpm `--workspace-concurrency=5`.

Following that literally on an install fails:

```
corepack pnpm install --workspace-concurrency=5
 ERROR  Unknown option: 'workspace-concurrency'
Did you mean 'network-concurrency'?
```

The flag is real but belongs to `pnpm run` / `pnpm exec` style recursive commands, not to
`install`. The rule names "pnpm" flatly, with no scope, so a session reading it applies it to the
install it is about to run - which is by far the most common pnpm invocation. The failure is
non-destructive but it costs a round trip every time, and the obvious "fix" (drop the flag) reads
like ignoring a non-negotiable rule.

Verified the same day that a bare `corepack pnpm install` is what actually works in that repo.

## Approach

1. Confirm which pnpm subcommands actually accept `--workspace-concurrency` on pnpm 10 - check
   `pnpm help install` and `pnpm help run` rather than trusting this todo.
2. Rewrite the bullet to name the subcommands it applies to, e.g. "pnpm recursive/run:
   `--workspace-concurrency=5`; plain `pnpm install` takes no concurrency flag."
3. While in there, sanity-check the other two entries in the same bullet against current versions -
   `turbo --concurrency=5` is verified working in `hubbub` as of 2026-08-22, the vitest one is not.
4. If `network-concurrency` is the right knob for install-time parallelism, say so explicitly
   rather than leaving the gap.

## Acceptance

- The Process Hygiene bullet can be followed literally on `pnpm install` without erroring.
- Each named flag in that bullet is scoped to the commands that accept it.
- Any flag left in the bullet has been verified against the installed tool version, with the
  version noted.

## Notes

- Low severity, high frequency: every monorepo session runs `pnpm install`, so this trips often
  and each trip wastes a turn.
- Do NOT weaken the concurrency cap itself. The cap exists because of a real incident (90+ orphan
  vitest processes at 100% CPU); only the flag spelling is wrong.
