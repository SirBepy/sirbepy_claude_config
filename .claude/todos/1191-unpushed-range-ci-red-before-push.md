<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no open todo names auto-respawn's missing flag or VENDORED.md's asd-ste100 row -->
# ~/.claude's unpushed range leaves ci/run_all.py red: fix before the next push

**Type:** task
**Origin:** ai

## Goal

`python ci/run_all.py` passes on the commits waiting to be pushed in `~/.claude`, so they can go
through the push gate.

## Context

A pre-push `/code-check` on 2026-10-17 (run from a claude_usage_in_taskbar session that wanted to
push its own `1cd3cb9`, the `/people` skill) over `@{u}..1cd3cb9` found `check_skill_frontmatter.py`
failing on two files this range adds. That session did not push `~/.claude` and did not edit other
sessions' skills:

- `skills/auto-respawn/SKILL.md:2` (commit 958c68d): the description says "Triggers on /auto-respawn
  only" but the frontmatter has no `disable-model-invocation: true`. Mechanical; the CI check fails
  on this line today and passes after the one-line fix.
- `skills/asd-ste100/SKILL.md:2` (commit 6813a5a, vendored): description 67w/465c vs the 25w/120c
  budget. A judgment call: trim it (vendor drift) or add a dated `LEGACY_OVER_BUDGET_DEBT` entry with
  a vendoring rationale. The 2026-10-15 `dropped-findings.log` entry that declined this said "no named
  test"; `check_skill_frontmatter.py` is one, so that premise no longer holds.
- `skills/VENDORED.md` has no row for asd-ste100 (source github.com/danyuchn/asd-ste100-skill,
  version 0.4.0 per its frontmatter, vendored in 6813a5a).
- `skills/impeccable/SKILL.md:2` fails the same check but predates this range.

Also raised, not a blocker: `skills/people/SKILL.md` and `skills/auto-respawn/SKILL.md` say "Joe",
against bepy-skill-creator's "no hardcoded user names" FAIL rule; 23 existing skills (including
bepy-skill-creator itself) break the same rule, so decide once whether it binds this single-user repo.

## Approach

Add the auto-respawn flag; decide and land the asd-ste100 budget remedy; add the VENDORED.md row;
rerun `python ci/run_all.py`; then push through the normal gate.

## Acceptance

`python ci/run_all.py` exits 0 on HEAD, and the range is pushed.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Say push to ship `~/.claude` master. The frontmatter fix landed (a9c74ff); `ci/check_skill_frontmatter.py` is clean on HEAD. The working tree still fails it on `skills/impeccable/SKILL.md` only, because another session's uncommitted 4.5.2 re-vendor restored the long description; that session has to re-trim it before committing.
