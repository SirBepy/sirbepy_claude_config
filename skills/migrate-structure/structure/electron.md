# Electron Project Structure Spec

## Setup

No bundler, no build step. Plain HTML/JS loaded directly via `loadFile()`. Packaged with `electron-builder`.

## Folder structure

```
project-root/
├── main.js
├── preload.js
├── package.json
├── src/
│   ├── renderer/
│   │   ├── PageName/
│   │   │   ├── PageName.html
│   │   │   └── PageName.js
│   │   └── styles/
│   │       ├── styles.css
│   │       └── base.css
│   ├── ipc/
│   │   └── domain.js
│   └── utils/
└── assets/
```

## File placement

| File type | Move to |
| --- | --- |
| Main process entry | `main.js` (project root) |
| Preload script | `preload.js` (project root) |
| Renderer HTML | `src/renderer/PageName/PageName.html` |
| Renderer JS | `src/renderer/PageName/PageName.js` |
| CSS main entry | `src/renderer/styles/styles.css` |
| CSS base/reset | `src/renderer/styles/base.css` |
| IPC handlers | `src/ipc/domain.js` (one file per domain) |
| Shared utilities | `src/utils/` |
| Images/fonts | `assets/` |

## Process boundaries

- `main.js` - Electron main process. Creates windows, registers IPC handlers, manages app lifecycle.
- `preload.js` - Runs in a sandboxed Node.js context. Bridges main and renderer via `contextBridge`. Lives at root, not inside renderer.
- `src/renderer/` - Pure browser context. No Node.js APIs. No direct IPC - must go through preload.

## Renderer pages

Each window/page gets its own subfolder:

```
src/renderer/dashboard/
├── dashboard.html
└── dashboard.js

src/renderer/settings/
├── settings.html
└── settings.js
```

## IPC structure

Handlers live in `src/ipc/`, split by domain. Each file registers its own `ipcMain.handle()` calls and is imported in `main.js`:

```
src/ipc/data.js
src/ipc/window.js
src/ipc/auth.js
```

## CSS structure

- `styles.css` is the main entry - import it in HTML with `<link>`
- `base.css` holds resets and variables
- No preprocessing, no SCSS - plain CSS only

## Never move

- `main.js`
- `preload.js`
- `package.json`
- `electron-builder.yml` or any electron-builder config
- Anything in `.github/`

## Unknown files

Any file that doesn't match a rule above: list it in the summary, do not move it.
