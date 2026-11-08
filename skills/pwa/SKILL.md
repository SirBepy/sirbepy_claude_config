---
name: pwa
description: Sets up Progressive Web App support, skipping stacks with their own PWA plugin. Step in /bepy-project-setup-web.
---

# /pwa

> Set up Progressive Web App support for the project.

## Step 0 - Skip for Tauri / desktop projects

If `src-tauri/` exists or `CLAUDE.md` lists `Type: tauri`, print:

```
/pwa - skipped, Tauri desktop apps don't use PWA.
```

And stop.

## Step 0b - Skip for bundler-based projects

If `vite.config.ts`, `vite.config.js`, `next.config.js`, `next.config.ts`, or an equivalent
bundler/framework config exists in the project root, this skill's hand-rolled `manifest.json` +
`sw.js` template will conflict with that stack's own PWA plugin ecosystem (no asset-hashing
awareness, wrong `public/` conventions). Don't generate it. Instead:

1. Check sibling packages in the same repo for an existing working PWA setup (e.g. `vite-plugin-pwa`
   or `next-pwa`/`@ducanh2912/next-pwa` in a sibling `package.json`). If found, print:

```
/pwa - this is a <Vite/Next.js> project. Skipping the static-site template.
<sibling package> already has a working PWA setup via <plugin> - mirror its config in
<vite.config.ts/next.config.js> rather than starting from scratch.
```

2. If no sibling setup exists, print:

```
/pwa - this is a <Vite/Next.js> project. Skipping the static-site template - use
<vite-plugin-pwa/next-pwa> instead, the idiomatic tool for this stack.
```

And stop either way.

## Step 1 - Check if already done

If the user passed `skipVerification`, skip this step entirely and proceed to Step 2.

If `manifest.json` exists, `sw.js` exists, and `index.html` contains the manifest link + service worker registration script, print:

```
/pwa - already complete, skipping.
```

And stop.

## Step 2 - Gather context

Read the following to fill manifest fields:

- `CLAUDE.md` - project type and name
- `.portfolio-data/metadata.json` - title, shortDescription
- `assets/images/favicon.png` and `favicon.ico` - for icons

## Step 3 - Generate manifest.json

Create `manifest.json` in the project root:

```json
{
  "name": "",
  "short_name": "",
  "description": "",
  "start_url": "./",
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

## Step 4 - Generate service worker

Create `sw.js` in the project root:

```javascript
// Fixed name on purpose: pages are network-first and assets revalidate on every load, so a deploy
// reaches returning users without bumping this. Change it only to purge every cache.
const CACHE_NAME = "static";
const ASSETS = [
  "./",
  "./index.html",
  "./src/styles/style.css",
  "./src/scripts/script.js",
  "./assets/images/favicon.png",
  "./manifest.json",
];

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => Promise.allSettled(ASSETS.map((asset) => cache.add(asset)))),
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const put = (res) => {
    if (res.ok) {
      const copy = res.clone();
      caches.open(CACHE_NAME).then((c) => c.put(e.request, copy));
    }
    return res;
  };
  if (e.request.mode === "navigate") {
    // Network-first: the HTML is the entry point to every other file.
    e.respondWith(fetch(e.request).then(put).catch(() => caches.match(e.request).then((c) => c || caches.match("./index.html"))));
    return;
  }
  // Stale-while-revalidate: instant from cache, refreshed in the background for the next load.
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const refresh = fetch(e.request).then(put).catch(() => cached);
      return cached || refresh;
    }),
  );
});
```

Replace the ASSETS list with the actual files that exist in the project.

## Step 5 - Update index.html

Add inside `<head>` if missing:

```html
<link rel="manifest" href="manifest.json" />
<meta name="theme-color" content="#9d7dfc" />
```

Add before `</body>` if missing:

```html
<script>
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js");
  }
</script>
```

## Step 6 - Confirm

Tell the user what was created and remind them:

- `theme_color` and `background_color` in `manifest.json` can be updated to match their preferred theme
- The service worker is network-first for pages and stale-while-revalidate for assets, so a
  redeploy reaches returning users on their next visit (assets one load later) with no cache bump.
  Adding a new file means adding it to the `ASSETS` list for offline precache. Running `/pwa` again
  does not touch `sw.js`: Step 1 sees a complete setup and stops, and `/pwa skipVerification`
  regenerates `manifest.json` and `sw.js` from the template, overwriting any colors or names
  edited since.
- PWA install prompt will appear in supported browsers once deployed to GitHub Pages

Do not commit - the user handles that.
