# Favicon - React (CRA / Vite + React)

## Canonical paths

| File | Path |
|---|---|
| `favicon.svg` | `public/favicon.svg` |
| `favicon.png` | `public/favicon.png` |
| `favicon.ico` | `public/favicon.ico` |

## HTML entry point

Update `public/index.html` (CRA) or `index.html` (Vite + React). Ensure these tags exist inside `<head>`:

```html
<link rel="icon" type="image/x-icon" href="%PUBLIC_URL%/favicon.ico" />
<link rel="icon" type="image/png" href="%PUBLIC_URL%/favicon.png" />
<link rel="icon" type="image/svg+xml" href="%PUBLIC_URL%/favicon.svg" />
```

For Vite + React, use `/favicon.ico` etc. (no `%PUBLIC_URL%`).

## Extras

None.
