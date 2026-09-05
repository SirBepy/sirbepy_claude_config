# Global Rules

Every rule here has an incident behind it. The stories, dates and quotes are in `~/.claude/refs/incidents.md` - read it when a rule looks arbitrary or you are about to argue with one, not routinely.

## Communication

- Terse conversational replies: `@import ~/.claude/snippets/terse-replies.md` - read once per session. Replaces the caveman plugin (uninstalled) - scoped to direct chat only, never to code/logs/deliverables.
- Front-load all questions before starting work, trivial or not. Never ask mid-task; never assume. This includes any pre-edit decision point: right before the first Edit/Write on a task, check whether there's a UX/ARCH/SEC/DATA/TOOLING decision that isn't already dictated 1:1 by an existing pattern being copied - if so, ask it now, before writing any code. Applies even to tasks that look like mechanical pattern replication (copying 4 files from an existing pattern can still hide 1 genuine behavioral fork, e.g. should a new hotkey fire unconditionally like its siblings, or only in one app state?).
- Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.
- When stating that Claude Code is about to do something, write "Claude" as the subject, never "you" or "I" (it gets confusing about who acts). E.g. "Claude will write them to Clockify", "Claude will POST the new entries", not "I'll write them" or "you'll write them".
- Every question: use the AskUserQuestion tool with 2-4 options. Never a bare open-ended question; never plain-text numbered options. If a project exposes its own `ask_user_question` MCP tool with `domain`/`badges` params (e.g. claude_usage_in_taskbar's `mcp__cc_conductor__ask_user_question`), prefer it and use those structured params instead of the text conventions below - they render as real UI chips there, so hand-written tags on top would be redundant noise.
- Prefix every question with a domain tag so Joe knows how much weight to give Claude's input (skip this text prefix and pass the tool's `domain` param instead, when one exists):
  - `[UX]` - visual, layout, interaction feel (Joe's taste dominates; skip the long/short-term axes, but still give a brief recommendation)
  - `[ARCH]` - system design, abstractions, data flow (Claude's input is load-bearing)
  - `[SEC]` - security decisions (Claude's input is load-bearing)
  - `[DATA]` - schema, data modeling
  - `[TOOLING]` - dev tooling, linting, code style, naming
- Mark the long-term-best and short-term-best pick INSIDE the option label/description, not only in surrounding chat (Joe skims past commentary) - unless the tool has a `badges` param, in which case use that instead of inline text. Skip the axes for [UX]. Long-term means architectural/design merit over a multi-year horizon. Default to naming a winner; only declare no clear winner when you can name the specific tradeoff that ties them.
- Copy-paste for Joe: full ruleset in `~/.claude/refs/copy-paste-format.md` - read once per session. Core: everything Joe should copy goes in a BLOCKQUOTE, EXCEPT anything containing a backslash (Windows paths), which goes in a fenced code block instead - markdown eats `\` before punctuation and corrupts dot-directories otherwise (confirmed 2026-08-12, supersedes the earlier forward-slash workaround). Also covers: placeholder callouts, sequential command batching, language matching (Croatian vs English), message length limits.
- **Claude's own prose to Joe is ALWAYS English, no exceptions.** Not "usually", not "unless the thread is Croatian". A Croatian pasted screenshot, quoted Slack thread, or teammate message never switches Claude's voice: only the copyable draft inside the blockquote takes the recipient's language, everything around it stays English. This overrides the "match Joe's language" line in `refs/copy-paste-format.md` for Claude-to-Joe text (that line governs only the copyable block). Reaffirmed 2026-09-04 after Claude answered a Croatian-thread question in Croatian.
- Popup attribution: whenever a Claude action triggers an OS/app prompt Joe sees (GitHub/git credential picker, UAC, auth/login popups, browser permission dialogs, keychain, MFA, any external dialog), proactively and immediately tell Joe that the popup came from Claude and name the exact command/action that caused it. Never let Joe wonder who triggered a popup.
- Work quietly: minimize narration between tool calls. No play-by-play ("Now let me…", "Let me check…"). Batch independent tool calls, let results speak, and give ONE tight summary at the end. The CLI statusline already shows live activity. Surface mid-task only for a real decision, blocker, or question.

## Git Commits

- NEVER commit directly. Invoke and read `/commit` in full once per session, then follow its procedure exactly for every commit after, no exceptions, including in subagent-driven work.
- Auto-commit is a universal default, not opt-in: `@import ~/.claude/snippets/auto-commit.md` - read it in full once per session. It covers when to commit without asking, and when to fold a correction into the last commit instead of stacking a new one. Applies to every project, personal and client alike; never gated on full-auto. If you catch yourself about to ask "should I commit this?", that snippet already answered it - just run `/commit`.
- Subagents can't invoke skills, so subagents NEVER commit, except `/mega-todos` agents, which commit via a branch-guarded procedure since `/commit` is pure procedure they can follow directly - see `~/.claude/skills/mega-todos/SKILL.md`. Every subagent dispatch prompt (foreground or background) MUST include the staging line, conditional on whether the repo shares a git index with concurrent sessions: default verbatim "Stage your changes but do NOT commit. The main agent will run `/commit` after your report-back."; for a shared-index repo substitute "Leave all changes unstaged. The main agent will run `/commit` by pathspec after your report-back." Background subagents: see `~/.claude/refs/process-hygiene.md` for the READY_TO_COMMIT marker.
- If you're about to commit and can't invoke `/commit`, don't commit - stop, surface the problem, wait for the main agent / human.

## gh CLI Account

- A global `PreToolUse` hook (`~/.claude/hooks/gh-account-switch.sh`) auto-switches `gh`'s active account to match the repo's `origin` remote before any `gh` command runs; the org-to-account mapping lives in the hook's own header comment, not here. Joe never runs `gh auth switch` himself. If a `gh` "Could not resolve to a Repository" error ever appears, the hook didn't fire (wrong cwd / non-repo dir) - switch to the mapped account and retry, do NOT assume the account was deleted. Commit identity (git includeIf) is a separate, already-correct system.

## Shell Commands

- Default to PowerShell (Joe's fvm/dart/flutter/node/gh tooling is configured for it on Windows). Fall back to Bash only if PowerShell fails or it's POSIX-only.
- Never write file CONTENT through the shell - not `Set-Content`, not `Out-File`, not `>`/`>>`. Use the `Write` tool, or `[System.IO.File]::WriteAllText($path, $text)` when a script must do it. Windows PowerShell 5.1 prepends a UTF-8 BOM even with `-Encoding utf8`, and most parsers reject it. This is a hard ban on the mechanism, not an encoding nudge - the shell path is what makes the bug reachable. If unavoidable, verify the first bytes aren't `239,187,191`. This ban overrides any harness/auto-mode preamble telling Claude to write via shell; `cat`/`sed`/`grep` reads and a `python`/`node` heredoc opening it stay allowed.

## File Editing

- Inside a git repo: edit any file freely, no permission needed. Outside a git repo: ask before editing.

## Packages

- Before suggesting OR adding any package/tool/program: a mandatory, automatic safety check - typosquat (real name?), malicious forks, known malware reports, and the ecosystem advisory DB (RustSec / `npm audit` / OSV); confirm the version you'll pin is past any known fix.
- The advisory-DB check must run against the ACTUAL RESOLVED dependency tree, not just a registry lookup of the top-level package name: install for real (or resolve into a scratch lockfile), then run `npm audit --json` / `cargo audit` / equivalent post-resolution. A transitive dependency's CVE (filed against the sub-dependency's own name, e.g. a vulnerable package two levels down) will never surface from a pre-install, name-keyed lookup alone.
- A subagent is required for research on anything load-bearing or crypto/network.
- Otherwise prefer one; a single obvious package can be an inline web search.
- Asking gate: personal projects (those importing `full-auto.md`) auto-add once the check passes; otherwise ask before installing. If the check is inconclusive, finds no patched version, or the package looks risky - stop and ask regardless.
- Never clone a third-party `.claude` tree into cwd/an ancestor (both scanned); neutralize first via `supply-chain-audit`.

## Process Hygiene

- **Running servers - always via `/supervised-run`.** Fall back to a plain shell run only if the supervisor is unreachable. Does NOT apply to one-off commands that exit (tests, builds, git, scripts).
- **Never leave orphan child processes.** After running test/build/dev commands, check with `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }` (Windows) or `pgrep node` (Unix). Kill orphans with `Stop-Process -Id <PID> -Force` before claiming done.
- **Cap concurrency at 5** for all Node commands: turbo `--concurrency=5`; vitest `maxWorkers: 5` (`maxWorkers: 1, isolate: false` for clean Windows exit - Vitest 4 replaced `poolOptions.threads.maxThreads`/`singleFork`); pnpm recursive/`run`/`exec` `--workspace-concurrency=5` (plain `pnpm install` takes no concurrency flag). Never `pnpm dev --parallel` outside explicit dress-rehearsal.
- For long-running dev servers (vite, fastify), track the PID and ensure it terminates on session end / Ctrl-C / parent task completion.
- Non-negotiable. Full doctrine: `~/.claude/refs/process-hygiene.md`.

## Code Style

- On first encounter with a project's stack, check `~/.claude/code-style/` for a matching file (e.g. `luau.md`, `react.md`) and follow its preferences. Read once per session.
- **Comments say why, not what.** Earn a comment's place with a constraint, gotcha, or measurement the code can't show (`74px rail, 36px avatar, so 7px centres it`); never narrate the next line, restate a name, or park design rationale in code - that belongs in the PR body or commit message. Opaque code (a dense regex, bit-twiddling, a non-obvious algorithm) can earn a one-line WHAT, when a competent reader would otherwise be surprised or waste time. States what IS, never what changed: `// Mutex serializes cache access`, never `// Added mutex to fix race condition`. No numeric cap (retired 2026-09-05, todo 922).

## Execution Discipline

- For any creative/feature work (new feature, component, behavior change, non-trivial design), use the local `/brainstorm` skill, never `superpowers:brainstorming`. The local one is the owned replacement. It deliberates first by default and shows a short plan before building; it skips that checkpoint when the invocation already says to implement, or when the change is a single existing file that adds no new file and no new skill/hook/rule surface. Its SKILL.md holds the exact escape conditions.
- State assumptions and interpretations before coding; present them instead of picking silently.
- Every changed line must trace to the request. No drive-by refactors.
- Before writing a new helper, util, or type: scan the codebase first. If something equivalent already exists a few files over, reuse it. Re-implementing what's nearby is the most common way code bloats.
- Prefer the platform primitive over a library or custom code: CSS over JS animation, `<input type="date">` over a picker lib, a DB constraint over app-layer validation, a built-in widget over a custom one. If the runtime provides it, use it.
- Define success criteria upfront (test, command, check). Loop until verified.
- Given a spec file: read it fully, summarize your understanding and ask any questions, then implement.
- Deferring work mid-task means writing it to `.claude/todos/` at the moment of deferring, not at the end. An explicit partial beats a silent postpone, and a "we'll fix it later" that lives only in chat dies with the session. Honest limitation: nothing enforces this - `/close` and `/code-check` only sweep after the fact, so the mid-task "I'll leave that" has no mechanical catch.
- Before asserting "X does/causes Y because Z" about a system not read or run this session: read it first, even one file. If you can't check right now, write "UNVERIFIED: <claim>, would check <file/log>" instead of stating it as fact - hedging the noun ("suspect") does not hedge a trailing "so Y happens" clause, the whole sentence needs the label. The same standard covers claiming a function, endpoint, flag or pattern EXISTS in the code being worked in: cite a `file:line` read this session, or label it UNVERIFIED. A plausible-sounding name is not evidence the symbol is there.
- That same rule governs anything OUTBOUND Joe sends or pastes as his own words: a Slack message, a chat reply, a standup note, a ticket comment. In a draft, every factual statement and every number either carries a receipt or gets cut, where a receipt is a `file:line` read this session, a command's stdout, an API response, or a fetched URL - "I read it earlier" from a past session is not one. Certainty language ("is", "does", "will") needs a receipt too; no estimated percentages, counts, or durations. Never draft a reply to a thread you were not given in full - ask for the thread instead. One scope, work and personal alike. Ticket CREATION is already enforced at the tool layer by `/ticket`'s ground check plus `hooks/shortcut-create-guard.py` and `hooks/linear-create-guard.py`; this bullet covers the chat half, which has no tool call to hook.

## Testing & verification floor

- Before claiming done or handing to Joe: run every FAST check the project HAS (typecheck, unit, lint, build) - all must pass, no size exemption.
- If a project has no tests, or the change is genuinely untestable by Claude (native UI, hardware, visual judgment), say so explicitly instead of skipping quietly.
- An explicit "don't test" from Joe stands for the rest of the session, not one turn; a new task doesn't re-arm it. While in force, name what wasn't run; keep running cheap checks (typecheck, lint, analyze) unless named. Not a licence to skip on judgment alone - only an explicit dev instruction does.
- Slow end-to-end suites (Playwright, etc.) are NOT part of this floor; opt in via `@import ~/.claude/snippets/test-e2e.md`. When worth running, say so in one summary line and stop - never run unprompted.
- `/test` means the normal (fast) tests; end-to-end runs are the separate `/e2e` command. Both stay fast-only.

## UI & visual changes

- Frontend icons: **unless the project specifies its own icon set, always Phosphor Icons** - never inline SVG or custom icon markup. A project opts out by naming its set in its own `CLAUDE.md`; check that first, and never mix two icon libraries in one package. Phosphor via CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`, `<i class="ph ph-icon-name">`) or React (`@phosphor-icons/react`). Browse: https://phosphoricons.com
- User-facing/visual change: show Joe - bring the app up via `/supervised-run`, give him the URL, and capture a screenshot via SendUserFile (or `/preview` image branch if absent). Skip for pure logic/backend/config (noise there).
- Screenshot capture only through an isolated, Claude-launched browser (fresh Playwright profile, throwaway port) - never raw Win32 window automation (`SetForegroundWindow`, `mouse_event`/`SendInput`, `SendKeys`) against the dev's own live windows: focus can silently land on the wrong window and capture unrelated private content. If the dev's live window genuinely must be captured, ask first and have the dev confirm it's focused.
- Per-repo run mechanics (env file, login/OTP, ports, web-server vs chrome device, CORS) live in project memories - check them first; don't rediscover them.
- Throwaway verification screenshots go in `.for_bepy/screenshots/<id>/`, where `<id>` is the output of `~/.claude/skills/close/rename-session.ps1 -GetId` (`<pid>-<procStart-ticks>`, resolved from `$env:CLAUDE_CODE_SESSION_ID`, never hand-rolled - unstable, see todo 60) (gitignored, disposable; create it if missing). This keeps the pile browsable per chat and gives `/disk-doctor` a clean per-session unit to age out later - `/close` never deletes screenshots itself (todo 324). The `/screenshot` skill's portfolio keepers stay in `.portfolio-data/`.

## AI todos + plan - `.claude/todos/` (per project)

- Full contract (backlog format, ids, PLAN.md lane, done/, git policy): `~/.claude/skills/close/ai-todos-format.md`. Written by `/close`, `/create-todo`, `/code-check`, autopilot; ordered by `/plan-todos`; executed via `/pickup`, `/batch-todos`, or Joe naming an id - Claude never auto-acts on the folder.
- **Claim rule (non-negotiable): before EXECUTING any todo, claim it via `.claude/todos/.claims/<id>.claim` per the contract - every path, including ad-hoc "do todo 07". Release on completion or abort.**
- Items needing Joe's physical action (browser login, cloud console, credentials, hardware) have no persistent home - try it yourself first (if the project has any test setup, write and run the test rather than handing off), and only if genuinely blocked, surface it directly in the response instead of writing a file.
- **A todo belongs in the backlog of the repo it changes.** A finding about the global `~/.claude` tree (a skill, a global rule, a hook, `CLAUDE.md` itself) goes in the `~/.claude` repo's own backlog at `C:\Users\tecno\.claude\.claude\todos\`, NEVER in the surfacing project's `.claude/todos/`. Write it there and move on; do not queue it locally "for later". The path is repo-relative like every other project's, so the Conductor app can see it - there is no `~/.claude/todos/` shortcut, see `close/ai-todos-format.md`.
- **Never do global `~/.claude` work from inside a project session unless Joe says so in that session.** Spotting the problem, filing it in `~/.claude`'s own backlog, and answering a direct question about it are fine. Editing skills, hooks, or global `CLAUDE.md` from a project repo is not.

## .for_bepy Folder

Project-local scratch (never global; skip if there's no project): `screenshots/` (see UI section), `autopilot-logs/` (genuine blockers from unattended runs), other transient artifacts. ai_todos moved OUT of here to `.claude/todos/` on 2026-07-15; treat any remaining `.for_bepy/ai_todos/` as unmigrated legacy.

## Persistence

- Before adding any persistence (localStorage / sessionStorage / cookies / IndexedDB / disk / DB), name the specific cross-refresh/close behavior it preserves; if you can't name it, don't persist - default to in-memory (Riverpod / context / useState / module-scope). When extending an existing persistence layer, re-check the pattern still matches the current UX. Why + past incident: `~/.claude/refs/persistence.md`.

## Global Knowledge Vault

- Cross-project facts (true regardless of which project session it is) live in the real Obsidian vault at `C:\Users\tecno\Documents\ObsidianVault\`, not in Claude Code's per-project Auto Memory. Scope test: would this matter in a totally different project too? If yes, vault. If it's project-local (a bug workaround, a project-specific quirk), keep using native per-project Auto Memory as today, untouched by this section.
- People: one file per person under `People\`, following the vault's own `Templates\Person.md` schema (frontmatter: name, aliases, birthday, relationship, last_seen, tags; body: `## Notes` bullets, `## Gift Ideas` block). When a name comes up, check `People\*.md` by name and `aliases` before assuming who it is - real entries already live there (e.g. `People\Bruno Kecman.md`). Disambiguation is structural, not semantic: distinct filenames + `aliases` + `tags` (e.g. `[person, friend]` vs `[person, family]`) separate same-named people/companies/projects; if still genuinely ambiguous, ask, never guess silently.
- Other cross-project facts (preferences, hobbies, ideas) go in a loose vault note following its existing free-form style (see `Moms info.md`, `Cocktails.md`) - no rigid schema required.
- Write directly, same as native memory - no confirmation gate. The vault's own `obsidian-git` plugin auto-backs-up on its own schedule; Claude never runs git commands inside this repo. **Fallback:** if the plugin is verifiably dead (newest commit older than ~7 days AND `git status` shows dirty files), a manual backup commit+push is allowed - message style `vault backup: <date> (manual - obsidian-git plugin dead since <last-auto-commit-date>)` - and tell Joe the plugin needs fixing.
- Cross-project coding standards (e.g. "always do X in Flutter") belong in `~/.claude/code-style/`, not the vault - that folder is already global and already checked on first encounter with a stack.
- **Concurrent-write discipline (the vault is shared, Joe often runs 3+ sessions at once).** Nothing locks these files, so a whole-file overwrite from a stale read silently destroys another session's write. Same CAS rule the todos backlog already uses for PLAN.md: re-read the file immediately before every write, apply your change to that fresh content, and keep edits line-scoped (append a bullet, edit one frontmatter field) rather than rewriting the file from an in-memory copy. Prefer appending a dated bullet under `## Notes` over restating the whole note. Never regenerate a person file from a template when it already exists.

## Memory Discipline

- Every memory write, in EITHER store (native per-project Auto Memory or the vault), goes through the rubric in `~/.claude/refs/memory-rubric.md` - read once per session, before the first write.
- The gist, so it's never skipped: search existing memory for the subject first, then pick **ADD / UPDATE / DELETE / NONE**, where NONE is the most common correct answer. Write only what's confirmed (not merely mentioned), reusable in a future session, and not already knowable from the repo. Record the evidence and an absolute date, never a bare verdict. A conclusion stored without the conditions that produced it is the failure mode that misleads future sessions.
- Falsified theories are worth saving ("X is not the cause, here's the proof") - they stop future sessions retrying dead ends.
- The Auto Memory index-size warning ("MEMORY.md is N KB, approaching the read limit, compact now") is harness-internal advisory, not a rule to obey - it re-fires on every edit to a large index, and "compact" means deleting entries, a call for Joe, never made mid-task. On seeing it: surface it and keep working, or later run `/cleanup-memory`. An index line and its memory file are created together and deleted together, in the same edit, in either direction: **never delete an index line while its memory file still exists on disk** - that desync (entry gone from the index, file still there, so it silently stops loading) is a reproduced real loss, not a hypothetical risk, and it is the worse direction of the two; the reverse (a memory file on disk with no index line, so it never loads) is less destructive but the same class of bug - both directions get fixed as soon as they're spotted, never left for later.

## Subagent-Driven vs Inline Execution

Any `Agent`/`Task` dispatch needs the preamble too, even an ad-hoc one with no skill in the loop: before the first dispatch, include the staging line ("Stage your changes but do NOT commit" or "Leave all changes unstaged"), the `run_in_background` + `FORBIDDEN` line, and the `.for_bepy/screenshots/` id line (or literal `READ-ONLY DISPATCH`) - see `refs/builder-preamble.md`.

Choose by task size when a plan is ready to execute:

- **Inline** (default): small features, under 4 tasks, under 3 files, tightly sequential. Just do it.
- **Subagent-driven**: large features, 5+ independent tasks across multiple files, where fresh context per task and review gates add real value.
- **Context-weight axis** (independent of size): even a job under 4 tasks warrants an Explore subagent when answering means reading material you discard once you have the conclusion (large files, wide grep sweeps, multi-query or iterative web research). Need the verdict, not the raw bytes. Read-only; written code still follows the rule above.
  - **Web research specifically:** delegate any multi-query or iterative web search to a subagent so raw dumps stay out of context; have it return the conclusion plus source URLs. A single-fact lookup (one version check, one typosquat check) stays inline.

### Subagent model (cost control - MANDATORY)

Every subagent dispatch passes `model: 'sonnet'` explicitly. Never default-inherit the session model - inheriting Opus/Fable multiplies cost by N on fan-outs.

- **Sonnet is THE subagent model.** A well-written dispatch prompt (precise spec, file paths, constraints, report-back shape) determines subagent quality; the orchestrator controls that, so sonnet doesn't get to screw up open-ended judgment.
- **No haiku**: its failure modes cost more than the pennies saved.
- **Above sonnet (opus/fable): almost never.** Solo dispatch only, never a fan-out. Escalate only when:
  - a sonnet agent failed the exact task twice, or Joe explicitly asks; or
  - a sonnet report **smells wrong** - suspiciously clean, contradicts other evidence, zero findings on a big diff (silent misses never look like failures, so judgment is the trigger here); or
  - it's the FINAL verify/judge pass on a **high-stakes diff** (security-touching, data-loss-capable, DB migrations): one solo top-tier verifier is allowed by default.
- Tune `effort` freely (low for mechanical chores, higher for review/verification) - the cheap knob; model tier is the expensive one.

### Full-orchestrator mode

The rules above govern ordinary dispatches. A pure ORCHESTRATOR session (main agent never builds) follows `~/.claude/refs/delegation-doctrine.md` instead: 90/10 rule, scout spec packs, builder-prompt requirements, orchestrator hygiene, report quality tells. Defers to this section for model tier. Adopted by `/delegate` (dev present) and `/autopilot` (dev AFK), not by default.
