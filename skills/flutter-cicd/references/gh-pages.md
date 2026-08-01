# GitHub Pages web deploy

Read this only after the dev has confirmed (per SKILL.md's ask-gate) that
web hosting via GitHub Pages should be wired.

Flutter web compiles to static files, so GitHub Pages serves it fine. Default for the portfolio (uniform across static-HTML and Flutter projects, free, no per-app cloud project).

**Blocker check first:** `gh repo view <owner/repo> --json visibility`. Pages does NOT publish from a **private** repo on the Free plan - it needs the repo public or GitHub Pro. If private + Free, ask the dev: make public, or use Firebase Hosting instead (ignores repo visibility). Before making a repo public, run a secrets pre-flight over the working tree AND git history (`git log --all --name-only` for keystores/service-account JSON/.env; grep for private keys/tokens). Firebase API keys in `firebase_options.dart` / `google-services.json` are public-safe by design.

**Routing:** Flutter web defaults to **hash** URLs (refresh-safe on Pages) unless the app calls `usePathUrlStrategy()`. If it uses path strategy, add a `404.html` = copy of `index.html` fallback.

**base-href:** a project page lives at `<user>.github.io/<repo>/`, so build with `--base-href /<repo>/`. A root/user site (`<user>.github.io`) needs no base-href.

Workflow `.github/workflows/deploy-web.yml`:

```yaml
name: Deploy Web (GitHub Pages)
on:
  push: { branches: [ main ] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
concurrency: { group: pages, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with: { flutter-version: '<from .fvmrc>', channel: stable, cache: true }
      - run: flutter pub get
      - run: flutter build web --release --base-href /<repo>/
      - uses: actions/upload-pages-artifact@v3
        with: { path: build/web }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Enable Pages with Actions as the source (once): `gh api -X POST repos/<owner/repo>/pages -f build_type=workflow`.

**Firebase apps - one manual step:** if the app uses Firebase Auth (Google popup via `signInWithPopup`), add the hosting domain (e.g. `<user>.github.io`) to Firebase Console -> Authentication -> Settings -> Authorized domains, or sign-in popups are rejected. This is one-time and covers all project pages on that github.io domain.
