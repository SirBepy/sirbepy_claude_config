---
name: supervised-run
description: Use when you need to start a LONG-LIVED dev server / watcher for the current project (e.g. npm run dev, vite, next dev, flutter run, a backend that stays running). Routes it through the local server_supervisor app so it is visible in Joe's dashboard, owned (no orphans), and centrally logged - auto-registering it if needed. Do NOT use for one-off commands that exit (tests, builds, git, scripts); run those normally. Falls back to a normal shell run if the supervisor is not reachable.
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
   If either file is missing, treat the supervisor as not running → go to Fallback.

2. **Probe health.** `GET http://127.0.0.1:<port>/health` (no auth). If it does not return 200 (connection refused, timeout, missing) → go to Fallback.

3. **Run it.** `POST http://127.0.0.1:<port>/run` with header `Authorization: Bearer <token>` and JSON body:
   ```json
   { "root": "<absolute path of the current project folder>", "cmd": "<the server command>", "kind": "generic", "use_dynamic_port": true }
   ```
   - Set `"kind": "flutter"` only for `flutter run` commands; otherwise `"generic"`.
   - For the dynamic port to actually take effect, template the port flag INTO the command where the tool supports one, using the literal `{PORT}` placeholder (the supervisor substitutes it and also sets the `PORT` env var):
     - Vite: `vite --port {PORT}` (or `npm run dev -- --port {PORT}`)
     - Next: `next dev -p {PORT}`
     - Flutter web: `flutter run -d chrome --web-port {PORT}`
     - Node servers reading `process.env.PORT`: no `{PORT}` needed; the env var is set automatically.
     - If you cannot make the tool honor a port, send `"use_dynamic_port": false` and accept its built-in port.
   - The response is the started process's info: `{ id, project, name, kind, status, pid, port }`.

4. **Report.** Tell Joe it's running, on which port, and that it's in the supervisor dashboard. Calling `/run` again with the same root+cmd is safe - it reuses the same entry and restarts it (no duplicates).

5. **Manage it afterward** via the same base URL + bearer token:
   - Logs: `GET /procs/<id>/logs`
   - Stop: `POST /procs/<id>/stop`
   - Restart: `POST /procs/<id>/restart`
   - List everything running: `GET /procs`

## Fallback (supervisor not reachable)

Run the server the normal way (in your own background shell), and tell Joe: "server_supervisor isn't running, so I ran <cmd> directly." Never block on the supervisor being up. Do NOT try to launch the supervisor app yourself.

## Notes

- The API binds 127.0.0.1 only and the token is per-machine; never send it anywhere off-localhost.
- One-off commands never go through here - this is only for processes that stay running.
