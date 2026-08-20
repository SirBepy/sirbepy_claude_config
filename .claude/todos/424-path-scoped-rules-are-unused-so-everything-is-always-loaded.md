<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Path-scoped .claude/rules/ is unused, so every rule is always-loaded

**Type:** task
**Origin:** ai

## Goal

Move rules that only matter for specific file types out of the always-loaded CLAUDE.md into
path-scoped rule files that load only when Claude touches matching files.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Claude Code natively supports `.claude/rules/*.md` with a `paths:` frontmatter glob. A rule file
loads **only when Claude touches a matching file**, and costs nothing otherwise.
`poshan0126/dotclaude/rules/{database,security,error-handling}.md` uses this, with always-loaded
rules capped at 30 lines and everything conditional pushed into path-scoped files.

Current state here: everything in global `CLAUDE.md`, `refs/`, `snippets/` and `code-style/` is
either always-loaded or manually `@import`ed with a "read once per session" instruction. Global
CLAUDE.md is large and growing, and the pattern for adding a rule is "add a bullet to CLAUDE.md",
which has no ceiling.

The relevant evidence, and the reason this is worth doing rather than just tidy: an unverified
community report in the harvest describes a CLAUDE.md growing 45 to 190 lines with compliance
**dropping**, attributed to mixing mechanical rules into behavioral guidance. Anthropic's own docs
describe the same over-specification failure. This CLAUDE.md is well past 190 lines. So the risk is
not token cost, it is that adding a rule makes the other rules weaker.

`code-style/` is the clearest existing candidate: it already has per-stack files (`luau.md`,
`react.md`) loaded via a "check on first encounter with a project's stack" instruction, which is
exactly what `paths:` does mechanically instead of by remembering. Several CLAUDE.md rules are also
obviously file-type-scoped rather than global: the Phosphor icons rule (frontend only), the
persistence rule (localStorage/DB code), the comment budget (code files, not markdown).

This todo pairs with 423: the token budget gate gives a number, this gives the mechanism to get
under it.

## Approach

1. Verify the mechanism actually works in this harness before migrating anything. Create one trivial
   `.claude/rules/` file with a `paths:` glob, touch a matching and a non-matching file, and confirm
   it loads and does not load respectively. The `InstructionsLoaded` hook is documented as the way to
   debug instruction loading and is also unused here, so it may be the cheapest observation tool.
   **Do not migrate rules on the assumption this works.**
2. Audit global CLAUDE.md and classify every rule: genuinely global (communication style, git
   commits, question protocol, delegation) versus file-type-scoped (icons, persistence, comment
   budget, per-stack style). Produce the classification as the deliverable of this step, before
   editing anything, so the scope is visible.
3. Migrate the clearly-scoped ones first, one at a time, and measure the always-loaded weight before
   and after. Report real numbers.
4. Decide what happens to `code-style/`. It is already the right shape, so the question is whether it
   becomes `.claude/rules/` files with `paths:` globs, or stays as-is with its manual-load
   instruction. Recommend converting, since the manual instruction is exactly the kind of rule that
   depends on being remembered.
5. Leave `refs/` alone. Those are procedures read on demand by skills, not rules that should
   auto-load, and converting them would make sessions load material they do not need.

## Acceptance

- The mechanism is proven with a real load and a real non-load, not assumed.
- A written classification of every current CLAUDE.md rule as global or path-scoped exists.
- At least the clearly-scoped rules are migrated, with the always-loaded weight stated before and
  after as real measured numbers.
- No rule silently stops applying: for each migrated rule, name a file path that triggers it and
  confirm it loads there.
- Global CLAUDE.md still reads coherently. A migration that leaves dangling references to moved rules
  is worse than not migrating.

## Notes

The failure mode to avoid is a rule that quietly stops firing because its glob does not match what
the dev actually edits. That is strictly worse than an always-loaded rule, because nothing signals
the absence. Hence the per-rule trigger check in acceptance.

Do not migrate the whole CLAUDE.md in one pass. Migrate, verify the rule still fires, then continue.
