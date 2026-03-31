---
name: update-workflow
description: Triggers on /update-workflow only.
---

# /update-workflow

> Ensure the deploy workflow matches the correct template for this project type.

## Workflow

### Step 1 - Detect project type

Read `CLAUDE.md` and check the `Type:` field. If CLAUDE.md does not exist or type is missing, infer from the project structure:

- `vite.config.*` exists - vite
- `package.json` with React deps - react
- `index.html` with no `package.json` - html
- `default.project.json` or `*.project.json` - roblox

### Step 2 - Read the correct template

Based on project type, read the corresponding template from this skill's `templates/` folder:

- `html` - read `templates/html.yml`
- `vite` - read `templates/vite.yml`
- `react` - read `templates/react.yml`
- `roblox` - read `templates/roblox.yml`
- `flutter` - read `templates/flutter.yml`

If no template exists for the detected type, tell the user and stop.

### Step 3 - Compare to existing workflow

Check if `.github/workflows/deploy.yml` exists.

If it does not exist:

- Create `.github/workflows/` folder if needed
- Write the template as `deploy.yml`
- Tell the user it was created fresh

If it exists:

- Read it and compare to the template
- If it matches, tell the user and stop
- If it differs, use AI judgment to determine if the difference is intentional (e.g. a custom step the user added) or just outdated
- If outdated, rewrite it to match the template exactly
- If potentially intentional, show the user the diff and ask before overwriting

### Step 4 - Confirm

Tell the user what was done and flag anything that looked intentional that you preserved or flagged.
Do not commit - the user handles that.

## Notes

- Templates live in the `templates/` folder next to this SKILL.md
- To update a workflow template, edit the file directly in `templates/`
- New project types can be supported by adding a new template file and updating Step 2
