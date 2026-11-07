<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hits are flutter/cargo bump and hook todos, none about a repo-declared pre-bump command -->
# /release should run a repo's pre-bump smoke command before pushing the VERSION commit

**Type:** task
**Origin:** ai
**Summary:** The global `/release` skill has no hook for a repo-specific smoke check, so a failure that only CI's smoke job catches costs a version number.

## Why

rodge release 0.2.1 stopped at the CI `smoke` job after `/release` had pushed the `VERSION:` commit, and 0.2.1 was lost (rodge todo pc-0119). Joe decided on 2026-11-05 that `pnpm smoke:image` (`infra/deploy/test/image-smoke.sh`) runs in the e2e step before every bump in rodge. The repo's `CLAUDE.md` now says so, but nothing in the global skills runs it.

## Goal

`/release` (or `/e2e` before it) runs a repo-declared pre-bump command and stops before the `VERSION:` commit is pushed when it fails.

## Context

- rodge `CLAUDE.md`, "Testing and supply chain": the bullet naming `pnpm smoke:image`.
- `~/.claude/skills/release/SKILL.md` and `~/.claude/skills/commit/SKILL.md` "Push pipeline" are where the step list lives.

## Approach

Let a repo name a pre-bump command (a line in its `CLAUDE.md`, or a file the skill reads) and run it as the last e2e step of `/release`. Keep it generic, no rodge names in the skill.

## Acceptance

A deliberately failing pre-bump command stops `/release` before the `VERSION:` commit is created.

## Decided

- The repo declares its checks in `.claude/pre-bump.txt` (one command per line, `#` comments), read by `release.py pre-bump`, not a line in `CLAUDE.md`: a file is parseable and testable, prose is not. Step 4a in `skills/release/SKILL.md` and `skills/commit/SKILL.md`'s Push pipeline list.
- It runs after the gate, before 4b, so a rejected build never gets a VERSION commit; `test_release.py` `PreBumpTest` pins that a failing command exits 1 and stops the rest.

## Completion note

Verify only / follow-up in the other repo: rodge still needs a `.claude/pre-bump.txt` containing `pnpm smoke:image`; that file belongs to rodge and was not written from this repo.
