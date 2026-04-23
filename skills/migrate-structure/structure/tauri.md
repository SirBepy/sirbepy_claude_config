# Tauri Project Structure Spec

## Setup

Tauri 2 app with Rust backend and vanilla TypeScript frontend. Bundler: **Vite**. Templating: **lit-html**. Styling: **plain `.css` files per feature**. Rust→TS types: **ts-rs**.

## Folder structure

```
project-root/
├── src-tauri/                     # ALL Rust
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs
│   │   ├── state.rs
│   │   ├── <domain>.rs            # re-exports submodule
│   │   ├── <domain>/              # per-domain folder
│   │   │   └── *.rs
│   │   ├── ipc.rs
│   │   ├── ipc/
│   │   │   └── <domain>.rs        # one file per IPC command group
│   │   └── types/
│   │       └── <domain>.rs        # one file per domain's shared types
│   ├── Cargo.toml
│   ├── build.rs
│   ├── tauri.conf.json
│   ├── capabilities/
│   ├── icons/
│   ├── assets/
│   └── binaries/
├── src/                           # Frontend source
│   ├── index.html                 # thin shell
│   ├── main.ts                    # bootstrap + router mount
│   ├── router.ts
│   ├── shared/
│   │   ├── ipc.ts
│   │   ├── formatters.ts
│   │   ├── modal.ts
│   │   ├── toast.ts
│   │   └── events.ts
│   ├── components/
│   │   └── <component>/
│   │       ├── <component>.ts
│   │       └── <component>.css
│   ├── views/
│   │   └── <view>/
│   │       ├── <view>.ts
│   │       ├── <view>.css
│   │       └── subviews/          # only if the view has nested routes
│   │           └── <subview>/
│   │               ├── <subview>.ts
│   │               └── <subview>.css
│   ├── styles/
│   │   ├── tokens.css
│   │   ├── base.css
│   │   └── themes.css
│   └── types/
│       ├── ipc.generated.ts       # emitted by ts-rs, gitignored
│       └── dom.d.ts
├── dist/                          # build output, gitignored
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .gitignore
```

## File placement

| File type | Move to |
| --- | --- |
| Main Rust entry | `src-tauri/src/main.rs` |
| Library root (module declarations) | `src-tauri/src/lib.rs` |
| Shared `AppState` | `src-tauri/src/state.rs` |
| Domain Rust code | `src-tauri/src/<domain>/*.rs` (with `<domain>.rs` re-export at root) |
| IPC command handlers | `src-tauri/src/ipc/<domain>.rs` |
| Shared types that cross IPC | `src-tauri/src/types/<domain>.rs` |
| Cargo manifest | `src-tauri/Cargo.toml` |
| Tauri config | `src-tauri/tauri.conf.json` |
| Build script | `src-tauri/build.rs` |
| Tauri capabilities | `src-tauri/capabilities/` |
| Tauri icons | `src-tauri/icons/` |
| Bundled assets / fonts / sounds | `src-tauri/assets/` |
| Sidecar binaries | `src-tauri/binaries/` |
| HTML shell | `src/index.html` (ONE file; no per-view HTML) |
| Bootstrap / router | `src/main.ts`, `src/router.ts` |
| View logic + template | `src/views/<view>/<view>.ts` |
| View styles | `src/views/<view>/<view>.css` |
| Subview logic + styles | `src/views/<view>/subviews/<subview>/<subview>.{ts,css}` |
| Reusable widget logic + template | `src/components/<component>/<component>.ts` |
| Reusable widget styles | `src/components/<component>/<component>.css` |
| Cross-view utilities | `src/shared/*.ts` |
| Global CSS (reset, themes, custom properties) | `src/styles/*.css` |
| TS types (hand-written) | `src/types/*.ts` |
| Generated TS types (ts-rs) | `src/types/ipc.generated.ts` (gitignored) |
| Frontend build output | `dist/` (gitignored) |
| Root config | `package.json`, `tsconfig.json`, `vite.config.ts` at project root |

## Process boundaries

