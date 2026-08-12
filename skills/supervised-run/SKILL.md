---
name: supervised-run
description: Use when you need to start a LONG-LIVED dev server / watcher for the current project (e.g. npm run dev, vite, next dev, flutter run, a backend that stays running). Routes through server_supervisor for visibility and no orphans. Do NOT use for one-off commands that exit (tests, builds, git, scripts); run those normally.
---

# supervised-run

Start a long-lived dev server through server_supervisor instead of spawning it in your own shell.

## When this applies

- The command is a server / watcher that STAYS RUNNING (dev server, API, file watcher).
- NOT one-off commands that exit (tests, builds, lint, git) - run those normally.

## Steps

1. **Ensure it's up - one call.** Run `sv.ps1` (next to this file) instead of re-deriving the token/health/list/reuse dance by hand:
   ```
   powershell -File "<this skill's dir>\sv.ps1" ensure -Project <folder-name> -Cmd "<cmd>" [-Kind flutter] [-Restart]
   ```
   `cmd` must have `{PORT}` templated into the actual port flag - see the Port table below for the exact flag per tool. `sv.ps1` reuses a matching entry (running: left alone, or reloaded/restarted with `-Restart`; stopped/crashed: started/restarted), or `/run`s a new one if nothing matches.
   - **Reuse is matched by project name AND absolute root** (from `projects.json`), not name alone - so a git worktree of the same project (e.g. Fibo's `frontend`/`frontend-2`/`frontend-3`) never reuses another worktree's process and serves stale code.
   - **Zero exit:** stdout is `<id> status=<status> port=<port>`. Note the `id` - you manage everything else by it.
   - **Non-zero exit:** supervisor unreachable (or a real error) -> go to Fallback.
   - **`-Root` defaults to the current shell's cwd, not to `-Project`.** If the target repo differs
     from the session's cwd (e.g. verifying a sibling project from another project's session),
     always pass `-Root "<absolute-path>"` explicitly. Incident (2026-08-11, zng-admin session):
     `ensure -Project zng-biller -Cmd "flutter run ..."` was called with no `-Root` while the shell
     was still in zng-admin's folder - it launched a second zng-admin instance
     (`zng-admin:flutter-run-4`) instead of zng-biller, caught only by `sv.ps1 ls` showing two
     `zng-admin:` entries and zero `zng-biller:` ones.

2. **On failure, clean up before you retry.** If the process is `crashed` (`sv.ps1 ls` or `sv.ps1 logs -Id <id>`):
   - Read the logs to see why.
   - **Retrying the SAME command** (e.g. a transient port clash): `sv.ps1 restart -Id <id>`. Reuses the entry, keeps its log history. Do NOT re-`ensure`/`/run`.
   - **Trying a DIFFERENT command** (different flags/port/target): `sv.ps1 rm -Id <id>` to remove the failed attempt FIRST, then `ensure` the new command. This is what prevents leaving dead variants behind.
   - (The backend also auto-prunes dead-on-arrival variants on the next successful `/run`, but delete explicitly - do not rely on it.)

3. **Report.** Tell Joe it's running, on which port, and that it's in the supervisor dashboard.

