# Favicon - Tauri

Tauri has two separate icon concerns: web favicon (frontend) and native app icon (`src-tauri/icons/`). Handle both.

## Step A - Web favicon

Detect the frontend framework inside the Tauri project (usually Vite or React). Read the matching platform spec and apply it normally for the web favicon.

## Step B - Native app icons

Tauri generates its full native icon set from a single source image via the CLI.

### Source image

Use the canonical PNG generated in Step A (e.g. `public/favicon.png`). It must be at least 1024x1024 for best results. If the source PNG is 256px, warn the user that a higher-res source would give better native icons.

### Generate

```
npx tauri icon <source-png-path>
```

This overwrites everything in `src-tauri/icons/` automatically - `.icns`, `.ico`, multiple PNG sizes.

### Canonical paths

| File | Path |
|---|---|
| Web SVG | per frontend spec (e.g. `public/favicon.svg`) |
| Web PNG | per frontend spec (e.g. `public/favicon.png`) |
| Web ICO | per frontend spec (e.g. `public/favicon.ico`) |
| Native icons | `src-tauri/icons/` (managed by `tauri icon` command) |

## HTML entry point

Per the frontend spec (Vite, React, etc.).

## Extras

After running `npx tauri icon`, confirm that `src-tauri/icons/` was populated. List the generated files.
