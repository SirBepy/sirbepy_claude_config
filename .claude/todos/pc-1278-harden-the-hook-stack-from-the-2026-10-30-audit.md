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

## Decided

Decided by the 2026-11-07 overnight run (loop-todos lane h5-hook-stack).

- [x] [ARCH] Retry mechanism - decided **one tiny `hooks/_hookboot.py`, imported first inside each guard's existing try block**, because it keeps every guard's own fail-closed or fail-open branch untouched (a module still broken after the retry is left unimported, so the guard's own `from _hooklib import ...` raises the real error) and avoids 41 copies of retry boilerplate. Retries any exception once after 0.4 s (env `CLAUDE_HOOK_IMPORT_RETRY_DELAY_S`), not only ImportError, because a half-written file is a SyntaxError.
- [x] [ARCH] The `_hooklib` docstring's "Edit/Write bypass" - decided **remove the claim**, because the Write/Edit guards fail closed on the same import. Recovery is documented as a terminal outside Claude Code or one atomic Write.
- [x] [ARCH] dev-server-guard - decided **skip a server name that follows `<package manager> <install/inspect verb>` in the same statement** (npm, pnpm, yarn, bun, pip, pipx, uv, poetry, cargo, gem), keeping the existing first-program scan, because a full command-position rewrite risked new false negatives.
- [x] [ARCH] commit-guard unparseable commands - decided **mask heredoc and here-string bodies, then fall back to a command-position regex**, so a shlex failure fails toward gating instead of "not a commit".
- [x] [ARCH] approve-rename - decided **Python hook that approves only when every statement is an invocation of `skills/close/rename-session.ps1`** (direct, `&`, `$x = ...`, or `-File`), with `$(`, backtick and `>` disqualifying.
- [x] [ARCH] status-marker-guard - decided **remove** (settings entry first, same commit as the file), because Conductor replaced the markers with `report_turn_status`. `skills/autopilot/SKILL.md:17` still names it in prose (outside this lane's write set).
- [x] [TOOLING] `"if"` filters (approach step 6) - decided **not applied tonight**, because a filter string like `Bash(*git*)` only matches the Bash tool, so each hook serving `Bash|PowerShell` would split into two entries, and a wrong pattern silently disables a guard, the failure this bundle exists to remove. Facts gathered: `"if"` exists in the hook schema of claude 2.1.316 ("Permission rule syntax to filter when this hook runs", read from the binary); 22 hooks run for a Bash call (mean 89 ms each, 1.97 s if run back to back; the harness may run them concurrently, so the saving is unmeasured).

## Open questions

Written by /auto-do-todos on 2026-11-07. The next run opens with these.

- [ ] [TOOLING] Measure real wall-clock per Bash call (only the harness can: time a nested `claude -p` run with and without an `"if"` filter on the git/gh guards), then decide whether the saving justifies splitting those entries per tool. Needs a measurement run, not code.
- [ ] [TOOLING] `CLAUDE.md:60` still says "Fall back to a plain shell run only if the supervisor is unreachable", which `dev-server-guard.py` denies. CLAUDE.md is over budget and off limits tonight, so Joe reviews it with the trim; suggested replacement: "If the supervisor is unreachable, stop and tell Joe (dev-server-guard denies a raw run)."

## Landed

- c060638 dev-server-guard false denies + stale fallback texts (`refs/process-hygiene.md`, `restart-and-wait.ps1`); test `hooks/test_dev_server_guard.py`.
- 7ebd4be `_hookboot` retry in every `_hooklib` importer + docstring; test `hooks/test_hookboot.py`.
- 6959527 commit-guard heredoc / here-string / lone-apostrophe; test `hooks/test_commit_guard.py`.
- 14e6bab approve-rename Python port + anchored match, status-marker-guard removed; test `hooks/test_approve_rename.py`.
- 95cfb58 em-dash-guard scans `write_draft`; test `hooks/test_em_dash_guard.py`.
- 51aa933 testing-floor-guard "don't test" skip; test `hooks/test_testing_floor_guard.py`.
- 7e79a47 `git.exe` / `gh.exe` in push-gate, push-read-gate, pr-guard; single `is_agent_call` in `_hooklib`; tests in `test_push_gate.py`, `test_push_read_gate.py`, `test_pr_guard.py`, `test_hookboot.py`.
- Second review round follow-ups: 9a6b164 approve-rename refuses any prefix of -Command/-EncodedCommand and a bare `\r`; 770dfc5 commit-guard unparsed fallback (statement-ended assignment, quoted git.exe, key=value -c, --git-dir, env/sudo wrappers, escaped-newline and quoted-name trailers); 7be8267 dev-server-guard joins line continuations; c177709 testing-floor-guard phrase must open a clause. Known limits kept on purpose: `don't test it here, test it in CI` still reads as a dont-test, and a `Generated with Claude Code` line discussed in a heredoc subject is denied like the `-m` form already was.
- Review follow-ups (a fresh reviewer found these in the first pass): ea62650 dev-server-guard per-statement check (newline-separated launch after an install), 5ee1b90 approve-rename anchored to the real home script and refusing `(){}` / `-Command`, 8555616 commit-guard `git.exe` / quoted `-C` / `VAR=1` fallback and AI trailer inside heredoc or here-string, 4280ceb testing-floor-guard dont-test phrase must end the sentence.
