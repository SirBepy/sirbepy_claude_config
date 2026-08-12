<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Delegation doctrine should require restating relevant project-memory facts in dispatch prompts

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop subagents burning full runs rediscovering environment facts that are already recorded in
project memory, by making the dispatch checklist name memory explicitly.

## Provenance

Originally filed inside the Hubbub project backlog as
`hubbub/.claude/todos/34-restate-project-memory-facts-in-dispatch-prompts.md`. That was the wrong
home: the change targets `~/.claude/refs/delegation-doctrine.md`, which is global tooling, and the
global rule is that findings about the `~/.claude` tree never sit in a project backlog. Relocated
here by an `/auto-do-todos` run on 2026-08-08. The Hubbub copy was archived to its `done/` folder
with a pointer to this file; nothing was lost.

## Context

`~/.claude/refs/delegation-doctrine.md`, under "Every builder prompt embeds, without exception",
lists what a dispatch must restate: the verify floor, the no-commit line, "the load-bearing global
rules it needs, restated: PowerShell on Windows, never chain commands with `&&` / `;` / `|`, the
working directory", the screenshot path, the orphan check, and the no-background line. It closes
that item with "Subagents do not inherit session context."

That last sentence is true of PROJECT MEMORY too, but memory is never named, so it gets skipped.

**Incident, 2026-08-05 (Hubbub cloud-hosting session).** A subagent was dispatched to repair the
`capture` skill and then verify a change in a real browser. It repaired the skill, then failed the
browser half entirely, reporting that Playwright had no Chromium installed and that the
chrome-devtools MCP could not attach. It spent a long run on that wall and returned half done.

The workaround was already in project memory, in `hubbub-local-dev-and-testing`: "Playwright's
downloaded browsers are not dependable; `channel: \"chrome\"` is (2026-08-05) ...
`chromium.launch({ channel: \"chrome\" })` drives Joe's installed Chrome with no download and worked
immediately. Prefer the channel over a pinned path." The orchestrator had read that memory and did
not pass it. Every subsequent dispatch in that session included the line verbatim and none hit the
problem again.

The same session had a second, related near-miss: a dispatch forbade adding a workspace dependency
and touching a sibling app, which forced the subagent to leave a real defect in place (a typed room
code silently dropped, making the user enter it twice). That is a different failure, over-constraint
rather than under-informing, but both come from the orchestrator writing the prompt without checking
what the subagent would need to know or be allowed to do.

**Positive control, 2026-08-08.** An `/auto-do-todos` run on Hubbub embedded a restated
project-memory block in all seven dispatches (the Chrome channel, the Vite stale-shadow trap, the
fixed ports, the never-bare-`pnpm dev` rule, the apps/web-is-only-glue fact). Zero agents hit any of
those walls. That is weak evidence on its own, since it is one session, but it is the shape the
doctrine change is trying to make routine rather than a thing an orchestrator happens to remember.

## Approach

Edit `~/.claude/refs/delegation-doctrine.md`, in the "Every builder prompt embeds, without
exception" list. Add an item along these lines:

- Any PROJECT MEMORY fact the task depends on, quoted or paraphrased inline. Subagents inherit no
  memory at all, so an environment quirk, a known-broken tool, a working workaround, or a past
  incident that would change how the task is approached must be restated in the prompt. Before
  dispatching, scan recalled memories for anything touching the tools or paths the subagent will
  use.

Consider also adding a short line to the same section warning that constraints should be scoped to
what genuinely must not change, since a constraint written to keep a diff tidy can force a subagent
to ship a known defect. Keep it to one sentence; the file is deliberately dense.

Do not restructure the file or restate the model-tier rules, which live in the global `CLAUDE.md`
and are deliberately not repeated there.

## Acceptance

- `~/.claude/refs/delegation-doctrine.md` names project memory in the mandatory-embeds list.
- The addition is one or two bullets, matching the file's existing terse style.
- `/delegate` and `/autopilot` both pick it up automatically, since both adopt this file wholesale
  and neither restates its contents.

## Notes

Two sibling findings surfaced by the same 2026-08-08 Hubbub run, both also global and both worth
folding in if whoever picks this up is already editing the file:

- The mandatory-embeds list should probably also name **shared fixed-port dev stacks**. That run
  dispatched three parallel agents that each independently wanted to run `pnpm dev:all` on the same
  hardcoded ports, which would have made them fight over `EADDRINUSE`. The orchestrator caught it
  only by noticing after dispatch and messaging all three. A checklist line ("if more than one
  parallel builder needs a dev server on fixed ports, the orchestrator starts it once and tells
  them") would have prevented it by construction.
- The doctrine says every builder stages but never commits, which is correct, but it says nothing
  about **when the orchestrator should commit during a parallel fan-out**. Committing after each
  agent returns risks sweeping another still-running agent's staged work into the wrong commit.
  A line recommending a commit barrier at the end of each parallel wave would close that.
- Re-verified 2026-08-08: premise still holds.
- Shipped 2026-08-11 in commit df3d04e. Added to delegation-doctrine.md's mandatory builder-prompt embeds: restate any load-bearing project memory inline, because a subagent re-solving a problem memory already answered is a wasted dispatch.
