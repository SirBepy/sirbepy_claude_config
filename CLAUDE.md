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

- **Safety check is mandatory and automatic.** Before suggesting OR adding any package, tool, or program, research that it is legitimate and safe. This is default behavior - do it every time without being asked.
- The check must cover: typosquatting (is this the real package name?), malicious forks, known malware reports, AND the security-advisory databases for the ecosystem (RustSec for crates, `npm audit` / GitHub advisories for npm, PyPI/OSV for Python, etc.). Confirm the version you'll pin is past any known vulnerability fix.
- **Prefer a subagent for the research.** Dispatch a subagent (e.g. `general-purpose`) to do the safety investigation and report back a verdict + the specific advisories/versions it found. This keeps the main context clean and is more thorough. For a single obvious package a quick inline web search is acceptable, but for anything load-bearing or crypto/network-related, use a subagent.
- **Asking before adding:** in non-personal projects, still ask before installing. In personal projects (those importing `full-auto.md`), auto-adding is allowed *once the safety check passes* - no need to ask. If the safety check is inconclusive, finds an advisory with no patched version, or the package looks risky, stop and ask regardless of project type.

## Process Hygiene

- **Never leave orphan child processes.** After running test/build/dev commands, check with `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }` (Windows) or `pgrep node` (Unix). Kill orphans with `Stop-Process -Id <PID> -Force` before claiming done. Past incident: 90+ orphan vitest processes pegged the CPU at 100% and 90°C.
- **Cap concurrency at 5** for all Node commands: turbo `--concurrency=5`, vitest `poolOptions.threads.maxThreads: 5` (or `pool: 'forks'` + `singleFork: true` for clean Windows exit), pnpm `--workspace-concurrency=5`. Never `pnpm dev --parallel` outside explicit dress-rehearsal.
- For long-running dev servers (vite, fastify), track the PID and ensure it terminates on session end / Ctrl-C / parent task completion.
- Non-negotiable. Full doctrine (3-layer defense, subagent prompt requirements): `~/.claude/refs/process-hygiene.md`.

## .for_bepy Folder

All persistent cross-session notes live in `.for_bepy/` at the project root. Two files:

### BEPY_TODOS.md - Manual tasks for Joe

- Before adding anything here: try to do it yourself first. If you can run a bash command, make an API call, edit a file - do it. Only add here if it genuinely requires Joe's physical action (browser login, cloud console, credentials, hardware, etc.).
- **Testing:** if the project has Playwright, a test suite, or any automated testing setup - use it. Write the test and run it. Only hand off to Joe if it is genuinely untestable by Claude (e.g. native Tauri UI, hardware, visual judgment calls). Never ask Joe to test something Claude can test itself.
- Bullet points only, no numbers.
- Keep each bullet brief and actionable. One sentence.
- Delete bullets when Joe completes them or you have context they're done.
- **Categories:** group entries under `### Urgent` (credentials, keys, hardware) and `### Visual QA` (needs Joe's eyes) so Joe can triage at a glance.

### ai_todos/ - Flagged items for Claude (one .md per task)

- `/close` writes flagged code health issues, unfinished offers, and other follow-ups here, one file each.
- Claude does NOT auto-act on this folder. Joe triggers execution by saying "do the AI todos" or naming a specific id.
- Format spec (filename rules, id-numbering, required sections): `~/.claude/skills/close/ai-todos-format.md`.

## Icons

- Always use Phosphor Icons for icons. Never create inline SVGs or custom icon markup.
- HTML projects: load via CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`) and use `<i class="ph ph-icon-name">`.
- React projects: use `@phosphor-icons/react` package.
- Browse available icons at https://phosphoricons.com

## Screenshots

- Verification/debug screenshots (ad-hoc Playwright captures, manual smoke tests) go in `.for_bepy/screenshots/`, never the repo root. That folder is gitignored, so they never leak into commits or clutter `git status`. Create the folder if it's missing before saving.
- This does NOT apply to the `/screenshot` skill: its portfolio-quality keepers stay in `.portfolio-data/`. Only throwaway verification shots go in `.for_bepy/screenshots/`.
- `/close` empties `.for_bepy/screenshots/` at session end, so treat anything there as disposable.

## Code Style

- On first encounter with a project's language/stack (editing code, debugging, inspecting build/wally configs, or planning), check if `~/.claude/code-style/` has a matching file (e.g. `luau.md`, `react.md`). If it exists, read it and follow its preferences.
- Read it once per session.

## Execution Discipline

- State assumptions before coding. Present interpretations instead of picking silently.
- Every changed line must trace to the request. No drive-by refactors.
- Define success criteria upfront (test, command, check). Loop until verified.

## Testing & verification floor

- Before claiming done or handing work to Joe, run every fast check the project HAS - typecheck, unit tests, lint, build - and it must pass. Change size never exempts: a one-line edit gets the same floor as a rewrite. Never skip silently because something "looks small."
- If a project has no tests, or the change is genuinely untestable by Claude (native UI, hardware, visual judgment), say so explicitly instead of skipping quietly.
- Slow end-to-end suites (Playwright, etc.) are NOT part of this floor. A project with a browser e2e suite `@import`s `~/.claude/snippets/test-e2e.md` in its own CLAUDE.md, which defines when/how e2e runs; projects that don't import it run the floor only.

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
