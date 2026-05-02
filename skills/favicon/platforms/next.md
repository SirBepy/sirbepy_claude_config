# Favicon - Next.js

## App Router (next.config.* + `app/` directory)

Next.js App Router auto-detects favicon files placed directly in the `app/` directory. No `<link>` tags needed.

### Canonical paths

| File | Path |
|---|---|
| `favicon.svg` | `public/favicon.svg` (served at `/favicon.svg`) |
| `favicon.png` | `public/favicon.png` (served at `/favicon.png`) |
| `favicon.ico` | `app/favicon.ico` (auto-detected by Next.js) |

### HTML entry point

None - App Router handles this automatically via `app/favicon.ico` convention.

Optionally add to `app/layout.tsx` for SVG support:

```tsx
export const metadata = {
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/favicon.png', type: 'image/png' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
  },
}
```

## Pages Router (`pages/` directory, no `app/`)

### Canonical paths

| File | Path |
|---|---|
| `favicon.svg` | `public/favicon.svg` |
| `favicon.png` | `public/favicon.png` |
| `favicon.ico` | `public/favicon.ico` |

### HTML entry point

Update `pages/_document.tsx` (or `_document.js`). Add to `<Head>`:

```tsx
<link rel="icon" type="image/x-icon" href="/favicon.ico" />
<link rel="icon" type="image/png" href="/favicon.png" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

## Extras

None.
