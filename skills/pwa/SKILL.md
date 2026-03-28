---
name: pwa
description: Triggers on /pwa only.
---

# /pwa

> Set up Progressive Web App support for the project.

## Step 1 - Gather context

Read the following to fill manifest fields:

- `CLAUDE.md` - project type and name
- `.portfolio-data/metadata.json` - title, shortDescription
- `assets/images/favicon.png` and `favicon.ico` - for icons

## Step 2 - Generate manifest.json

Create `manifest.json` in the project root:

```json
{
  "name": "",
  "short_name": "",
  "description": "",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#16151f",
  "theme_color": "#9d7dfc",
  "icons": [
    {
      "src": "assets/images/favicon.png",
      "sizes": "256x256",
      "type": "image/png"
    },
    {
      "src": "assets/images/favicon.svg",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ]
}
```

Fill fields from gathered context:

- `name` - full project title
- `short_name` - max 12 chars, used on home screen
- `description` - from shortDescription in metadata.json or inferred
- `background_color` and `theme_color` - use void theme defaults above, user can update later

Only include SVG icon entry if `assets/images/favicon.svg` exists.

## Step 3 - Generate service worker

Create `sw.js` in the project root:

```javascript
const CACHE_NAME = "v1";
const ASSETS = [
  "/",
  "/index.html",
  "/src/styles/style.css",
  "/src/scripts/script.js",
  "/assets/images/favicon.png",
  "/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request)),
  );
});
```

Replace the ASSETS list with the actual files that exist in the project.

## Step 4 - Update index.html

Add inside `<head>` if missing:

```html
<link rel="manifest" href="manifest.json" />
<meta name="theme-color" content="#9d7dfc" />
```

Add before `</body>` if missing:

```html
<script>
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
  }
</script>
```

## Step 5 - Confirm

Tell the user what was created and remind them:

- `theme_color` and `background_color` in `manifest.json` can be updated to match their preferred theme
- The service worker caches files at install time - run `/pwa` again if the file list changes significantly
- PWA install prompt will appear in supported browsers once deployed to GitHub Pages

Do not commit - the user handles that.
