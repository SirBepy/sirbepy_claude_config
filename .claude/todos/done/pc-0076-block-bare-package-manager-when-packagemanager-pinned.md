<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Block a bare yarn/npm/pnpm call when package.json pins a different packageManager

**Type:** skill-improvement
**Origin:** ai

## Goal

A `PreToolUse` hook that refuses `yarn|npm|pnpm install` (and other lockfile-mutating subcommands) when the target repo's `package.json` has a `packageManager` field naming a different manager or major version than the binary about to run, and tells Claude the corepack-prefixed command to run instead.

## Context

**Incident, 2026-08-10, `revaire-server`.** Claude ran a bare `yarn install`. A global **yarn 1.22.22** is on PATH and shadowed the repo's pin (`"packageManager": "yarn@4.9.3"`, `.yarnrc.yml` with `nodeLinker: node-modules`). Yarn 1 silently "succeeded", printed `success Saved lockfile`, built a v1-layout `node_modules`, and **rewrote the Yarn 4 `yarn.lock` in v1 format**. It only surfaced because the Docker build log showed `corepack enable && yarn install --frozen-lockfile` running Yarn 4.9.3, which prompted a `git status` check that revealed ` M yarn.lock`. Recovery was `git checkout -- yarn.lock`, `rm -rf node_modules`, `corepack yarn install` - about four wasted tool calls plus a ~2.5 minute reinstall.

**Why a hook and not a rule.** The project memory `project_revaire_server_local.md` **already said** "yarn is NOT global - get it via `corepack enable` (repo pins Yarn 4.9.3)", and that memory was loaded in context at the time. It was still not applied. This is precisely the enforcement-gap shape: the knowledge existed, was surfaced, and lost to momentum. A "remember to check" rule has already demonstrably failed once.

**Why it is worth catching.** The failure is silent and destructive-adjacent: an exit-0 command that corrupts a checked-in lockfile. If it had been committed it would have broken CI and every other developer's install. Same family as the `Set-Content` BOM ban in global CLAUDE.md - the shell path is what makes the bug reachable, so ban the path.

Related existing todos, deliberately NOT duplicated here: `07`, `21` and `64` all cover the no-chained-shell-commands rule and its missing enforcement. This is a different rule.

## Approach

1. Add a `PreToolUse` hook on `Bash` and `PowerShell` in the global `~/.claude/settings.json` (see the `update-config` skill for the settings shape).
2. Detection, kept deliberately narrow to avoid false positives:
   - Match the command against `\b(yarn|npm|pnpm)\b` NOT already prefixed by `corepack`.
   - Only fire for subcommands that can mutate a lockfile or `node_modules`: `install`, `add`, `remove`, `up`, `upgrade`, `dedupe`, and a bare `yarn` with no subcommand (which is `yarn install`). Let `run`, `test`, `why`, `info`, `dlx`, `--version` through untouched.
   - Resolve the target directory: an explicit `--cwd <path>` / `-C <path>` if present, else the tool call's working directory. Walk up for the nearest `package.json`.
   - Read its `packageManager` field. No field means no opinion - allow.
3. Compare the pinned manager+major against what the bare binary would resolve to. Cheapest reliable check: if `packageManager` is present at all and the command is not corepack-prefixed, block - corepack is the correct invocation whenever a pin exists, regardless of what happens to be on PATH. That avoids having to shell out to `yarn --version` inside a hook.
4. Deny with a message naming the exact replacement, e.g. `packageManager pins yarn@4.9.3 - run "corepack yarn install", not bare "yarn install" (a global yarn 1 on PATH silently rewrites the lockfile)`.
5. Verify on `C:\Users\tecno\Desktop\Projects\revaire-server`: bare `yarn install` blocked, `corepack yarn install` allowed, `yarn run build` allowed, and a repo with no `packageManager` field unaffected.

## Acceptance

- Bare `yarn install` in `revaire-server` is denied with the corepack replacement named in the message.
- `corepack yarn install` runs unimpeded.
- Non-mutating subcommands (`yarn run`, `npm test`) are never blocked.
- A repo whose `package.json` has no `packageManager` field behaves exactly as before - zero new friction on the many projects that do not pin.
- Hook adds no perceptible latency: pure file read plus regex, no process spawn.

## Notes

The global CLAUDE.md "Packages" section already mandates a post-resolution `npm audit`/`cargo audit` against the real tree. This hook is complementary, not a duplicate: that rule is about *what* gets installed, this one is about *which binary does the installing*.

Scope check per global CLAUDE.md: this is a finding about the global `~/.claude` tree, so it is filed here rather than in `revaire-mobile/.claude/todos/`, and it must NOT be executed from inside a project session unless Joe says so in that session.
- Shipped 2026-08-11, wired in commit f9055ac. hooks/package-manager-guard.py resolves the nearest package.json (honouring --cwd/-C/--dir/--prefix) and blocks mutating yarn/npm/pnpm subcommands unless invoked via corepack with the pinned manager. Read-only subcommands untouched. 18/18 against a real fixture. Open tuning question: it requires corepack even when the PATH binary already matches the pin.
