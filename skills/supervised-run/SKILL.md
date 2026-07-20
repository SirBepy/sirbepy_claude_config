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

1. **Discover the API.** Read the data dir `%APPDATA%\com.sirbepy.server-supervisor\supervisor\`:
   - token = contents of `api_token.txt`
   - port = contents of `api_port.txt`
   If either file is missing, treat the supervisor as not running -> go to Fallback.

2. **Probe health.** `GET http://127.0.0.1:<port>/health` (no auth). If it does not return 200 -> go to Fallback.

3. **List first - reuse before you create.** `GET http://127.0.0.1:<port>/procs` (header `Authorization: Bearer <token>`). Look for an existing entry whose `project` equals the current project folder's name AND whose `name`/command is the server you want.
   - **If a matching entry exists:** do NOT `/run` a new one. Reuse it by id:
     - status `running` and you just want it up: leave it, or pick up code changes with `POST /procs/<id>/restart` - **except for a flutter entry**, where `POST /procs/<id>/reload` is the fast path: it hot-restarts via the flutter daemon instead of a full process respawn, and auto-falls back to `/restart` on its own if the daemon isn't ready yet. Always prefer `/reload` over `/restart` for flutter.
     - status `stopped` or `crashed`: `POST /procs/<id>/start` (or `/restart`).
   - **Only if nothing matches** do you go to step 4. This is what stops the same project from collecting `flutter run` three times.

4. **Run it (first launch only).** `POST /run` with header `Authorization: Bearer <token>` and JSON body:
   ```json
   { "root": "<absolute path of the current project folder>", "cmd": "<the server command>", "kind": "generic", "use_dynamic_port": true }
   ```
   - Set `"kind": "flutter"` only for `flutter run` commands; otherwise `"generic"`.
   - **Set the port** - see the Port table below. This is the step AIs most often get wrong.
   - The response is the started process's info: `{ id, project, name, kind, status, pid, port, mem_bytes }`. Note the `id` (form: `<project>:<name>`) - you manage everything else by it.

5. **On failure, clean up before you retry.** If the started process is `crashed` (check `GET /procs` or `GET /procs/<id>/logs`):
   - Read `GET /procs/<id>/logs` to see why.
   - **Retrying the SAME command** (e.g. it was a transient port clash): `POST /procs/<id>/restart`. Reuses the entry, keeps its log history. Do NOT `/run` again.
   - **Trying a DIFFERENT command** (different flags/port/target): `DELETE /procs/<id>` to remove the failed attempt FIRST, then `/run` the new command. This is what prevents leaving dead variants behind.
   - (The backend also auto-prunes dead-on-arrival variants on the next successful `/run`, but delete explicitly - do not rely on it.)

6. **Report.** Tell Joe it's running, on which port, and that it's in the supervisor dashboard.

7. **Manage it afterward** via the same base URL + bearer token:
   - Logs: `GET /procs/<id>/logs`
   - Stop: `POST /procs/<id>/stop`
   - Restart: `POST /procs/<id>/restart` (full process respawn - use for non-flutter entries, or a flutter entry whose daemon isn't ready)
   - Reload (flutter only, fast path): `POST /procs/<id>/reload` - hot-restarts via the flutter daemon instead of respawning the process; for a `web-server` target this also auto-refreshes every open browser tab on the live-reload proxy port (see Port table). Prefer this over `/restart` for any flutter entry.
   - Delete (remove the entry entirely): `DELETE /procs/<id>` (stop it first if running)
   - List everything: `GET /procs`

## Port table (do this in step 4)

For a dynamic port to take effect, template the port flag INTO the command with the literal `{PORT}` placeholder. The supervisor substitutes it AND sets the `PORT` env var.

| Tool | `cmd` to send |
| --- | --- |
| Vite | `vite --port {PORT}` (or `npm run dev -- --port {PORT}`) |
| Next.js | `next dev -p {PORT}` |
| Flutter web (auto-reload) | `flutter run -d web-server --web-port {PORT}` - after editing source, call `POST /procs/<id>/reload` (not `/restart`) to hot-restart via the daemon; the supervisor's live-reload proxy then refreshes every open tab on its own, no manual F5 |
| Flutter web (chrome) | `flutter run -d chrome --web-port {PORT}` - flutter owns its chrome; no supervisor proxy, no auto-refresh |
| Node server reading `process.env.PORT` | no `{PORT}` needed - the env var is set automatically |
| Tool with no port flag you can find | send `"use_dynamic_port": false` and accept its built-in port |

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

## Tauri dev entries

- **Before `cargo build`/`cargo test` in a repo whose supervised entry runs `cargo tauri dev`:** stop the entry first (`POST /procs/<id>/stop`), run the build/test, then `POST /procs/<id>/start`. The running dev app holds a lock on `target/debug/<app>.exe`; building or testing against it while it's up fails with "failed to remove <app>.exe: Access is denied (os error 5)".
- **After any `cargo tauri dev` entry crash, before restarting:** the supervisor only kills the `tauri` CLI process, not its `beforeDevCommand` grandchild (vite/node). Check for and kill an orphan vite first, then verify the dev port (1420 by default for Tauri) is free, or the restart will crash again with "Port 1420 is already in use":
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vite' }
  ```
  Kill any matches with `Stop-Process -Id <PID> -Force`, then confirm the port is free before `POST /procs/<id>/start` or `/restart`.

## Notes

- The API binds 127.0.0.1 only and the token is per-machine; never send it anywhere off-localhost.
- One-off commands never go through here - this is only for processes that stay running.
- Manage a process by the `id` from its `/run` (or `/procs`) response. Never blind-`/run` a variant when an entry already exists - reuse it.
- Endpoints verified against the running supervisor on 2026-06-06: `GET /health`, `GET /procs`, `POST /run`, and per-id `POST /procs/<id>/{start,stop,restart}`, `GET /procs/<id>/logs`, `DELETE /procs/<id>` all exist. Auth is `Authorization: Bearer <token>` on everything except `/health`. `POST /procs/<id>/reload` (flutter fast path, see Steps) exists in the same router as of the 2026-06-17 flutter daemon work.
