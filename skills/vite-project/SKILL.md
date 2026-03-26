---
name: vite-project
description: Use this skill when creating, restructuring, or updating a plain Vite project (no React). Triggers on any request to scaffold a new Vite project, migrate an old one, or review/fix folder structure in a Vite codebase.
---

# Vite Project Structure

Plain JS only. Never use TypeScript in Vite projects.

## Folder Structure

```
project-root/
├── index.html
├── vite.config.js
├── .eslintrc.js
├── .prettierrc
├── public/
│   └── (images, fonts, static assets)
└── src/
    ├── app.js              ← JS entry point
    ├── styles/
    │   ├── styles.scss     ← main entry, imports everything
    │   ├── base.scss       ← resets, variables, typography
    │   └── components/     ← one .scss file per UI component
    ├── components/         ← reusable UI pieces
    ├── utils/              ← helper functions
    └── assets/             ← images/fonts referenced in JS
```

## Rules
- Entry JS file is always `app.js`
- Entry SCSS file is always `styles.scss` — it imports `base.scss` and all `components/*.scss`
- Static assets (images, fonts) go in `public/` if referenced in HTML, `src/assets/` if referenced in JS
- ESLint + Prettier both required
- Never use TypeScript
