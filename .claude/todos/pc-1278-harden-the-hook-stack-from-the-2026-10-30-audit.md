<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 1; pc-1160 and pc-1257 are different hook defects -->
# Harden the hook stack: recoverable import failures, dev-server-guard false denies, commit-guard heredoc bypass, per-call cost

**Type:** task
**Origin:** dev
**Summary:** Hooks stop blocking harmless commands, one bad shared-library edit no longer locks every session out, and each shell call starts fewer processes.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run ("All 9 bundles"). It was left for an attended run because every guard fails closed, so a bad edit here blocks every live session.

## Goal

The hook stack keeps its zero-exception guards but stops false-denying ordinary commands, can be repaired from inside a session, and costs less per tool call.

## Context

Findings verified by a refuter (probes piped synthetic payloads into the hooks):

- `hooks/_hooklib.py:13` docstring promises an "Edit/Write bypass" escape. False: `hooks/secret-write-guard.py:25-28` and four other Write/Edit guards exit 2 on a failed `_hooklib` import, so a broken `_hooklib.py` blocks Bash, PowerShell, Write and Edit together. The import retry from pc-0923 exists only in `destructive-command-guard.py` (and catches ImportError only). 18 guards have the same FATAL branch.
- `hooks/dev-server-guard.py` denies `npm install fastify`, `pip install uvicorn`, `pnpm add -D vite`, `grep vite`, `ls node_modules/vite`, `npm view vite version` (all exit 2). It matches the tool name anywhere in the command, not as the launched program.
- `CLAUDE.md:59`, `refs/process-hygiene.md:55` and `skills/supervised-run/restart-and-wait.ps1:57` tell sessions to fall back to a plain shell run when the supervisor is down; `dev-server-guard.py` denies exactly that. pc-1120 fixed only the SKILL.md copy.
- `hooks/commit-guard.py` lets a raw `git commit` through with a bare `<<'EOF'` heredoc or a PowerShell `@'...don't...'@` here-string (exit 0). `-m "$(cat <<'EOF'...)"` and `-m "it's"` are blocked. `hooks/test_commit_guard.py` has no heredoc or unbalanced-quote case.
- `approve-rename.ps1` (wired in `settings.json` ~302-307) cold-starts PowerShell (~240 ms measured once) on every PowerShell call and returns allow for any command containing `rename-session.ps1`, e.g. one ending in `# rename-session.ps1`.
- `hooks/status-marker-guard.py` polices `<cc-status>` markers that Conductor replaced with `report_turn_status` (Conductor `args.rs:5-8`); nothing emits them.
- Per-call cost recounted from `settings.json`: 25 hook processes per Bash call, 26 per PowerShell, 8 per Write, 7 per Edit. No hook uses the native `"if"` condition yet. Wall-clock cost is unmeasured.
- Smaller: `push-read-gate.py` / `push-gate.py` / `pr-guard.py` miss `git.exe` / `gh.exe`; `em-dash-guard.py` does not scan `write_draft` text; `testing-floor-guard.py` has no "don't test" skip; `commit-guard.py` and `_testing_floor_lib.py` exec all of `agent-todo-write-guard.py` to read one predicate.

## Approach

1. Add the pc-0923 retry pattern to every `_hooklib` importer (or a tiny shared bootstrap), and make the docstring true, or remove the false bypass claim. Keep fail-closed.
2. `dev-server-guard.py`: match only when the command launches a dev server (first program word, or `npm/pnpm/yarn run <dev-script>`), not when a server name appears as an argument. Add the probe commands above as tests. Fix the three stale fallback texts (CLAUDE.md:59 needs the dev's wording because of its 24-token CI headroom).
3. `commit-guard.py`: handle heredocs and here-strings; add tests for both shapes.
4. Port `approve-rename.ps1` to Python and anchor the match to the actual script invocation.
5. Remove `status-marker-guard.py` and its `settings.json` entry in one commit, settings entry first.
6. Measure hook wall-clock per shell call, then add `"if"` filters to the hooks that only care about specific commands.
Write each shared hook file in a single Write call, never partial Edits (a half-written module a guard imports takes shell access from every session).

## Acceptance

- The six probe commands above pass `dev-server-guard.py`; `npm run dev` and `npx vite` still deny.
- A deliberately broken `_hooklib` import in a scratch copy is recoverable as documented.
- `python ci/run_all.py` passes, including new hook tests.
- Measured per-call hook time recorded in the commit body before and after.
