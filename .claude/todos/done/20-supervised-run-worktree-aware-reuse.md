<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=c02985f1 -->
# supervised-run reuse should match proc ROOT, not just project name

**Type:** skill-improvement

## Goal

Make the `/supervised-run` reuse step worktree-aware so it never serves a stale branch.

## Context

Skill file: `C:\Users\tecno\.claude-fibo\skills\supervised-run\SKILL.md` (step 3, "List first -
reuse before you create"). It reuses an existing proc when `project` matches the current folder
name AND the command matches. In a repo with git worktrees, several entries share the same
`project` name (e.g. Fibo has `frontend:dev`, `frontend-2:dev`, `frontend-3:dev`, each rooted in a
different worktree/branch). Matching by name alone can reuse a proc rooted in another branch's
checkout and serve stale code.

Incident (2026-07-15, feature/navigation-revamp): reused `frontend-3:dev` (a worktree on
feature/e2e-check-skill); the dev saw old UI and thought changes hadn't landed. Roots are in
`%APPDATA%\com.sirbepy.server-supervisor\supervisor\projects.json`.

## Approach

Amend step 3 of the skill: when several entries share the target `project`/command, disambiguate
by ROOT — reuse only the entry whose `root` (from `projects.json`) equals the ABSOLUTE path of the
current working dir (not just the folder basename). If none matches the current root, `/run` a new
one (or start the stopped entry whose root matches) rather than reusing a same-named worktree proc.

## Acceptance

- The skill's reuse instructions explicitly say to match on absolute `root`, with a one-line note
  about the multi-worktree ambiguity + where roots live.
- Following the updated skill on a repo with worktrees serves the current branch's checkout.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 112; renumbered to 20 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: `sv.ps1 ensure` matches project + registered absolute `root` (from `projects.json`) before reusing a proc; SKILL.md step 1 carries a one-line note on the worktree-ambiguity + where roots live.
