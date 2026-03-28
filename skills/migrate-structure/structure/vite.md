# Vite Project Structure Spec

## Folder structure

```
src/
├── app.js
├── styles/
│   ├── styles.scss
│   ├── base.scss
│   └── components/
│       └── button.scss
├── components/
│   └── Button/
│       ├── Button.js
│       └── Button.scss
├── utils/
└── assets/
```

## File placement

| File type | Move to |
| --- | --- |
| SCSS main entry | `src/styles/styles.scss` |
| SCSS base/reset | `src/styles/base.scss` |
| SCSS component partials | `src/styles/components/` |
| JS components | `src/components/ComponentName/ComponentName.js` |
| Component styles | `src/components/ComponentName/ComponentName.scss` |
| JS utilities/helpers | `src/utils/` |
| Images/fonts imported in JS | `src/assets/` |
| Images/fonts referenced in HTML | `public/` |
| Other static assets | `public/` |

## Entry point rule

The JS entry is always `app.js`. If `main.js` exists at the entry, rename it to `app.js` and update all references.

## SCSS structure

- `styles.scss` is the main entry - imports `base.scss` and all `components/*.scss`
- `base.scss` holds resets, variables, and typography
- Component partials in `src/styles/components/` use plain filenames, no underscore prefix

## Component structure

Each component gets its own subfolder with a matching `.scss` file:

```
src/components/Button/
├── Button.js
└── Button.scss
```

## Public vs src/assets

- Referenced in HTML (src, href) → `public/`
- Imported in JS → `src/assets/`

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