4. **Manage it afterward** via `sv.ps1`:
   - Logs: `sv.ps1 logs -Id <id>`
   - Stop: `sv.ps1 stop -Id <id>`
   - Restart: `sv.ps1 restart -Id <id>` (full process respawn - use for non-flutter entries, or a flutter entry whose daemon isn't ready)
   - Reload (flutter only, fast path - no `sv.ps1` subcommand yet, raw API): `POST /procs/<id>/reload` with header `Authorization: Bearer <token>` - hot-restarts via the flutter daemon instead of respawning the process; for a `web-server` target this also auto-refreshes every open browser tab on the live-reload proxy port (see Port table). Prefer this over `/restart` for any flutter entry - `ensure -Restart` already does this automatically.
   - Delete (remove the entry entirely): `sv.ps1 rm -Id <id>` (stop it first if running)
   - List everything: `sv.ps1 ls`

## Wait for readiness before using it

A just-started or just-restarted entry is running but may still be mid cold-boot. Poll
`sv.ps1 logs -Id <id>` for a readiness marker in a `run_in_background` + bash `until` loop
(per this harness's own "wait for a condition" guidance) instead of blocking synchronously or
guessing a fixed sleep:

```bash
until powershell -File "<dir>\sv.ps1" logs -Id <id> | grep -q "<marker>"; do sleep 2; done
```

Known markers (not exhaustive):
- NestJS: `Nest application successfully started`
- Flutter web / chrome / mobile: see the readiness cell per target in the Port table below - the
  `-d web-server` and `-d chrome`/mobile markers are different lines and NEVER share a grep pattern.
- Generic Node dev servers: whatever "ready"/"listening on port" line the tool prints.

A genuinely large Flutter web app's first cold DDC compile can still take 1-3+ minutes after its
readiness marker appears - a blank first page load isn't necessarily broken; give it up to
~60-90s before concluding something's wrong.

## Port table (do this in step 1)

For a dynamic port to take effect, template the port flag INTO the command with the literal `{PORT}` placeholder. The supervisor substitutes it AND sets the `PORT` env var.

| Tool | `cmd` to send |
| --- | --- |
| Vite | `vite --port {PORT}` (or `npm run dev -- --port {PORT}`) |
| Next.js | `next dev -p {PORT}` |
| Flutter web (auto-reload) | `flutter run -d web-server --web-port {PORT}` - after editing source, call `POST /procs/<id>/reload` (not `/restart`) to hot-restart via the daemon; the supervisor's live-reload proxy then refreshes every open tab on its own, no manual F5. Readiness: `[flutter] app started` / `[flutter] serving at http://localhost:<port>` - this target NEVER prints `Debug service listening` (that needs the Dart Debug Chrome extension), so a loop grepping for it hangs forever even after a healthy compile |
| Flutter web (chrome) | `flutter run -d chrome --web-port {PORT}` - flutter owns its chrome; no supervisor proxy, no auto-refresh. Readiness: `Debug service listening on ws://` (or `A Dart VM Service`) - `app started` fires first but mid-DDC-compile, so wait for the debug-service line specifically |
| Node server reading `process.env.PORT` | no `{PORT}` needed - the env var is set automatically |
| Tool with no port flag you can find | send `"use_dynamic_port": false` and accept its built-in port |

**Proxy port vs raw port (Flutter web auto-reload only):** the port you pass in `cmd` (`--web-port {PORT}`) is the RAW flutter port. The supervisor fronts it with a SEPARATE live-reload proxy on a DIFFERENT port - check `GET /procs/<id>/logs` for the line `[supervisor] live-reload proxy on 127.0.0.1:<proxyPort> -> flutter :<rawPort>` and point any browser/script at `<proxyPort>`, not `<rawPort>`. Hitting the raw port directly can cause DWDS/DDC reconnect stalls - a script or browser tab hangs indefinitely waiting for the app to finish mounting, no error, that looks like a slow cold compile but isn't fixed by waiting longer. Only switching to the proxy port fixes it reliably (restarting the process can appear to fix it once, then recur).

### Worked example (Vite project)

```http
POST http://127.0.0.1:<port>/run
Authorization: Bearer <token>
Content-Type: application/json

{ "root": "C:\\Users\\joe\\Projects\\my-app", "cmd": "npm run dev -- --port {PORT}", "kind": "generic", "use_dynamic_port": true }
```
Response: `{ "id": "my-app:dev", "project": "my-app", "port": 42013, "status": "running", ... }` -> the app is on http://127.0.0.1:42013.

## Fallback (supervisor not reachable)

Run the server the normal way (in your own background shell), and tell Joe: "server_supervisor isn't running, so I ran <cmd> directly." Never block on the supervisor being up. Do NOT try to launch the supervisor app yourself.

## Daily-driver apps - ask before touching

Before you `start`, `restart`, or `stop` ANY entry, ask first if it might be software Joe
actively relies on for other live work, not just a disposable dev server. `status: stopped`
does NOT mean safe - it only means the supervisor isn't tracking a live process under that id,
not that starting/stopping one won't disrupt something already running outside its view.

## Tauri dev entries

See `tauri.md` (next to this file) before `cargo build`/`cargo test` or a crash-restart in a repo
whose supervised entry runs `cargo tauri dev` - both have entry-locking / orphan-process gotchas.

## Proxy hub (upstream presets)

See `proxy-hub.md` (next to this file) - only needed when a task explicitly wants an app to swap
backends (local / develop / prod) live, without a rebuild.

## Notes

- The API binds 127.0.0.1 only and the token is per-machine; never send it anywhere off-localhost.
- One-off commands never go through here - this is only for processes that stay running.
- Manage a process by the `id` from its `/run` (or `/procs`) response. Never blind-`/run` a variant when an entry already exists - reuse it.
