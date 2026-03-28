# React Project Structure Spec

## Folder structure

```
src/
├── main.jsx
├── App.jsx
├── styles/
│   ├── styles.scss
│   ├── base.scss
│   └── components/
│       └── button.scss
├── pages/
│   └── Home/
│       ├── Home.jsx
│       └── Home.module.scss
├── components/
│   └── Button/
│       ├── Button.jsx
│       └── Button.module.scss
├── hooks/
│   └── useAuth.js
├── context/
│   └── AuthContext.js
├── services/
│   └── api.js
└── utils/
```

## File placement

| File type | Move to |
| --- | --- |
| React entry point | `src/main.jsx` |
| Root component | `src/App.jsx` |
| Route-level components | `src/pages/PageName/PageName.jsx` |
| Page styles | `src/pages/PageName/PageName.module.scss` |
| Reusable UI components | `src/components/ComponentName/ComponentName.jsx` |
| Component styles | `src/components/ComponentName/ComponentName.module.scss` |
| Custom hooks | `src/hooks/useXxx.js` |
| Context providers | `src/context/XxxContext.js` |
| API/service logic | `src/services/` |
| Helper functions | `src/utils/` |
| Images/fonts imported in JS/JSX | `src/assets/` |
| Images/fonts referenced in HTML | `public/` |
| Other static assets | `public/` |

## SCSS structure

- `styles.scss` is the main entry - imports `base.scss` and all `components/*.scss`
- `base.scss` holds resets, variables, and typography
- Component partials in `src/styles/components/` use plain filenames, no underscore prefix
- Per-component scoped styles use `.module.scss` inside the component folder

## Component and page structure

Each component and page gets its own subfolder. Only create `.module.scss` if the component has styles:

```
src/components/Button/
├── Button.jsx
└── Button.module.scss   ← only if styles exist

src/pages/Home/
├── Home.jsx
└── Home.module.scss     ← only if styles exist
```

## Context

One file per context, flat in `src/context/`:

- `context/AuthContext.js`
- `context/ThemeContext.js`

## Services

Flat files named after the domain, in `src/services/`:

- `services/api.js`
- `services/auth.js`

## Hooks

Flat files with `use` prefix, in `src/hooks/`:

- `hooks/useAuth.js`
- `hooks/useFetch.js`

## Public vs src/assets

- Referenced in HTML (src, href) → `public/`
- Imported in JS/JSX → `src/assets/`

## Never move

- `vite.config.js`
- `.eslintrc.js`
- `.prettierrc`
- `index.html`
- `favicon.ico`
- Anything in `.github/`
- `package.json`, `package-lock.json`

## Unknown files

Any file that doesn't match a rule above: list it in the summary, do not move it.
