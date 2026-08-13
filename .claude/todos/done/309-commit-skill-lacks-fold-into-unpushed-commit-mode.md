<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit skill has no mode for folding a fix into an existing unpushed commit

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/commit` (`~/.claude/skills/commit/SKILL.md`) an explicit subcommand or documented flow for "fold these staged changes into commit `<sha>`, which is already committed but not pushed", so this doesn't require falling back to manual git surgery outside the skill.

## Context

2026-07-16, zng-biller: dev said "fix it and fold it into that commit that we didn't push yet", a specific, unambiguous request to amend a *non-HEAD* unpushed commit (`c3ad69f`, with another unpushed commit `32d24e5` sitting on top of it). The global rule is "NEVER commit directly. Always invoke `/commit` first... every commit, no exceptions." But `/commit`'s SKILL.md only covers: normal commit, version-bump variants, and push variants, none of them handle folding into a specific *older* commit while preserving its original message and everything committed on top of it.

Since `git rebase -i --autosquash` is also forbidden (global rule bans any `-i` flag, even with `GIT_SEQUENCE_EDITOR=true` to avoid hanging), the resolving session did this manually: staged the fix, verified no file overlap with the commit on top, `git reset --soft <parent-of-target>`, then split-recommitted via pathspec (`git commit <file> -m "<original msg>"` then `git commit -m "<next original msg>"` for the remainder), backdating both to their original timestamps. Full recipe saved as a zng-biller project memory: `reference_fold_into_unpushed_commit.md`.

This worked and was verified byte-identical (patch-diff, not full-tree-diff, confirmed the untouched commit's own changes were unchanged), but it bypassed `/commit` entirely, which is a real gap against the "no exceptions" rule, not a one-off judgment call that should recur silently next time.

## Approach

- Add a new `/commit fold <sha>` (or similar) subcommand to `~/.claude/skills/commit/SKILL.md`, alongside the existing `v`/`bump`/`push`/`pushbump`/`pushnbump`/`onlyv`/`onlybump` variants.
- Flow should mirror the manual recipe in zng-biller's `reference_fold_into_unpushed_commit.md` memory: confirm `<sha>` is unpushed, confirm no file overlap with commits on top of it, `reset --soft` to its parent, pathspec-split-recommit preserving each original message/timestamp, verify via patch-diff (not full-tree-diff) that untouched commits are unchanged.
- Should refuse (or ask) if `<sha>` IS pushed, or if there's a file overlap between the target commit and something on top of it (the pathspec-split technique can't cleanly separate overlapping hunks, that needs the existing "Splitting one file across commits" partial-staging recipe instead, already documented in `/commit`'s SKILL.md).
- This is project-agnostic (git-only), so the change belongs in the global `~/.claude/skills/commit/SKILL.md`, not a project-local override.

## Acceptance

- `/commit fold <sha>` (or whatever name is chosen) exists and is documented in the skill's subcommand list.
- Dry-run against a throwaway local repo (2 unpushed commits, a fix targeting the older one, no file overlap) reproduces the same result as the manual recipe.
- The skill explicitly declines/asks when `<sha>` is already pushed or when file overlap makes a clean pathspec split impossible.

## Notes

Not urgent, the manual recipe works and is now memorized, but this is the second time in recent history that a real, explicit dev request ("fold this into commit X") hit a gap in `/commit`'s subcommand coverage. Worth closing so future sessions don't have to reason through the rule tension from scratch each time.

Relocated from 42 in zng-biller via /cleanup-todos 2026-08-13: targets global ~/.claude/skills/commit/SKILL.md per the todo's own text.
- Done 2026-08-13. /commit gained a fold <sha> mode, added to the frontmatter subcommand list so it is discoverable. It defers to auto-commit.md's atomic update-ref recipe when the target is HEAD with nothing on top, and handles the harder case (commits sitting on top) with a pathspec-split recommit rather than a rebase, since the global rule bans -i. Preconditions are explicit: refuse when the target is already pushed (no upstream counts as safe), refuse on file overlap with commits on top and redirect to the existing partial-staging recipe, plus the usual step 5a prefilters, branch guard and peer check. Proved in a throwaway repo, never against real history: a 4-commit chain folded a fix into the OLDEST commit with two commits on top, original messages and backdated author/committer timestamps preserved, and patch-diff confirmed the untouched commits byte-identical. The refusal path was proved too, by pushing and re-running the check. Also fixed 6 em dashes in this todo's own text.
