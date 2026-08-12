# Proxy hub (upstream presets)

Only when a live environment swap is actually wanted - do not set this up by default when
bringing a server up. Reach for it only when the task explicitly wants an app to switch between
backends (local / develop / prod) without a rebuild.

- **What it is.** A project can own a list of named upstream presets (`name`, `base_url`,
  `danger`), exactly one active at a time. The supervisor runs one reverse-proxy hub per
  project, bound to a FIXED loopback port (the project's port block, top slot). An app that
  bakes that one address into its API client can have its backend swapped live, by switching
  the active preset - no rebuild, no app restart.
- **Find the hub port.** `GET /projects/<project_id>/hub-port` (same bearer token as everything
  else here) returns the raw port as a bare JSON number (e.g. `42013`), not an object. 404 with
  a plain-text body means either an unknown project or one with no presets configured yet - that
  is the "no hub" case, not a transport error. Requires server_supervisor v0.1.34+.
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

## Limitations - read before reaching for this

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
