---
name: github-pages-init
description: Triggers on /github-pages-init only.
---

# /github-pages-init

> Create a GitHub repo if missing and enable GitHub Pages for web projects.

## Step 0 - Check project type

Read `CLAUDE.md` for the `Type:` field. Only proceed if the value contains `html`, `vite`, or `react` as a substring (the field can carry extra descriptive text, e.g. `Type: react (Vite 7 + React 19)` still matches). If not a web project, print:

```
/github-pages-init - not a web project, skipping.
```

And stop.

## Step 1 - Ensure remote repo exists

1. Check if a remote exists: `git remote get-url origin`
2. If no remote, create a public GitHub repo using the current folder name: `gh repo create [folder-name] --public --source=.`
3. If remote already exists, skip this step

## Step 1.5 - Check deploy workflow exists

Check if `.github/workflows/deploy.yml` exists. If it does not, warn:

```
No .github/workflows/deploy.yml found - run /update-workflow first.
```

## Step 2 - Enable GitHub Pages

1. Check if Pages is enabled: `gh api repos/{owner}/{repo}/pages`. A 404 means Pages is not yet enabled - this is expected, continue to step 2, do not treat it as an abort condition.
2. If not enabled, enable it with GitHub Actions as source: `gh api repos/{owner}/{repo}/pages -X POST -f build_type=workflow`
3. If already enabled, skip this step

## Step 3 - Confirm

Print what was done (repo created, Pages enabled, or both already existed). Then print:

```
Now all that's left is to push.
```

Do not push. The user handles that.
