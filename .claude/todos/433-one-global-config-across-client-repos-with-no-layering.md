<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=6, reconfirm-count=1, content-hash=2958002e -->
<!-- duplicate-checked -->
# One global config serves every client repo, with no layering mechanism

**Type:** task
**Origin:** ai

## Goal

A way for client repos to add their own rules and skills without either duplicating the global config
or having project-specific concerns leak into it.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current state: one global `~/.claude` tree (83 skills, 41 hooks, one CLAUDE.md) applies to every repo
Joe works in, personal and client alike. Per-project customisation happens two ways today, both
ad hoc: a project `CLAUDE.md`, and occasionally a gitignored project-local skill (memory records
`/framer` living in `zng-app/.claude/skills/framer` as personal tooling rather than in `~/.claude`).

There is no mechanism for "this is shared, that is project-specific, and here is how they compose".
The visible symptoms are already in the global config: CLAUDE.md carries repo-specific knowledge that
does not belong in a global file, naming `zng-app` and `zng-biller` explicitly for their shared git
index, and `zirtue-corp`/`Fibo-Studio`/`revaire` for gh account mapping. Those are project facts
living in the global layer because there is nowhere else for them.

Reference: `repos/DazzleML_dazzle-claude-code-config` and its `ccs` tool (`docs/setup.md`,
`customization.md`). Three mechanisms worth understanding:

1. `ccs apply` copies shared skills and hooks into `~/.claude/`, and seeds personal files **only if
   absent, never overwriting**.
2. The shared `CLAUDE.md` **imports personal `@`-files**, so a personal override is a separate file
   the shared one references. Upstream pulls never conflict with local edits, because they touch
   different files.
3. `ccs status` reports drift and `ccs collect` pulls local edits back into the shared repo, with
   credential scanning on the way.

Mechanism 2 is the transferable one and is available natively: CLAUDE.md already supports `@import`,
and this setup already uses it for snippets. Mechanisms 1 and 3 are a sync tool, which matters for a
team distributing config and much less for one person with one machine and one git repo.

Also relevant, and cheaper: **path-scoped `.claude/rules/`** (todo 424) solves part of this problem
from the other direction. A rule that only matters for one stack can be scoped by glob rather than by
repo. Read 424 first; the two overlap and should not produce two competing mechanisms.

## Approach

1. Establish the actual problem before designing, because it may be smaller than it looks. Audit
   global CLAUDE.md for content that is project-specific rather than universal (the shared-index repo
   names, the gh account map, any stack-specific rule). List it. **If that list is short, the honest
   answer may be "move those five lines and stop", not a layering system.**
2. Read 424's classification if it has run. Path-scoped rules and per-project layering are different
   axes and the audit in step 1 will show which axis each item actually belongs on.
3. Decide the composition model, and keep it native: a project `.claude/` that `@import`s from the
   global tree, with the global CLAUDE.md carrying only universal rules. Do not build a sync tool.
   One machine, one repo, edited directly, is not the problem `ccs` solves.
4. Define where project-local skills live and say it out loud. Today `/framer` is gitignored inside a
   client repo, which works but is undocumented and invisible. Write the convention down (it belongs
   in the README from todo 428).
5. Verify composition actually happens rather than assuming. Take one client repo, move one
   project-specific rule out of global CLAUDE.md into it, and confirm the rule still applies there and
   no longer applies elsewhere. **Both halves need checking**: a rule that silently stops applying is
   the failure mode.

## Acceptance

- A written list of project-specific content currently sitting in global CLAUDE.md.
- An explicit recommendation, including "just move these lines" if the audit supports it.
- If a composition model is adopted: one rule migrated, proven to apply in its repo and proven not to
  apply in another.
- No sync tool is built.
- The project-local skill convention is documented.

## Notes

Resist building `ccs`. It exists because a team distributes config to many machines. Joe has one
machine and edits the source of truth directly, and memory already records that personal tooling must
not override shared project decisions, which is the concern a sync tool would reintroduce.

The likely honest outcome is that this is a documentation and five-line-move task, not an
architecture task. That is a fine result; write it down rather than inflating the work.
