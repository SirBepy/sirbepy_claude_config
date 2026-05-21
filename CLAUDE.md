# Global Rules

## Communication

- Always invoke `/caveman` at the start of every session before doing anything else.
- Front-load all questions before starting work, trivial or not. Never ask mid-task; never assume.
- Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.
- When asking any question, always use the AskUserQuestion tool with 2-4 options. Never type numbered options in plain text. Never ask a bare open-ended question.
- Prefix every question with a domain tag so Joe knows how much weight to give Claude's input:
  - `[UX]` - visual, layout, interaction feel (Joe's taste dominates; skip long/short-term axes, but still give a brief recommendation)
  - `[ARCH]` - system design, abstractions, data flow (Claude's input is load-bearing)
  - `[SEC]` - security decisions (Claude's input is load-bearing)
  - `[DATA]` - schema, data modeling
  - `[TOOLING]` - dev tooling, linting, code style, naming
- When presenting options, always tag which is best long-term and which is best short-term INSIDE the option label or description (e.g. description starts `Long-term best: ...`), not only in surrounding chat - Joe skims past commentary. EXCEPT for [UX] questions, skip the axes. Long-term means architectural/design merit over a multi-year horizon. If the same option wins both axes, say so explicitly. Default to picking a winner; only declare "no clear long-term winner" when you can name the specific tradeoff that ties them.

## Git Commits

- NEVER commit directly. Always invoke the `/commit` skill first and follow its instructions.
- This applies to every commit, no exceptions - including commits made by subagents in subagent-driven development.
- **Subagents cannot invoke `/commit` (they have no access to the Skill tool).** Therefore subagents must NEVER commit. When dispatching any subagent (foreground or background), the dispatch prompt MUST include this exact language: "Stage your changes but do NOT commit. The main agent will run `/commit` after your report-back." For background subagents, have them write a short `READY_TO_COMMIT.md` marker (or similar report-back doc) so the main agent knows there's staged work waiting when the completion notification arrives.
- If you find yourself about to commit and cannot invoke the `/commit` skill, do not commit at all. Stop, surface the problem, wait for the main agent / human.

## Shell Commands

- Default to PowerShell. Joe's tooling (fvm, dart, flutter, node, gh, etc.) is configured for PowerShell on Windows. Only fall back to Bash if a PowerShell attempt fails or the command is genuinely POSIX-only.
- Never chain commands with `&&`, `;`, or `|`. One command per call, always.
- This includes git - never do `cd /path && git add && git commit` in one call.

## File Editing

- Inside a git repo, edit any file freely without asking for permission first.
- Outside a git repo, ask before editing.

## Packages

- Never install packages without asking first.
- Before suggesting any package, tool, or program to install/download, do a quick web search to verify it is legitimate and safe. Check for typosquatting, malicious forks, or known malware reports. Only suggest after confirming.

## Process Hygiene

- **Never leave orphan child processes.** After running test/build/dev commands, check with `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }` (Windows) or `pgrep node` (Unix). Kill orphans with `Stop-Process -Id <PID> -Force` before claiming done. Past incident: 90+ orphan vitest processes pegged the CPU at 100% and 90°C.
- **Cap concurrency at 5** for all Node commands: turbo `--concurrency=5`, vitest `poolOptions.threads.maxThreads: 5` (or `pool: 'forks'` + `singleFork: true` for clean Windows exit), pnpm `--workspace-concurrency=5`. Never `pnpm dev --parallel` outside explicit dress-rehearsal.
- For long-running dev servers (vite, fastify), track the PID and ensure it terminates on session end / Ctrl-C / parent task completion.
- Non-negotiable. Full doctrine (3-layer defense, subagent prompt requirements): `~/.claude/refs/process-hygiene.md`.

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

- `/close` writes flagged code health issues, unfinished offers, and other follow-ups here, one file each.
- Claude does NOT auto-act on this folder. Joe triggers execution by saying "do the AI todos" or naming a specific id.
- Format spec (filename rules, id-numbering, required sections): `~/.claude/skills/close/ai-todos-format.md`.

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

## Persistence

- Before adding any persistence (localStorage, sessionStorage, cookies, IndexedDB, disk, DB), state explicitly before writing the code the specific user-facing behavior it preserves across tab close or refresh. If you cannot name the behavior, do not persist. Default to in-memory state (Riverpod / context / useState / module-scope).
- When extending an existing persistence layer (e.g. adding a field to a storage class), re-check whether the underlying pattern still matches the current UX. Existing code is not evidence the pattern is right.
- Past incident: pending-login email persisted to localStorage in a flow whose UX is "refresh redirects to login." Persistence was contradictory by definition and introduced a race between in-memory and persisted state. Should have stayed in Riverpod (`keepAlive: true`) with zero disk.

## Specs

- If given a spec file, read it fully before writing any code.
- Summarize your understanding and ask any questions, then implement.

## Subagent-Driven vs Inline Execution

When a plan is ready to execute, choose based on task size - do not default to subagent-driven just because skills recommend it:

- **Inline execution** (default): small features, fewer than 4 tasks, fewer than 3 files, tightly sequential steps. Just do it.
- **Subagent-driven**: large features with 5+ independent tasks, multiple files, where fresh context per task and review gates add real value.

If it feels quick, it's inline. Only escalate to subagent-driven when the complexity genuinely justifies the overhead.
