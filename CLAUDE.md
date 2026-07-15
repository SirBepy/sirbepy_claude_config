# Global Rules

## Communication

- Front-load all questions before starting work, trivial or not. Never ask mid-task; never assume.
- Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.
- When stating that Claude Code is about to do something, write "Claude" as the subject, never "you" or "I" (it gets confusing about who acts). E.g. "Claude will write them to Clockify", "Claude will POST the new entries", not "I'll write them" or "you'll write them".
- Every question: use the AskUserQuestion tool with 2-4 options. Never a bare open-ended question; never plain-text numbered options.
- Prefix every question with a domain tag so Joe knows how much weight to give Claude's input:
  - `[UX]` - visual, layout, interaction feel (Joe's taste dominates; skip the long/short-term axes, but still give a brief recommendation)
  - `[ARCH]` - system design, abstractions, data flow (Claude's input is load-bearing)
  - `[SEC]` - security decisions (Claude's input is load-bearing)
  - `[DATA]` - schema, data modeling
  - `[TOOLING]` - dev tooling, linting, code style, naming
- Mark the long-term-best and short-term-best pick INSIDE the option label/description, not only in surrounding chat (Joe skims past commentary). Skip the axes for [UX]. Long-term means architectural/design merit over a multi-year horizon. Default to naming a winner; only declare no clear winner when you can name the specific tradeoff that ties them.
- Copy-paste for Joe: full ruleset in `~/.claude/refs/copy-paste-format.md` - read once per session. Core: everything Joe should copy goes in a BLOCKQUOTE (inline backticks and fenced code blocks don't render distinctly in the app). Also covers: placeholder callouts, sequential command batching, language matching (Croatian vs English), message length limits.
- Popup attribution: whenever a Claude action triggers an OS/app prompt Joe sees (GitHub/git credential picker, UAC, auth/login popups, browser permission dialogs, keychain, MFA, any external dialog), proactively and immediately tell Joe that the popup came from Claude and name the exact command/action that caused it. Never let Joe wonder who triggered a popup.
- Work quietly: minimize narration between tool calls. No play-by-play ("Now let me…", "Let me check…"). Batch independent tool calls, let results speak, and give ONE tight summary at the end. The CLI statusline already shows live activity. Surface mid-task only for a real decision, blocker, or question.

## Git Commits

- NEVER commit directly. Always invoke `/commit` first and follow it - every commit, no exceptions, including in subagent-driven work.
- Subagents can't invoke skills, so subagents NEVER commit. Every subagent dispatch prompt (foreground or background) MUST include verbatim: "Stage your changes but do NOT commit. The main agent will run `/commit` after your report-back." Background subagents: see `~/.claude/refs/process-hygiene.md` for the READY_TO_COMMIT marker.
- If you're about to commit and can't invoke `/commit`, don't commit - stop, surface the problem, wait for the main agent / human.

## gh CLI Account

- A global `PreToolUse` hook (`~/.claude/hooks/gh-account-switch.sh`) auto-switches `gh`'s active account to match the repo's `origin` remote before any `gh` command runs (zirtue-corp -> JosipMuzicZirtue, Fibo-Studio -> JosipMuzicFibo, revaire -> josipmuzic, else SirBepy). Joe never runs `gh auth switch` himself. If a `gh` "Could not resolve to a Repository" error ever appears, the hook didn't fire (wrong cwd / non-repo dir) - switch to the mapped account and retry, do NOT assume the account was deleted. Commit identity (git includeIf) is a separate, already-correct system.

## Shell Commands

- Default to PowerShell (Joe's fvm/dart/flutter/node/gh tooling is configured for PowerShell on Windows). Fall back to Bash only if a PowerShell attempt fails or the command is genuinely POSIX-only.
- Never chain commands with `&&`, `;`, or `|` - one command per call, always, git included.

## File Editing

- Inside a git repo: edit any file freely, no permission needed. Outside a git repo: ask before editing.

## Packages

- Before suggesting OR adding any package/tool/program: a mandatory, automatic safety check - typosquat (real name?), malicious forks, known malware reports, and the ecosystem advisory DB (RustSec / `npm audit` / OSV); confirm the version you'll pin is past any known fix.
- Prefer a subagent for the research; required for anything load-bearing or crypto/network. A quick inline web search is acceptable for a single obvious package.
- Asking gate: personal projects (those importing `full-auto.md`) auto-add once the check passes; otherwise ask before installing. If the check is inconclusive, finds no patched version, or the package looks risky - stop and ask regardless.

## Process Hygiene

- **Running servers - always via `/supervised-run`.** Always route long-lived servers through the `/supervised-run` skill; fall back to a plain shell run only if the supervisor is unreachable. Does NOT apply to one-off commands that exit (tests, builds, git, scripts).
- **Never leave orphan child processes.** After running test/build/dev commands, check with `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }` (Windows) or `pgrep node` (Unix). Kill orphans with `Stop-Process -Id <PID> -Force` before claiming done. Past incident: 90+ orphan vitest processes pegged the CPU at 100% and 90°C.
- **Cap concurrency at 5** for all Node commands: turbo `--concurrency=5`, vitest `poolOptions.threads.maxThreads: 5` (or `pool: 'forks'` + `singleFork: true` for clean Windows exit), pnpm `--workspace-concurrency=5`. Never `pnpm dev --parallel` outside explicit dress-rehearsal.
- For long-running dev servers (vite, fastify), track the PID and ensure it terminates on session end / Ctrl-C / parent task completion.
- Non-negotiable. Full doctrine (3-layer defense, subagent prompt requirements): `~/.claude/refs/process-hygiene.md`.

## Code Style

- On first encounter with a project's stack, check `~/.claude/code-style/` for a matching file (e.g. `luau.md`, `react.md`) and follow its preferences. Read once per session.

## Execution Discipline

- For any creative/feature work (new feature, component, behavior change, non-trivial design), use the local `/brainstorm` skill, never `superpowers:brainstorming`. The local one is the owned, gate-free replacement.
- State assumptions and interpretations before coding; present them instead of picking silently.
- Every changed line must trace to the request. No drive-by refactors.
- Before writing a new helper, util, or type: scan the codebase first. If something equivalent already exists a few files over, reuse it. Re-implementing what's nearby is the most common way code bloats.
- Prefer the platform primitive over a library or custom code: CSS over JS animation, `<input type="date">` over a picker lib, a DB constraint over app-layer validation, a built-in widget over a custom one. If the runtime provides it, use it.
- Define success criteria upfront (test, command, check). Loop until verified.
- Given a spec file: read it fully, summarize your understanding and ask any questions, then implement.

## Testing & verification floor

- Before claiming done or handing to Joe: run every FAST check the project HAS (typecheck, unit, lint, build) - all must pass. No size exemption; a one-line edit gets the same floor as a rewrite. Never skip silently because something "looks small."
- If a project has no tests, or the change is genuinely untestable by Claude (native UI, hardware, visual judgment), say so explicitly instead of skipping quietly.
- Slow end-to-end suites (Playwright, etc.) are NOT part of this floor; projects opt in via `@import ~/.claude/snippets/test-e2e.md`.

## UI & visual changes

- Frontend icons: always Phosphor Icons, never inline SVG or custom icon markup. HTML via CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`, `<i class="ph ph-icon-name">`); React via `@phosphor-icons/react`. Browse: https://phosphoricons.com
- User-facing/visual change: show Joe - bring the app up via `/supervised-run`, give him the URL, and capture a screenshot via SendUserFile. Skip for pure logic/backend/config (noise there).
- Per-repo run mechanics (env file, login/OTP, ports, web-server vs chrome device, CORS) live in project memories - check them first; don't rediscover them.
- Throwaway verification screenshots go in `.for_bepy/screenshots/` (gitignored, disposable, `/close` empties it; create the folder if missing). The `/screenshot` skill's portfolio keepers stay in `.portfolio-data/`.

## AI todos + plan - `.claude/todos/` (per project)

- Full contract (backlog format, ids, PLAN.md lane, done/, git policy): `~/.claude/skills/close/ai-todos-format.md`. Written by `/close`, `/create-todo`, `/code-check`, autopilot; ordered by `/plan-todos`; executed via `/pickup`, `/batch-todos`, or Joe naming an id - Claude never auto-acts on the folder.
- **Claim rule (non-negotiable): before EXECUTING any todo, claim it via `.claude/todos/.claims/<id>.claim` per the contract - every path, including ad-hoc "do todo 07". Release on completion or abort.**
- Items needing Joe's physical action (browser login, cloud console, credentials, hardware) have no persistent home - try it yourself first (if the project has any test setup, write and run the test rather than handing off), and only if genuinely blocked, surface it directly in the response instead of writing a file.

## .for_bepy Folder

Project-local scratch (never global; skip if there's no project): `screenshots/` (see UI section), `autopilot-logs/` (genuine blockers from unattended runs), other transient artifacts. ai_todos moved OUT of here to `.claude/todos/` on 2026-07-15; treat any remaining `.for_bepy/ai_todos/` as unmigrated legacy.

## Persistence

- Before adding any persistence (localStorage / sessionStorage / cookies / IndexedDB / disk / DB), name the specific cross-refresh/close behavior it preserves; if you can't name it, don't persist - default to in-memory (Riverpod / context / useState / module-scope). When extending an existing persistence layer, re-check the pattern still matches the current UX. Why + past incident: `~/.claude/refs/persistence.md`.

## Subagent-Driven vs Inline Execution

Choose by task size when a plan is ready to execute:

- **Inline** (default): small features, fewer than 4 tasks, fewer than 3 files, tightly sequential. Just do it.
- **Subagent-driven**: large features with 5+ independent tasks across multiple files, where fresh context per task and review gates add real value.
- **Context-weight axis** (independent of size): even a job under 4 tasks warrants an Explore subagent when answering means reading material you discard once you have the conclusion (large files, wide grep sweeps, multi-query or iterative web research). Need the verdict, not the raw bytes. Read-only investigation; subagent-written code still follows the rule above.
  - **Web research specifically:** delegate any multi-query or iterative web search (research, comparisons, "how do people do X") to a subagent so raw result dumps never land in the main context; have it return the conclusion plus the source URLs. A single-fact lookup (one version check, one typosquat check) stays inline - the subagent round-trip isn't worth it there.

### Subagent model (cost control - MANDATORY)

Every subagent dispatch passes `model: 'sonnet'` explicitly. Never default-inherit the session model - inheriting Opus/Fable multiplies cost by N on fan-outs for no gain.

- **Sonnet is THE subagent model.** A well-written dispatch prompt (precise spec, file paths, constraints, report-back shape) is what determines subagent quality - and the orchestrator controls that, so sonnet doesn't get the chance to screw up open-ended judgment.
- **No haiku**: its failure modes cost more than the pennies it saves over sonnet.
- **Above sonnet (opus/fable): almost never.** Solo dispatch only, never a fan-out. Escalate only when:
  - a sonnet agent failed the exact task twice, or Joe explicitly asks; or
  - a sonnet report **smells wrong** - suspiciously clean, contradicts other evidence, zero findings on a big diff. Silent verifier misses never look like failures, so judgment is the trigger here; or
  - it's the FINAL verify/judge pass on a **high-stakes diff** (security-touching, data-loss-capable, DB migrations): one solo top-tier verifier is allowed there by default.
- Tune `effort` freely (low for mechanical chores, higher for review/verification angles) - it's the cheap knob; model tier is the expensive one.
- Past incident (2026-07-08): an 8-way code-review fan-out + verifiers all inherited Fable 5 and burned a painful chunk of Joe's tokens.
