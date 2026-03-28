---
name: migrate-structure
description: Triggers on /migrate-structure only.
---

# /migrate-structure

> Normalize project file structure and sync missing boilerplate files.

## Workflow

### Step 1 - Detect project type

Read `CLAUDE.md` and check the `Type:` field. If missing, infer from project structure.

### Step 2 - Read the structure spec

Read the corresponding spec from this skill's `structure/` folder:

- `html` - read `structure/html.md`
- `vite` - read `structure/vite.md`
- `react` - read `structure/react.md`
- `roblox` - read `structure/roblox.md`
- `flutter` - read `structure/flutter.md`

If no spec exists for the detected type, tell the user and stop.

### Step 3 - Scan the project

Read the project file tree. Identify:

- Files that are in the wrong location according to the spec
- Folders that need to be created
- Files that don't fit any rule in the spec

### Step 4 - Sync boilerplate templates

Read everything in `templates/[type]/` and compare to what exists in the project root. For any file that is missing, copy it in. For any file that exists, swap it with the template version exactly.

### Step 5 - Move files

Move all misplaced files to their correct locations according to the spec. Create folders as needed, only if there is content going into them.

Then update all references:

- All paths in `index.html` or equivalent entry point
- Any imports inside moved files that reference other moved files

### Step 6 - Confirm

Print a summary of everything moved, created, and swapped. Flag any files that didn't fit a rule. Do not commit - the user handles that.
