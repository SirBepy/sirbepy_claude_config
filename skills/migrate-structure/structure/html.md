# HTML Project Structure Spec

## File placement

| File type  | Move to          |
| ---------- | ---------------- |
| `.css`     | `src/styles/`    |
| `.js`      | `src/scripts/`   |
| `.data.js` | `src/data/`      |
| `.json`    | `assets/data/`   |
| images     | `assets/images/` |
| fonts      | `assets/fonts/`  |

Create folders only if there is content that belongs there.

## Never move

- Config files (`*.config.js`, `*.config.ts`)
- `favicon.ico` - always stays in root
- Anything in `.github/`

## After moving

- Update all references in `index.html`
- Update any imports inside moved files
- Flag anything that didn't fit a rule in the summary
