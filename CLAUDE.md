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

## Manual Tasks

- If something requires manual action from Joe (web configs, credentials, cloud console, etc.), don't stop working.
- Add it as a numbered step to `WORKFLOWS_FOR_SIRBEPY.md` and continue.
- When Joe completes a manual task (or you have context that it's done), delete that line from the file.
- If the file has no remaining tasks, delete the file entirely.

## Notes for Joe

- If you have comments, questions, or things Joe should review after a session, append them to `COMMENTS_FOR_BEPY.md` in the project root.
- Never reset or clear that file. Joe manages it.
- If the file doesn't exist, create it.

## Icons

- Always use Phosphor Icons for icons. Never create inline SVGs or custom icon markup.
- HTML projects: load via CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`) and use `<i class="ph ph-icon-name">`.
- React projects: use `@phosphor-icons/react` package.
- Browse available icons at https://phosphoricons.com

## Code Style

- Before writing or modifying code, detect the project's language/stack and check if `~/.claude/code-style/` has a matching file (e.g. `luau.md`, `react.md`). If it exists, read it and follow its preferences.
- Only read the file once per session, and only when you actually need to write or change code.

## Specs

- If given a spec file, read it fully before writing any code.
- Summarize your understanding and ask any questions, then implement.
