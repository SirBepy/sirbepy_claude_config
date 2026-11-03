<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Package safety-check subagents must pin their scratch install directory

**Type:** skill-improvement
**Origin:** ai
**Summary:** A package safety-check subagent can no longer run `pnpm install` in the real repo by mistake when its scratch directory does not exist yet.

## Goal

Scratch installs for package safety checks (the "install for real, then audit the resolved tree" rule in global
`CLAUDE.md` "Packages") always run against an explicit scratch path, never the inherited cwd.

## Context

2026-10-29, dashboard-a architecture chat (session cee45401-9474-433e-af10-42207a217188): a sonnet subagent vetting
`dependency-cruiser` was told to install in `$env:TEMP\depcruise-probe`. Its own report says its first `pnpm install`
ran in the repo root "because the scratch directory had not been created"; pnpm printed "Lockfile is up to date ...
Packages: -10" and pruned 10 undeclared packages from the repo's `node_modules` while another chat's eval jobs ran from
that tree. No tracked file changed; `corepack pnpm install --frozen-lockfile --offline` afterwards printed "Already up
to date". The dispatch prompt named the scratch path but nothing forced the install to use it.

## Approach

- Add a line to `refs/builder-preamble.md` (or the package-check guidance it points to): a scratch install creates the
  directory first and passes it explicitly (`pnpm --dir <scratch> install`, `npm --prefix <scratch>`,
  `cargo ... --manifest-path`), never relies on cwd.
- Optionally extend `hooks/package-manager-guard.py`: when a subagent runs a bare `pnpm install` / `npm install` whose
  cwd is a repo root, warn or deny unless the dispatch declared that repo as the install target. UNVERIFIED whether
  the hook can tell a subagent call from the main agent's; check its input payload first.

## Acceptance

- A dispatch prompt following the preamble cannot reach `pnpm install` in the repo by forgetting `mkdir`.
- Ordinary `corepack pnpm install` by the main agent in a repo still works.

## Notes

- Fixed in the batch 3 builder-preamble commit (scratch install dir pin; the optional package-manager-guard hook was skipped).
