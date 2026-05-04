# Global Rules

## Communication

- Always invoke `/caveman` at the start of every session before doing anything else.
- Brevity over grammar. Always.
- Ask ALL questions before starting work - trivial or not. Never assume.
- Never ask questions mid-task. Front-load everything.
- Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.
- When asking any question, always use the AskUserQuestion tool with 2-4 options. Never type numbered options in plain text. Never ask a bare open-ended question.
- Prefix every question with a domain tag so Joe knows how much weight to give Claude's input:
  - `[UX]` - visual, layout, interaction feel (Joe's taste dominates; skip long/short-term axes, but still give a brief recommendation)
  - `[ARCH]` - system design, abstractions, data flow (Claude's input is load-bearing)
  - `[PERF]` - speed/memory tradeoffs
  - `[SEC]` - security decisions (Claude's input is load-bearing)
  - `[DATA]` - schema, data modeling
  - `[TOOLING]` - dev tooling, linting, code style, naming
  - `[CI/CD]` - deployment, infra, pipelines
- When presenting options, always tag which is best long-term and which is best short-term (in the option label or description), EXCEPT for [UX] questions. Joe always wants to see both axes so he can weigh tradeoffs. If the same option wins both, say so explicitly.

## Git Commits

- NEVER commit directly. Always invoke the `/commit` skill first and follow its instructions.
- This applies to every commit, no exceptions - including commits made by subagents in subagent-driven development.

## Shell Commands

- Never chain commands with `&&`, `;`, or `|`. One command per bash call, always.
- This includes git - never do `cd /path && git add && git commit` in one call.

## File Editing

- Inside a git repo, edit any file freely without asking for permission first.
- Outside a git repo, ask before editing.

## Packages

- Never install packages without asking first.
- Before suggesting any package, tool, or program to install/download, do a quick web search to verify it is legitimate and safe. Check for typosquatting, malicious forks, or known malware reports. Only suggest after confirming.

## Process Hygiene

- **Never leave orphan child processes.** If you spawn a process (vitest, turbo, dev server, anything that forks workers), verify it exited cleanly before claiming the task is done. After running test/build/dev commands, sanity-check with `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` (PowerShell) or `pgrep node` (Unix). Kill any orphans immediately. Joe found 90+ orphan vitest processes from one session at 100% CPU and 90°C; this is unacceptable.
- **Three-layer orphan defense:**
  1. **In every subagent prompt that runs tests/builds:** mandatory final step is "run the project's orphan-check script (e.g. `pnpm check-orphans` if it exists, otherwise `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }`). If orphans remain, kill them with `Stop-Process -Id <PID> -Force` before reporting DONE."
  2. **Main agent rule:** after every subagent that ran Node commands completes, the main agent runs the same orphan check itself. If orphans are found, dispatch a one-shot cleanup subagent or kill them inline.
  3. **Optional Stop hook (recommended):** configure a Claude Code Stop hook that runs the project's orphan-killer when the session ends. Acts as the last safety net.
- **Cap concurrency at 5.** Never run more than 5 Node-based commands concurrently. Always pass `--concurrency=5` to turbo. Set `poolOptions.threads.maxThreads: 5` (or use `pool: 'forks'` with `singleFork: true` for clean Windows exit) in every vitest config. Use `--workspace-concurrency=5` on pnpm. Never run `pnpm dev --parallel` outside of explicit dress-rehearsal use. (Joe's hardware can handle 5 fine; the orphan issue, not concurrency itself, was what burned the CPU last time.)
- For long-running dev servers (vite, fastify), track the PID and ensure it terminates on session end / Ctrl-C / completion of the parent task.
- This is non-negotiable — orphan processes pegged Joe's CPU and disrupted his work.

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

### ai_todos/ - Flagged items for Claude (one .md per task)

A folder of per-task markdown files. Each file is briefed densely enough that a future cold AI session can execute the task without rebuilding context.

- `/close` writes flagged code health issues, unfinished offers, and other follow-ups here, one file each.
- Claude does NOT auto-act on this folder. Joe triggers execution by saying "do the AI todos" or naming a specific one.
- Filename: zero-padded numeric prefix + kebab-case slug (e.g. `03-tighten-onboarding-step-redirect.md`). The prefix is the task's stable id; Joe references tasks by id ("do todo 03").
- Picking the next id: scan existing filenames in `ai_todos/` (and `ai_todos/done/` if it exists), take the max numeric prefix, add 1. Never reuse ids, even after a task is deleted.
- Done tasks: delete the file (or move to `ai_todos/done/` if Joe wants history). The id stays burned either way.

Required sections in every file:

```md
# <one-line task title>

## Goal

One or two sentences. The user-facing or code outcome we're after.

## Context

Background a future cold AI needs. Pointers to relevant writeups (e.g. `.for_bepy/commits_explained/<id>.md`), prior commits, related files with `path:line`. Why this is being deferred (so the AI knows what's already been considered).

## Approach

Concrete proposed steps. If a code shape was discussed, sketch it. Mention alternatives that were rejected and why, so the AI doesn't re-litigate.

## Acceptance

- How to know it worked.
- What must NOT regress (pointers to recent fixes, edge cases).
- Verification commands or manual repro steps if applicable.
```

Skip a section only if it genuinely doesn't apply (e.g. trivial chore with no alternatives). Never just write a title and a one-liner.

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
