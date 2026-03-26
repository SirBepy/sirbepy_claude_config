# Global Rules

## Communication
- Brevity over grammar. Always.
- Ask ALL questions before starting work - trivial or not. Never assume.
- Never ask questions mid-task. Front-load everything.
- Never use em dashes (—) anywhere, ever. Use a comma, colon, or hyphen instead.
- When asking any question, always use the AskUserQuestion tool with 2-4 options. Never type numbered options in plain text. Never ask a bare open-ended question.

## Shell Commands
- Never chain commands with `&&`, `;`, or `|`. One command per bash call, always.
- This includes git — never do `cd /path && git add && git commit` in one call.

## File Editing
- Inside a git repo, edit any file freely without asking for permission first.
- Outside a git repo, ask before editing.

## Packages
- Never install packages without asking first.

## Manual Tasks
- If something requires manual action from Joe (web configs, credentials, cloud console, etc.), don't stop working.
- Add it as a numbered step to `WORKFLOWS_FOR_SIRBEPY.md` and continue.
- Never reset or clear that file. Joe manages it.

## Specs
- If given a spec file, read it fully before writing any code.
- Summarize your understanding and ask any questions, then implement.
