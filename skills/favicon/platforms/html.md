# Favicon - Plain HTML

## Canonical paths

| File | Path |
|---|---|
| `favicon.svg` | `assets/images/favicon.svg` |
| `favicon.png` | `assets/images/favicon.png` |
| `favicon.ico` | `favicon.ico` (project root) |

## HTML entry point

Update `index.html`. Ensure these tags exist inside `<head>`:

```html
<link rel="icon" type="image/x-icon" href="favicon.ico" />
<link rel="icon" type="image/png" href="assets/images/favicon.png" />
<link rel="icon" type="image/svg+xml" href="assets/images/favicon.svg" />
```

## Extras

None.
