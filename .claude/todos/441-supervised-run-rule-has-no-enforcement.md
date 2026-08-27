<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=8, reconfirm-count=1, content-hash=95fe2636 -->
<!-- duplicate-checked -->
# The /supervised-run rule is prose, so a raw dev server in Bash is unblocked

**Type:** task
**Origin:** ai

## Goal

Block long-lived dev servers started directly in a shell tool, so the `/supervised-run` rule is
enforced rather than remembered.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

CLAUDE.md's Process Hygiene section says long-lived servers always route through `/supervised-run`,
calls it non-negotiable, and points at `refs/process-hygiene.md` for the full three-layer doctrine.
None of that is enforced. A raw `npm run dev`, `vite`, `flutter run` or `uvicorn` in the Bash or
PowerShell tool works today, and the consequence is documented in this repo's own history: **90+ orphan
vitest processes once pegged the CPU at 100% and 90 degrees C.**

The doctrine's own three layers are prose, a `run_in_background` ban restated in every builder dispatch
prompt, and an orphan-check instruction. The harvest's repeated lesson is that prose-only rules fail
here: the em-dash ban needed a Stop hook after breaking three times despite being restated verbatim in
every dispatch of the run that broke it, and the unverified-mechanism rule recurred five times.

Reference: `repos/rohitg00_awesome-claude-code-toolkit/hooks/scripts/block-dev-server.js`. A PreToolUse
hook hard-blocking `npm run dev`, `vite`, `uvicorn` and similar when run directly in Bash **unless
inside tmux or screen**. That escape condition is the interesting part: it does not ban the command, it
requires the command to run somewhere supervised.

The direct translation here is cleaner than tmux, because `/supervised-run` already exists and routes
through `server_supervisor`. So the guard's escape condition is "the process is being started by the
supervisor", not "the process is inside a terminal multiplexer".

Design questions to settle, in order of how much they decide the outcome:

1. **How does the hook tell a supervisor-launched process from a raw one?** If `/supervised-run` invokes
   the server through a wrapper, the hook can match the wrapper's command shape. If it uses an env var
   or a marker, match that. This is the crux: without a reliable distinguisher the guard either blocks
   the supervisor itself or blocks nothing.
2. **What counts as long-lived?** The rule explicitly exempts one-off commands that exit (tests, builds,
   git, scripts), and `npm test` versus `npm run dev` is a script-name distinction, not a command-shape
   one. A naive `npm run` match would block the entire test floor.
3. `deny` or `ask`? The rule says non-negotiable, which argues for `deny`. But a false positive on a
   legitimate one-off would be severe, so the distinguisher in (1) needs to be solid before choosing
   `deny`.

Related existing guard to model on rather than duplicate: there is already a package-manager guard
(todo 76, in `done/`) that inspects Bash commands, so the command-parsing shape is established in this
codebase.

## Approach

1. Read `skills/supervised-run/SKILL.md` and however it invokes `server_supervisor`, and establish the
   reliable distinguisher for a supervised launch. **Do this before writing any pattern.** If no
   reliable marker exists, adding one to `/supervised-run` is part of this todo.
2. Read the existing package-manager guard for the command-parsing conventions already used here.
3. Build the long-lived-command list from what this machine actually runs: `vite`, `next dev`,
   `npm run dev`, `pnpm dev`, `flutter run`, `dart run` for servers, `uvicorn`, `fastify`, and the
   Tauri dev command. Explicitly exclude the test and build paths named in the process-hygiene rule.
4. Handle both shells. Bash and PowerShell are both available here and the guard must match either,
   or explicitly scope itself and say which is uncovered.
5. Choose `deny` only if step 1 produced a solid distinguisher; otherwise `ask` with a message naming
   `/supervised-run` by name so the fix is obvious.
6. Fixture tests, with the negatives carrying the weight: `npm test` must pass, `npm run build` must
   pass, a supervisor-launched `vite` must pass, a raw `vite` must be caught.

## Acceptance

- The supervised-versus-raw distinguisher is identified and stated. If one had to be added to
  `/supervised-run`, that change is included.
- A raw `npm run dev` is caught; `npm test` and `npm run build` are not.
- A real supervisor launch is proven to pass, not assumed.
- Both Bash and PowerShell are covered, or the uncovered one is named.
- Fixture tests pass with real output, negatives included.

## Notes

The distinguisher is the whole todo. Everything else is a pattern list. A guard that cannot tell the
supervisor from a raw launch will either block `/supervised-run` itself or be trivially bypassed, and
both outcomes end with it disabled.

Do not add a `run_in_background` guard here as well. That ban is subagent-scoped and belongs with
todo 434's per-agent hook work, not in a globally-wired server guard.
