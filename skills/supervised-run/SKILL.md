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

Before you `start`, `restart`, or `stop` ANY entry, stop and ask first if there's reason to think
the entry IS (or spawns) software the user actively relies on for other live work - not just a
disposable dev server for something being built. This applies regardless of what `status` the
supervisor reports: `status: stopped` only means the supervisor isn't currently tracking a live
process under that id - it says NOTHING about whether starting one is safe or wanted, since the
user may be about to use it, or the underlying app may already be running outside the supervisor's
view. Incident (2026-07-16): a `cargo tauri dev` entry showing `status: stopped` was restarted to
verify a frontend change, reasoning that "stopped" meant safe - it wasn't, and the restart bounced
the user's live chats app-wide. When in doubt whether an entry is a throwaway dev server or the
user's real daily-driver app, ask before acting, don't infer safety from `status` alone.

## Tauri dev entries

- **Before `cargo build`/`cargo test` in a repo whose supervised entry runs `cargo tauri dev`:** stop the entry first (`POST /procs/<id>/stop`), run the build/test, then `POST /procs/<id>/start`. The running dev app holds a lock on `target/debug/<app>.exe`; building or testing against it while it's up fails with "failed to remove <app>.exe: Access is denied (os error 5)".
- **After any `cargo tauri dev` entry crash, before restarting:** the supervisor only kills the `tauri` CLI process, not its `beforeDevCommand` grandchild (vite/node). Check for and kill an orphan vite first, then verify the dev port (1420 by default for Tauri) is free, or the restart will crash again with "Port 1420 is already in use":
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vite' }
  ```
  Kill any matches with `Stop-Process -Id <PID> -Force`, then confirm the port is free before `POST /procs/<id>/start` or `/restart`.

## Proxy hub (upstream presets) - only when a live environment swap is actually wanted

Do not set this up by default when bringing a server up. Reach for it only when the task
explicitly wants an app to switch between backends (local / develop / prod) without a rebuild.

- **What it is.** A project can own a list of named upstream presets (`name`, `base_url`,
  `danger`), exactly one active at a time. The supervisor runs one reverse-proxy hub per
  project, bound to a FIXED loopback port (the project's port block, top slot). An app that
  bakes that one address into its API client can have its backend swapped live, by switching
  the active preset - no rebuild, no app restart.
- **Find the hub port.** There is no dedicated HTTP route for this (only IPC, dashboard-side).
  Add the project's first preset (below), then `GET /ports` and find the entry whose `owner`
  is `<project_id>:__proxyhub__` - its `port` is the hub address.
- **Define presets** (`project_id` is the same id that appears as the project half of a
  `/procs` entry's `id`, e.g. `"my-app"`):
  - List: `GET /projects/<project_id>/presets` -> `[{ id, name, base_url, danger }]`
  - Add: `POST /projects/<project_id>/presets` body `{ "name": "local", "base_url": "http://127.0.0.1:8787", "danger": false }` -> returns the created preset. The FIRST preset added for a project starts its hub listener immediately and becomes active automatically.
  - Remove: `DELETE /projects/<project_id>/presets/<preset_id>`. Removing the active preset promotes the next-first remaining one; removing the last preset stops the hub entirely.
- **Switch the active preset (live, no restart):** `POST /projects/<project_id>/presets/<preset_id>/activate`.
  Takes effect on the very next request the hub handles.
- **Read the request log:** `GET /projects/<project_id>/proxy-log` -> array of
  `{ ts, method, path, status, duration_ms, preset }` (which preset served each request),
  capped ring buffer of the last 500.
- Auth is the same bearer token as everything else here (`Authorization: Bearer <token>`).

**Limitations - read before reaching for this:**
- Websocket requests through the hub are rejected with a `501`, not proxied - every request is
  buffered and reissued, no raw byte passthrough, so anything with `Connection: Upgrade` fails.
- Scoped to unauthenticated / read-only traffic. Swapping the active preset on an app that is
  already logged in does not carry auth over - tokens/cookies belong to the old environment, so
  expect (and warn Joe to expect) a re-login after a swap.
- `danger: true` on a preset (e.g. a prod URL) only gets a visual warning in the dashboard -
  nothing backend-side blocks selecting it. It is not a safety gate.
- Doesn't help Flutter mobile out of the box: an Android emulator or physical device can't reach
  `localhost` on the host, so a hub URL baked into a mobile build won't resolve there. The
  workaround is `adb reverse tcp:<hub_port> tcp:<hub_port>` before running the app - the
  supervisor does not set that tunnel up for you.
- Useful for Flutter web / Vite / Node frontends hitting unauthenticated endpoints that need a
  live environment swap. It is not a general-purpose environment switch for authenticated flows
  or for mobile.

## Notes

- The API binds 127.0.0.1 only and the token is per-machine; never send it anywhere off-localhost.
- One-off commands never go through here - this is only for processes that stay running.
- Manage a process by the `id` from its `/run` (or `/procs`) response. Never blind-`/run` a variant when an entry already exists - reuse it.
- Endpoints verified against the running supervisor on 2026-06-06: `GET /health`, `GET /procs`, `POST /run`, and per-id `POST /procs/<id>/{start,stop,restart}`, `GET /procs/<id>/logs`, `DELETE /procs/<id>` all exist. Auth is `Authorization: Bearer <token>` on everything except `/health`. `POST /procs/<id>/reload` (flutter fast path, see Steps) exists in the same router as of the 2026-06-17 flutter daemon work.
- Proxy-hub endpoints verified against `src-tauri/src/api.rs`'s `router()` as of the 2026-07-28 hub work: `GET`/`POST /projects/:project_id/presets`, `DELETE /projects/:project_id/presets/:preset_id`, `POST /projects/:project_id/presets/:preset_id/activate`, `GET /projects/:project_id/proxy-log`. Same bearer auth as the rest of the router.
