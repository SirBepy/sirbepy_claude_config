---
name: git-init
description: Triggers on /git-init only.
---

# /git-init

> Initialize git, create .gitignore, and make the first commit if needed.

## Step 1 - Git init

1. Check if a git repo exists (`git status`)
2. If not, run `git init`

## Step 2 - Ensure .gitignore

If `.gitignore` does not exist, create one with these defaults:

```
.DS_Store
node_modules/
dist/
.env
```

If `.gitignore` already exists, check it includes `.DS_Store`. If not, add it at the top. Also scan the project and add any other obvious entries that are missing (e.g. `node_modules/` if there's a `package.json`).

## Step 3 - Initial commit

1. Check if there are any commits (`git log --oneline -1`)
2. If no commits exist and there are files to stage, stage all current files by name and commit: `MAJOR: initial commit`
3. If commits already exist, skip this step

## Step 4 - Confirm

Print what was done (initialized, .gitignore created/updated, committed, or skipped).
