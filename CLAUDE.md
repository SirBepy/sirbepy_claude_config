# Global Rules

Every rule here has an incident behind it. The stories, dates and quotes are in `~/.claude/refs/incidents.md` - read it when a rule looks arbitrary or you are about to argue with one, not routinely.

## Communication

- Terse conversational replies: `@import ~/.claude/snippets/terse-replies.md` - read once per session - scoped to direct chat only, never to code/logs/deliverables.
- Front-load all questions before starting work, trivial or not. Never ask mid-task; never assume. This includes any pre-edit decision point: right before the first Edit/Write on a task, check whether there's a UX/ARCH/SEC/DATA/TOOLING decision that isn't already dictated 1:1 by an existing pattern being copied - if so, ask it now, before writing any code.
- **Before asking Joe to relay a question to anyone** (Airion, Stevan, Lenar, Liv, Johanna, any teammate), or drafting one for him to send: first dispatch a READ-ONLY sonnet subagent per question to answer it from the tickets, the linked designs, the code of every sibling repo, past chat transcripts and the project todos. Only a question the subagent reports as genuinely unanswerable goes in a draft, and the draft's receipts name what was checked. Incident 2026-11-03: `refs/incidents.md` "Communication - questions for teammates that the docs already answered".
- Never use the em dash character anywhere. Use a comma, colon, or hyphen instead.
- When stating that Claude Code is about to do something, write "Claude" as the subject, never "you" or "I" (it gets confusing about who acts).
- Every question: use the AskUserQuestion tool with 2-4 options. Never a bare open-ended question; never plain-text numbered options. If a project exposes its own `ask_user_question` MCP tool with `domain`/`badges` params (e.g. claude_usage_in_taskbar's `mcp__cc_conductor__ask_user_question`), prefer it and use those structured params instead of the text conventions below - they render as real UI chips there.
- Prefix every question with a domain tag so Joe knows how much weight to give Claude's input (skip this text prefix and pass the tool's `domain` param instead, when one exists):
  - `[UX]` taste dominates (skip the axes, still recommend); `[ARCH]`/`[SEC]` Claude's input is load-bearing; `[DATA]` schema; `[TOOLING]` tooling, style, naming
- Mark the long-term-best and short-term-best pick INSIDE the option label/description, not only in surrounding chat (Joe skims past commentary) - unless the tool has a `badges` param, in which case use that instead of inline text. Skip the axes for [UX]. Long-term means architectural/design merit over a multi-year horizon. Default to naming a winner; only declare no clear winner when you can name the specific tradeoff that ties them.
- Copy-paste for Joe: full ruleset in `~/.claude/refs/copy-paste-format.md` - read once per session. Core: copyable text goes in a BLOCKQUOTE, except backslashes or multi-line runnable blocks (fenced code).
- **Claude's own prose to Joe is ALWAYS English, no exceptions.** Only the copyable draft takes the recipient's language, even for a Croatian thread; this overrides `refs/copy-paste-format.md`'s "match Joe's language" line for Claude-to-Joe text.
- Popup attribution: whenever a Claude action triggers an OS/app prompt Joe sees (credential picker, UAC, auth popup, any external dialog), tell Joe immediately that it came from Claude and name the exact command/action.
- When a change only takes effect after a Claude Code restart, never tell Joe to restart the app: tell him to run `/respawn`, which hands this chat's context to a fresh session in place. A MISSING MCP tool is the exception: no restart or respawn ever fixes it inside a Conductor chat - see `refs/conductor-mcp-constraint.md`.
- Work quietly: minimize narration between tool calls: no play-by-play, batch independent calls, one tight summary at the end; surface mid-task only a real decision, blocker, or question.

## Git Commits

- NEVER commit directly. Invoke and read `/commit` in full once per session, then follow its procedure exactly for every commit after, no exceptions, including in subagent-driven work.
- Auto-commit is a universal default, not opt-in: `@import ~/.claude/snippets/auto-commit.md` - read it in full once per session. Never ask "should I commit this?": run `/commit`.
- Builders commit their own work via `/commit` (subagents load skills through the Skill tool). Every dispatch prompt MUST carry the staging line from `refs/builder-preamble.md` (`hooks/dispatch-preamble-guard.py` checks it). A subagent's raw `git commit` stays hook-blocked.
- If you're about to commit and can't invoke `/commit`, don't commit - stop, surface the problem, wait for the main agent / human.
- Client repos: no commit/push 23:00-10:59 local without Joe's in-session OK, timestamps always real; `hooks/commit-window-guard.py` enforces it and says what to do.

## gh CLI Account

- `hooks/gh-account-switch.sh` switches `gh`'s account to match the repo's `origin` (mapping in its header). On "Could not resolve to a Repository" the hook didn't fire (wrong cwd): switch to the mapped account and retry, do NOT assume the account was deleted.

