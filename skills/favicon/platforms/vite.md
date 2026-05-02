# Favicon - Vite

## Canonical paths

| File | Path |
|---|---|
| `favicon.svg` | `public/favicon.svg` |
| `favicon.png` | `public/favicon.png` |
| `favicon.ico` | `public/favicon.ico` |

## HTML entry point

Update `index.html` (project root). Ensure these tags exist inside `<head>`:

```html
<link rel="icon" type="image/x-icon" href="/favicon.ico" />
<link rel="icon" type="image/png" href="/favicon.png" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

Note: Vite serves `public/` at `/`, so hrefs use `/filename` not `public/filename`.

## Extras

None.
