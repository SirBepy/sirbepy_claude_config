---
name: decouple-file
description: Triggers on /decouple-file only.
---

# /decouple-file

> Extract and split file content into properly structured, right-sized files.

## Command syntax

```
/decouple-file                          - show suggestions and ask what to target
/decouple-file index.html               - decouple a specific file
/decouple-file index.html, src/scripts/script.js - decouple multiple files
/decouple-file .html                    - decouple all files of that type
/decouple-file .html .js .css           - multiple types at once
```

## Step 0 - If no arguments given

Scan the project and suggest candidates. Use AskUserQuestion with options like:

- "index.html (has inline scripts/styles)"
- "src/scripts/script.js (over 200 lines)"
- "All .js files"
- "Let me type something"

Wait for selection before continuing.

## Step 1 - Read structure spec

Read `CLAUDE.md` for project type, then read the corresponding structure spec from `/migrate-structure/structure/[type].md` to know where extracted files should go.

## Step 2 - Analyze target files

For each target file, identify what can be extracted or split:

### HTML files

- Inline `<script>` blocks - extract to `src/scripts/`
- Inline `<style>` blocks - extract to `src/styles/`
- Inline SVGs that are large or reusable - extract to `assets/images/`
- Base64 encoded images - decode and save to `assets/images/`, replace with file reference

### JS files

- Large data structures, arrays, lookup tables - extract to `src/data/` as `.data.js`
- If file is over 200 lines, split into logical modules - hard limit is 400 lines per file
- Split at natural boundaries - functions, classes, concerns, not arbitrarily

### CSS files

- If file has clear logical sections (layout, typography, components, etc.), split into separate files
- Only split if there is a clear boundary - never split arbitrarily

## Step 3 - Plan before acting

Before moving anything, print the full plan:

```
Plan:
- Extract <script> block from index.html -> src/scripts/script.js (merge with existing)
- Extract inline SVG logo from index.html -> assets/images/logo.svg
- Split src/scripts/script.js (380 lines) -> script.js + flashcards.data.js
```

Ask for confirmation before proceeding.

## Step 4 - Execute

Carry out the plan. For each extraction:

- Create the target file
- If target file already exists, merge content in a logical way
- If merged file exceeds 200 lines, split it meaningfully - never exceed 400 lines in any single file
- Update all references in the source file to point to the new location
- Remove the extracted content from the source file

## Step 5 - Confirm

Print a summary of everything that was extracted and split. Flag anything that was too ambiguous to split automatically.
Do not commit - the user handles that.
