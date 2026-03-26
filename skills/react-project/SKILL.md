---
name: react-project
description: Use this skill when creating, restructuring, or updating a React project. Triggers on any request to scaffold a new React app, migrate an old one, or review/fix folder structure in a React codebase.
---

# React Project Structure

Plain JS only. Never use TypeScript in React projects.

## Folder Structure

```
project-root/
├── index.html
├── vite.config.js
├── .eslintrc.js
├── .prettierrc
├── public/
│   └── (static assets)
└── src/
    ├── App.jsx             ← root component
    ├── main.jsx            ← React entry point
    ├── styles/
    │   ├── styles.scss     ← main entry, imports everything
    │   ├── base.scss       ← resets, variables, typography
    │   └── components/     ← one .scss file per component (non-module global styles)
    ├── pages/              ← route-level components
    ├── components/         ← reusable UI components
    │   └── ComponentName/
    │       ├── ComponentName.jsx
    │       └── ComponentName.module.scss
    ├── hooks/              ← custom React hooks
    ├── context/            ← Context API providers and consumers
    ├── services/           ← API calls, external service logic
    └── utils/              ← helper functions
```

## Rules
- Plain JS always, never TypeScript
- `App.jsx` lives at the root of `src/`
- Each component gets its own folder with a `.jsx` and a `.module.scss` file
- Routing via React Router
- State management via Context API — no Redux, no Zustand
- ESLint + Prettier both required
- SCSS only, no plain CSS, no Tailwind
