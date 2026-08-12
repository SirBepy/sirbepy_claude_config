<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=7f85c36a -->
# Give /commit a formal way to target a repo other than the active project

**Type:** skill-improvement

## Goal

`~/.claude/skills/commit/SKILL.md` has no documented way to commit into a repo that isn't the
current project's cwd. Add one instead of relying on an ad-hoc prose argument.

## Context

This session needed to commit into `C:/Users/tecno/.claude` (the dotfiles repo) twice while the
active project was Fibo (`C:/Users/tecno/Desktop/Projects/fibo`) — once for the design-review
context docs + gitignore fix, once for the vendored Vercel skill. Both times, the workaround was
invoking the Skill tool with free-text args like `"repo: C:/Users/tecno/.claude (dotfiles repo,
NOT the Fibo project) — commit only the currently staged file..."`. It worked because the skill's
instructions are generic enough (`git -C <path>` throughout) to follow prose intent, but there's
no actual documented syntax for "target repo X" — a future cold AI session reading only
`SKILL.md` wouldn't know this is supported at all.

## Approach

Add a short section to `~/.claude/skills/commit/SKILL.md` documenting an explicit repo-path
convention, e.g. `/commit --repo <path>` or noting directly in the "Rules" section: "If the dev
or a prior instruction specifies a repo path other than the current project, use `git -C <path>`
for every git command in this run instead of the implicit cwd — state the repo path back in the
first line of output so it's unambiguous which repo is being committed to."

## Acceptance

- `SKILL.md` explicitly documents the non-default-repo case (not just implicitly supported via
  prose-following).
- Next time this comes up, invoking `/commit` with a repo path doesn't require re-deriving the
  same ad-hoc phrasing from scratch.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 124; renumbered to 22 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: Added a bullet to SKILL.md's `## Rules` section documenting the `git -C <path>` convention and the "state the repo path back" requirement.
