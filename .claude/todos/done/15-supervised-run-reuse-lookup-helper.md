<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=f2ac7c85 -->
# /supervised-run: collapse the token/health/list/reuse dance into one step

**Type:** skill-improvement

## Goal

Cut the four-call boilerplate every `/supervised-run` invocation pays before it can
reuse an already-running server, so the skill costs one tool call instead of four.

## Context

Skill file: `C:/Users/tecno/.claude-fibo/skills/supervised-run/SKILL.md`, steps 1-3.

Every session that touches a dev server repeats the same mechanical sequence by hand:

1. `cat $APPDATA/com.sirbepy.server-supervisor/supervisor/api_port.txt`
2. `cat .../api_token.txt`
3. `curl 127.0.0.1:<port>/health`
4. `curl -H "Authorization: Bearer <token>" 127.0.0.1:<port>/procs` -> scan JSON for a
   matching `project` + `name` -> `POST /procs/<id>/restart`

On 2026-07-10 (docs-site session) this was 4 calls just to discover that
`docs-site:http-server` was already running on 8091 and restart it. Same dance appeared
in the `fibo-backend2-local-run` and `playwright-cdp-supervised-dev-server` sessions.
It is pure ceremony: the inputs are always the same two files and the same base URL.

## Approach

Add a small helper script next to the skill, e.g.
`C:/Users/tecno/.claude-fibo/skills/supervised-run/sv.ps1`, that reads the token+port
itself and exposes verb subcommands:

- `sv.ps1 ls` — health-check + print `/procs` as a compact table (id, status, port)
- `sv.ps1 ensure -Project <name> -Cmd "<cmd>" [-Root <path>]` — the whole decision tree:
  reuse a matching running entry, `start` it if stopped/crashed, `restart` if `-Restart`
  is passed, else `POST /run`. Prints the resulting id + port.
- `sv.ps1 logs|stop|restart|rm -Id <id>`

Then rewrite SKILL.md steps 1-4 to "run `sv.ps1 ensure ...`; on non-zero exit, fall back
to a plain shell run and tell Joe the supervisor isn't reachable." Keep the Port table
(the `{PORT}` templating rule) and the Tauri notes — those are real judgment, not ceremony.

Guard: the script must never print the bearer token, and must bind only to 127.0.0.1.

## Acceptance

`/supervised-run <cmd>` reaches a running, correctly-reused server in ONE tool call for
the common case. `sv.ps1 ensure` is idempotent: run twice against the same project and no
duplicate `/procs` entry appears. Fallback path still works with the supervisor stopped.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 82; renumbered to 15 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: implemented `skills/supervised-run/sv.ps1` (ls/ensure/logs/stop/restart/rm) and rewrote SKILL.md steps 1-4 to call `sv.ps1 ensure` with a non-zero-exit fallback; folded in todo 20's root-aware reuse in the same `ensure` decision tree.
