# Global Rules

## Communication

- Always invoke `/caveman` at the start of every session before doing anything else.
- Brevity over grammar. Always.
- Ask ALL questions before starting work - trivial or not. Never assume.
- Never ask questions mid-task. Front-load everything.
- Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.
- When asking any question, always use the AskUserQuestion tool with 2-4 options. Never type numbered options in plain text. Never ask a bare open-ended question.

## Git Commits

- NEVER commit directly. Always invoke the `/commit` skill first and follow its instructions.
- This applies to every commit, no exceptions.

## Shell Commands

- Never chain commands with `&&`, `;`, or `|`. One command per bash call, always.
- This includes git - never do `cd /path && git add && git commit` in one call.

## File Editing

- Inside a git repo, edit any file freely without asking for permission first.
- Outside a git repo, ask before editing.

## Packages

- Never install packages without asking first.

## .for_bepy Folder

All persistent cross-session notes live in `.for_bepy/` at the project root. Three files:

### COMMENTS.md - Notes for Joe
- Only write here if something important happened that Joe might have missed - especially relevant in auto mode where Joe may not have seen every decision.
- High bar: if Joe would say "I already knew that", don't write it.
- Keep entries brief, one or two sentences max. No padding.
- Never reset or clear. Joe manages it.

### BEPY_TODOS.md - Manual tasks for Joe
- Before adding anything here: try to do it yourself first. If you can run a bash command, make an API call, edit a file - do it. Only add here if it genuinely requires Joe's physical action (browser login, cloud console, credentials, hardware, etc.).
- Bullet points only, no numbers.
- Keep each bullet brief and actionable. One sentence.
- Delete bullets when Joe completes them or you have context they're done.

### AI_TODOS.md - Flagged items for Claude
- `/close` writes flagged code health issues here (large files, duplicates, etc.).
- Claude does NOT auto-act on this file. Joe triggers execution by saying "do the AI todos".
- Format: `- [ ] [action] [file/target] - [reason]`
- Mark done items with `- [x]` then clean them up on next pass.

## Icons

- Always use Phosphor Icons for icons. Never create inline SVGs or custom icon markup.
- HTML projects: load via CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`) and use `<i class="ph ph-icon-name">`.
- React projects: use `@phosphor-icons/react` package.
- Browse available icons at https://phosphoricons.com

## Code Style

- On first encounter with a project's language/stack (editing code, debugging, inspecting build/wally configs, or planning), check if `~/.claude/code-style/` has a matching file (e.g. `luau.md`, `react.md`). If it exists, read it and follow its preferences.
- Read it once per session.

## Execution Discipline

- State assumptions before coding. Present interpretations instead of picking silently.
- Every changed line must trace to the request. No drive-by refactors.
- Define success criteria upfront (test, command, check). Loop until verified.

## Specs

- If given a spec file, read it fully before writing any code.
- Summarize your understanding and ask any questions, then implement.
