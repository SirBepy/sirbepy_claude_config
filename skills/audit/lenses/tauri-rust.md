# Lens pack: Tauri 2 (Rust backend + JS/TS webview)

Append these under the matching generic lens in `rubric-template.md`. Written from
auditing Claude Conductor (a Tauri 2 desktop app: Rust backend, vanilla-JS webview
SPA, a long-lived daemon, a remote-access HTTP server, peer federation) - the
concrete file names below are that project's, kept as a worked example of the
shape of check to run, not something to copy-paste against an unrelated repo. Swap
them for the equivalent files in Phase 2's project-specific context section.

## Architecture & code health
- A Tauri command module that both parses untrusted input and executes the
  privileged action in the same function - split the trust boundary from the
  business logic so the boundary is auditable on its own.
- A type defined once in Rust (`#[derive(Serialize)]`) and again by hand in the
  frontend TS - these drift; check whether a codegen step keeps them in sync.

## Robustness & failure modes
- **Data loss via serde defaults.** Any serde struct reachable from persisted JSON
  that lacks `#[serde(default)]` on a newer field: a present-but-incomplete
  sub-object fails the WHOLE file's deserialization, not just that field. This is
  Conductor's single most repeated real incident - check every struct in the
  persistence path, not just the ones that look new.
- A sync Tauri `#[command]` doing blocking IO on the main/UI thread - this hangs
  the whole webview, not just that call.
- A lock (`Mutex`/`RwLock`) held across an `.await` point - this is a real
  deadlock risk in async Rust, not just a style nit.
- A daemon or background process that can die mid-turn: what does the frontend
  see, does it retry, does it leave a half-applied state on disk.

## Security & trust surface
- Check a remote-transport permission table (Conductor's instance:
  `daemon/remote_transport_table.rs`) against what each exposed method actually
  does - a method added after the table was last reviewed is the common miss.
- Pairing/handshake secrets: is the comparison constant-time, does unpairing
  actually revoke access immediately or only on next reconnect.
- The hooks/MCP (or any plugin/extension) permission relay: can a decision be
  forged, replayed, or raced between the prompt and the action it gates.
- Frontend: CSP strictness, any `innerHTML` assignment with content that
  originates outside the webview's own trusted process, `escape-html` (or
  equivalent) bypasses.

## Product & UX
- A phone/remote UI (if the project has one) - does it degrade gracefully when
  the desktop app is asleep or the daemon is down, or does it hang silently.