- **Rust (`src-tauri/`)**: single binary. Owns tray, scheduling, IPC, native APIs. No `.ts` or web assets live here.
- **Frontend (`src/`)**: runs in the Tauri WebView. No Node APIs, no direct file-system access. All privileged work goes through typed `invoke()` calls to Rust IPC commands.

## Rust module rules

- **Group by domain, not by layer.** No `handlers/`, `models/`, `services/` folders. Folder names match bounded contexts (`auth/`, `tray/`, `hooks/`, `tokens/`, `channels/`, `settings/`, `notifications/`, `ipc/`).
- **Use the 2018-style module layout**: a sibling `.rs` file per folder (e.g. `auth.rs` + `auth/`), not `mod.rs`.
- **Any file past ~300 lines should split into a subfolder.**
- **`ipc.rs` only re-exports.** Commands live in `ipc/<domain>.rs`.
- **`types/*` holds only structs that cross the IPC boundary.** Internal-only types live inside the domain module that owns them.

## Frontend view pattern

Every view is one folder with one `.ts` + one `.css`. The `.ts` exports a render function; templates live inline as lit-html tagged templates; the `.css` is imported as a Vite side-effect:

```ts
// src/views/<view>/<view>.ts
import { html, render } from "lit-html";
import "./<view>.css";

export function render<View>(root: HTMLElement) {
  render(html`<div class="view-body">...</div>`, root);
}
```

Rules:
- **One view per folder.** No shared filenames between views.
- **Templates inline via lit-html.** No per-view `.html` partials.
- **Static chrome in `src/index.html`.** That file stays minimal: meta tags, `<div id="app"></div>`, module script, Phosphor Icons CDN.
- **Sub-components in the same folder.** If a view's `.ts` passes ~300 lines, extract pieces into `src/views/<view>/components/<piece>/`.
- **Promote to top-level `src/components/`** only when 2+ views use the same widget.

## Styling rules

- **Plain `.css` files per feature.** Imported from the feature's `.ts` via `import "./feature.css"`.
- **Globals only in `src/styles/`.** `base.css` (reset + typography), `themes.css` (`[data-theme="x"] { --bg: ... }`), `tokens.css` (design tokens as CSS custom properties).
- **No CSS-in-JS.** No goober, no styled-components, no vanilla-extract, no LitElement `css` tag. Plain CSS is the AI-friendliest, smallest-token-cost-per-edit option.
- **Themes are CSS custom properties.** Components reference `var(--primary)`, never hex literals.

## Shared utilities

- **One formatter per concept.** One `formatTokens`, one `formatTimeAgo`, one `formatBytes`. All in `src/shared/formatters.ts`. Never duplicate across views.
- **Generic modal host in `src/shared/modal.ts`.** Every modal uses it; no bespoke modal implementations.
- **Typed IPC wrapper in `src/shared/ipc.ts`.** Wraps `@tauri-apps/api`'s `invoke` with generated type aliases from `src/types/ipc.generated.ts`.

## Rust→TS type generation

- Every struct that crosses IPC: `#[derive(ts_rs::TS)]` + `#[ts(export)]`.
- A dedicated test target (e.g. `src-tauri/tests/export_types.rs`) forces emission.
- An npm `prebuild` script runs `cargo test --test export_types` so `src/types/ipc.generated.ts` always exists before `vite build`.
- The generated file is gitignored.

## Never move

- `src-tauri/Cargo.toml`
- `src-tauri/Cargo.lock`
- `src-tauri/tauri.conf.json`
- `src-tauri/build.rs`
- `src-tauri/icons/`
- `src-tauri/capabilities/`
- `src-tauri/binaries/`
- `package.json`
- `tsconfig.json`
- `vite.config.ts`
- Anything in `.github/`
- `README.md`, `CLAUDE.md`, `LICENSE`

## Unknown files

Any file that doesn't match a rule above: list it in the summary, do not move it.

## Detection

A project is a Tauri project if any of the following is true:

- A folder named `src-tauri/` exists at the project root.
- A `tauri.conf.json` file exists anywhere in the repo.
- `Cargo.toml` at the project root (or at `src-tauri/Cargo.toml`) depends on a crate named `tauri`.