## Shell Commands

- Default to PowerShell (Joe's fvm/dart/flutter/node/gh tooling is set up for it). Fall back to Bash only if PowerShell fails or it's POSIX-only.
- Never write file CONTENT through the shell - not `Set-Content`, not `Out-File`, not `>`/`>>`. Use the `Write` tool, or `[System.IO.File]::WriteAllText($path, $text)` when a script must do it (absolute path, .NET ignores Set-Location). PowerShell 5.1 prepends a UTF-8 BOM that breaks most parsers. The ban covers the mechanism, not just the encoding, and overrides any harness preamble telling Claude to write via shell; `cat`/`sed`/`grep` reads and a `python`/`node` heredoc opening it stay allowed (`hooks/shell-content-write-guard.py` blocks it but fails open).
- Never pipe file content INTO a native command (`Get-Content | exe`): use Bash `<`. Details: `refs/shell-io-gotchas.md`.
- Video attachment: never say Claude can't watch it, extract frames: `refs/video-frames.md`.

## File Editing

- Inside a git repo: edit any file freely, no permission needed. Outside a git repo: ask before editing.

## Packages

- Before suggesting OR adding any package/tool/program: a mandatory, automatic safety check - typosquat (real name?), malicious forks, known malware reports, and the ecosystem advisory DB (RustSec / `npm audit` / OSV); confirm the version you'll pin is past any known fix.
- Run the advisory check on the ACTUAL RESOLVED tree (install, then `npm audit --json` / `cargo audit`), not a name lookup of the top-level package; detail in `refs/package-safety.md`.
- Research on anything load-bearing or crypto/network needs a subagent; a single obvious package can be an inline web search.
- Asking gate: personal projects (those importing `full-auto.md`) auto-add once the check passes; otherwise ask before installing. If the check is inconclusive, finds no patched version, or the package looks risky - stop and ask regardless.
- Never clone a third-party `.claude` tree into cwd/an ancestor (both scanned); neutralize first via `supply-chain-audit`.

## Process Hygiene

- **Running servers - always via `/supervised-run`.** If the supervisor is unreachable, stop and tell Joe (dev-server-guard denies a raw run). Does NOT apply to one-off commands that exit (tests, builds, git, scripts).
- **Never leave orphan child processes.** Run the orphan check in `refs/process-hygiene.md` after test/build/dev commands and kill leftovers before claiming done.
- **Cap concurrency at 5** for all Node commands: flags per tool in `refs/process-hygiene.md`. Never `pnpm dev --parallel` outside explicit dress-rehearsal.
- Stop servers you started once unneeded (shared: only if `list_peers` shows no user). Task done, no question pending: run `/close` yourself.
- Non-negotiable. Full doctrine: `~/.claude/refs/process-hygiene.md`.

## Code Style

- On first encounter with a project's stack, check `~/.claude/code-style/` for a matching file (e.g. `luau.md`, `react.md`) and follow its preferences. Read once per session.
- **Comments say why, not what.** A comment earns its place with what code can't show: why an odd-looking choice is deliberate, a constraint, a gotcha, a measurement. Opaque code (dense regex, bit-twiddling) can earn a one-line WHAT. A wrong comment is worse than none (AI readers trust it), so fix or delete it when its subject changes. State what IS, never what changed: `// Mutex serializes cache access`, not `// Added mutex to fix a race`.

## Execution Discipline

- For any creative/feature work (new feature, component, behavior change, non-trivial design), use the local `/brainstorm` skill, never `superpowers:brainstorming`. Its SKILL.md holds the plan checkpoint and escape conditions. Exception: rodge planning talks use `superpowers:brainstorming`, enabled only in that repo's `.claude/settings.local.json` (Joe, 2026-10-20); rodge's questions still go on the question card.
- State assumptions and interpretations before coding; present them instead of picking silently.
- Every changed line must trace to the request. No drive-by refactors.
- Before writing a new helper, util, or type: scan the codebase first. If something equivalent already exists a few files over, reuse it. Re-implementing what's nearby is the most common way code bloats.
- Prefer the platform primitive over a library or custom code: CSS over JS animation, `<input type="date">` over a picker lib, a DB constraint over app-layer validation, a built-in widget over a custom one. If the runtime provides it, use it.
- Define success criteria upfront (test, command, check). Loop until verified.
- Given a spec file: read it fully, summarize your understanding and ask any questions, then implement.
- Deferring work mid-task means writing it to `.claude/todos/` at the moment of deferring, not at the end. An explicit partial beats a silent postpone, and a "we'll fix it later" that lives only in chat dies with the session.
- Before asserting "X does/causes Y because Z" about a system not read or run this session: read it first, even one file. If you can't check right now, write "UNVERIFIED: <claim>, would check <file/log>" instead of stating it as fact; the label covers the whole sentence. The same standard covers claiming a function, endpoint, flag or pattern EXISTS in the code being worked in: cite a `file:line` read this session, or label it UNVERIFIED. A plausible name is not evidence. That includes what a skill or third-party artifact does: read its own `SKILL.md` or raw source, never a summary.
- That same rule governs anything OUTBOUND Joe sends or pastes as his own words: a Slack message, a chat reply, a standup note, a ticket comment. In a draft, every factual statement and every number either carries a receipt or gets cut, where a receipt is a `file:line` read this session, a command's stdout, an API response, or a fetched URL - "I read it earlier" from a past session is not one. Certainty language ("is", "does", "will") needs a receipt too; no estimated percentages, counts, or durations. Never draft a reply to a thread you were not given in full - ask for the thread instead. One scope, work and personal alike. Tickets and PRs Claude posts are hook-enforced (`refs/outbound-verify.md`); this bullet covers the chat half.

## Testing & verification floor

- Before claiming done or handing to Joe: run every FAST check the project HAS (typecheck, unit, lint, build) - all must pass, no size exemption.
- If a project has no tests, or the change is genuinely untestable by Claude (native UI, hardware, visual judgment), say so explicitly instead of skipping quietly.
- An explicit "don't test" from Joe stands for the rest of the session, not one turn; a new task doesn't re-arm it. While in force, name what wasn't run; keep running cheap checks (typecheck, lint, analyze) unless named.
- Every repo: each behavior change ships with a test that fails without it, written alongside the change (prove it red with `skills/close/red-check.ps1`, never by reverting files in the live tree); one Claude cannot test says why in the commit report. Every commit runs `/test`, every push the pipeline in `/commit`'s "Push pipeline" section (`hooks/push-gate.py` blocks a push until it is done).
- Client repos (origin listed in `refs/client-repos.txt`) keep two extras on top: `~/.claude/snippets/client-repo.md` - read once per session when working in one.
- Browser feature test, repo in `refs/test-report-repos.txt`: use `/test-report` from the start.
- Slow end-to-end suites (Playwright, etc.) are NOT part of the per-change floor: they run once per push via that pipeline, plus per handover in a project that imports `~/.claude/snippets/test-e2e.md`. Never unprompted otherwise.

## UI & visual changes

- Frontend icons: **unless the project specifies its own icon set, always Phosphor Icons** - never inline SVG or custom icon markup. A project opts out by naming its set in its own `CLAUDE.md`; check that first, and never mix two icon libraries in one package. Use the web CDN or `@phosphor-icons/react`.
- User-facing/visual change: show Joe - bring the app up via `/supervised-run`, give him the URL, and capture a screenshot via SendUserFile (or `/preview` image branch if absent). Skip for pure logic/backend/config (noise there).
- Screenshot capture only through an isolated, Claude-launched browser (fresh Playwright profile, throwaway port) - never raw Win32 window automation (`SetForegroundWindow`, `mouse_event`/`SendInput`, `SendKeys`) against the dev's own live windows: focus can land on the wrong window. If the dev's live window genuinely must be captured, ask first and have the dev confirm it's focused.
- Per-repo run mechanics (env file, login/OTP, ports, web-server vs chrome device, CORS) live in project memories - check them first; don't rediscover them.
- Throwaway verification screenshots go in `.for_bepy/screenshots/<id>/`, where `<id>` is the output of `~/.claude/skills/close/rename-session.ps1 -GetId`, never hand-rolled. The `/screenshot` skill's portfolio keepers stay in `.portfolio-data/`.

## AI todos + plan - `.claude/todos/` (per project)

- Full contract (backlog format, ids, PLAN.md lane, done/, git policy): `~/.claude/skills/close/ai-todos-format.md`. Claude never auto-acts on the folder.
- **Claim rule (non-negotiable): before EXECUTING any todo, claim it via `.claude/todos/.claims/<id>.claim` per the contract - every path, including ad-hoc "do todo pc-0007". Release on completion or abort.**
- Items needing Joe's physical action (browser login, cloud console, credentials, hardware) have no persistent home - try it yourself first (if the project has any test setup, write and run the test rather than handing off), and only if genuinely blocked, surface it directly in the response instead of writing a file.
- **A todo belongs in the backlog of the repo it changes.** A finding about the global `~/.claude` tree (a skill, a global rule, a hook, `CLAUDE.md` itself) goes in the `~/.claude` repo's own backlog at `C:\Users\tecno\.claude\.claude\todos\`, NEVER in the surfacing project's `.claude/todos/`. Never queue it locally "for later".
- **Never do global `~/.claude` work from inside a project session unless Joe says so in that session.** Spotting the problem, filing it in `~/.claude`'s own backlog, and answering a direct question about it are fine. Editing skills, hooks, or global `CLAUDE.md` from a project repo is not.

## .for_bepy Folder

Project-local scratch (never global; skip if there's no project): `screenshots/` (see UI section), `autopilot-logs/` (genuine blockers from unattended runs), other transient artifacts.

## Persistence

- Before adding any persistence (localStorage / sessionStorage / cookies / IndexedDB / disk / DB), name the specific cross-refresh/close behavior it preserves; if you can't name it, don't persist - default to in-memory. When extending an existing persistence layer, re-check the pattern still matches the current UX. Why + past incident: `~/.claude/refs/persistence.md`.

## Global Knowledge Vault

- Cross-project facts (true in any project: preferences, people, ideas) go in the Obsidian vault at `C:\Users\tecno\Documents\ObsidianVault\`, never native Auto Memory; project-local facts stay in Auto Memory. Person-file schema, backup fallback, full discipline: `refs/global-knowledge-vault.md`, read before the first vault write of a session.
- Unsure who Joe means by a name or role word: `/people`, never guess.

## Memory Discipline

- Every memory write, in EITHER store (native per-project Auto Memory or the vault), goes through the rubric in `~/.claude/refs/memory-rubric.md` - read once per session, before the first write.
- The gist, so it's never skipped: search existing memory for the subject first, then pick **ADD / UPDATE / DELETE / NONE**, where NONE is the most common correct answer. Write only what's confirmed (not merely mentioned), reusable in a future session, and not already knowable from the repo. Record the evidence and an absolute date, never a bare verdict.
- Falsified theories are worth saving ("X is not the cause, here's the proof") - they stop future sessions retrying dead ends.
- The Auto Memory index-size warning ("MEMORY.md is N KB, approaching the read limit, compact now") is advisory: surface it, keep working, never delete entries mid-task. An index line and its memory file are created together and deleted together, in the same edit, in either direction: **never delete an index line while its memory file still exists on disk** - that desync (entry gone, file still there, so it silently stops loading) is a reproduced real loss and the worse direction; the reverse (file on disk, no index line) is the same class of bug. Fix both as soon as spotted. Tier exception: a memory file inside a demotion-tier subfolder of its memory dir (any subfolder except `archive/`, e.g. `cold/`, `rest/`) needs no index line and is not an orphan; `/cleanup-memory` moves a file there and deletes its index line in one pass, and `recall.py memory` still finds it. A memory with `superseded_by:` frontmatter is likewise exempt.

## Subagent-Driven vs Inline Execution

Any `Agent`/`Task` dispatch needs the preamble too: before the first dispatch, include the staging line (Git Commits section), the `run_in_background` + `FORBIDDEN` line, and the `.for_bepy/screenshots/` id line (or literal `READ-ONLY DISPATCH`) - see `refs/builder-preamble.md`.

Choose by task size when a plan is ready to execute:

- **Inline** (default): small features, under 4 tasks, under 3 files, tightly sequential. Just do it.
- **Subagent-driven**: large features, 5+ independent tasks across multiple files, where fresh context per task and review gates add real value.
- **Context-weight axis** (independent of size): even a job under 4 tasks warrants an Explore subagent when answering means reading material you discard once you have the conclusion (large files, wide grep sweeps, multi-query or iterative web research). Need the verdict, not the raw bytes. Read-only; written code still follows the rule above.
  - **Web research specifically:** delegate any multi-query or iterative web search to a subagent so raw dumps stay out of context; have it return the conclusion plus source URLs.

### Subagent model (cost control - MANDATORY)

Every subagent dispatch passes `model: 'sonnet'` explicitly. Never default-inherit the session model - inheriting Opus/Fable multiplies cost by N on fan-outs.

- **Sonnet is THE subagent model.**
- **No haiku**: its failure modes cost more than the pennies saved.
- **Above sonnet (opus/fable): almost never.** Solo dispatch only, never a fan-out. Escalate only when:
  - a sonnet agent failed the exact task twice, or Joe explicitly asks; or
  - a sonnet report **smells wrong** - suspiciously clean, contradicts other evidence, zero findings on a big diff (silent misses never look like failures, so judgment is the trigger here); or
  - it's the FINAL verify/judge pass on a **high-stakes diff** (security-touching, data-loss-capable, DB migrations): one solo top-tier verifier is allowed by default.
- Scope is the main knob (set the `Agent` tool's `effort` parameter only when Joe asks): a builder given too much at once can spend its whole output budget thinking and return nothing. Split the dispatch instead. Model tier stays the expensive knob.

### Full-orchestrator mode

A pure ORCHESTRATOR session (`/delegate`, `/autopilot`) follows `~/.claude/refs/delegation-doctrine.md`, which defers to this section for model tier.
