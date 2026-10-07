<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=9, reconfirm-count=1, content-hash=93c7bcd3 -->
<!-- duplicate-checked: done/15 and done/20 cover reuse lookup and worktree-aware reuse, not peer ownership -->
# supervised-run: `ensure` silently adopts a server another session started

**Type:** skill-improvement
**Origin:** ai (mc_plugins_tag cartel session, /close 2026-10-07)

## Goal
When `sv.ps1 ensure` matches an entry that is already running, the caller can tell it did NOT start
that process, so it never stops a peer's server as its own.

## Context
2026-10-06 ~21:41 UTC, mc_plugins_tag: the Haru session had just started the 26.2 e2e server
(`gradlew.bat :testserver:runE2eServer`) and announced it on the repo channel. The cartel session
ran `sv.ps1 ensure -Project mc-plugins-tag -Cmd "gradlew.bat :testserver:runE2eServer --console=plain"`,
got `mc-plugins-tag:gradlew-3 status=running`, read that as its own fresh boot, ran its suite, then
RCON-stopped the server and `sv.ps1 rm`'d the entry, cutting the peer's test run off. The output for
"reused someone's running entry" and "started a new one" is the same one-liner.
Skill: `C:\Users\tecno\.claude\skills\supervised-run\SKILL.md` and `sv.ps1` (`ensure`).

## Approach
- `sv.ps1 ensure` prints which branch ran: `started` vs `reused-running` (and the entry's start time),
  e.g. `<id> status=running port=... action=reused-running since=<time>`.
- SKILL.md step 1 + the Stop step: on `reused-running`, treat the process as shared infra (the
  existing "call list_peers before stopping" rule applies) and never stop it unless this session
  started it.

## Acceptance
- `ensure` against an already-running matching entry prints `action=reused-running`; against a
  stopped/new one prints `action=started`.
- SKILL.md tells the caller not to stop a `reused-running` entry without a peer check.
