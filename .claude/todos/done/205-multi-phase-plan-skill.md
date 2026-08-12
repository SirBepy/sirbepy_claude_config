# Design a "plan" layer on top of ai_todos (kanban To-Do lane over the backlog) — possible retirement of next-ai-prompt/pickup, possible plugin

**Type:** skill-improvement

## Goal

A skill (global, lives once in `~/.claude/skills/`, usable from any codebase) that lets Joe
define an explicit **order** to work through a project's existing `ai_todos` — "do this one
first, then that one, then those" — resumable later by a fresh agent via something like
`/pickup-next-part-of-plan`. This is NOT Claude's design to finalize — it's a note for Joe to
work through with a higher-tier model (he's referred to this as both "Opus" and "Fable" across
this conversation — whichever one it ends up being). Everything below is context + one Sonnet
session's suggestions, not decisions.

## Context

This idea evolved a lot across one conversation on 2026-07-14 (fibo repo, work-recap session).
Recording the full arc so the next session doesn't have to re-derive it or re-make mistakes
already corrected:

**Round 1 — Claude's first read (wrong on several counts).** Joe described wanting to sequence
several fibo tickets. Claude treated this as a brand-new plan format that might duplicate four
existing mechanisms (`ai_todos`, `/next-ai-prompt`+`/pickup`, `github-board`, the `Workflow`
tool's `phase()`/`pipeline()`), and rated it **3/10** — citing redundancy, and pointing at
`github-board` being unused as evidence Joe doesn't stick with tracker-shaped tools, plus a
worry that the plan would be global state shared across unrelated codebases (staleness risk).

**Correction 1 (Joe):** `github-board` was irrelevant noise in the comparison — he doesn't use
it at all. Per his request it was archived this session: moved
`~/.claude/skills/github-board` → `~/.claude/skills/archived-skills/github-board`, committed as
`0d3d670` ("CHORE: archive unused github-board skill") in the `~/.claude` dotfiles repo. Treat
it as gone from the comparison set going forward.

**Correction 2 (Joe):** Claude had explained the `Workflow` tool sloppily and Joe didn't
recognize it (unclear if it was something he or "we" had built). Clarified: `Workflow` is a
built-in Claude Code tool (Anthropic's product, not project code) — you write a small JS-like
script and it fans work out to subagents in parallel/pipelined stages, tracked live in the UI.
Critically, it's **ephemeral to one tool call** — no state persists once the run ends. Confirmed
it genuinely doesn't overlap with what Joe wants (which needs to survive across separate future
sessions), so it drops out of the comparison too — not a live alternative, just useful vocabulary
if the eventual design wants "fan out to N subagents for one phase" as a building block.

**Correction 3 (Joe, important):** Claude had misread "global skill" as "one global plan file
spanning every codebase" and rated accordingly (worried about cross-project shared state going
stale). Joe corrected: the **skill** is global (written once, works in any repo), but the
**plan** is per-project — structurally identical to how `/close`, `/create-todo`, and
`/batch-todos` already work today (global skill in `~/.claude/skills/`, reads/writes
project-local `.for_bepy/ai_todos/`). Once corrected, most of the "risky global state" objection
evaporated — this is a proven, already-adopted pattern, not a new shape. Score revised 3 → 7/10.

**Correction 4 (Joe, the kanban framing — current best description of the idea):** `ai_todos`
stays exactly as it is today and becomes, conceptually, the **backlog** column (everything,
unordered, one file per task, already working). The new "plan" is the **To Do** column: an
ordered list of references to *existing* `ai_todos` ids, saying what order to pull them off the
backlog in. Crucially the plan does **not** duplicate task descriptions — it only orders
pointers to todos that already exist as their own files. Claude re-rated this **8/10** — the only
real gaps found:
  - (a) a plan can end up pointing at a todo id that was later deleted (per the existing
    convention: finished todos get deleted, ids are never reused) — whatever reads "what's
    next" must silently skip a vanished id, not error.
  - (b) if the intended usage includes "Joe keeps opening a chain of independent fresh agent
    sessions, each grabbing the next unclaimed item" (see Joe's two invocation shapes below),
    there's no lock yet — two fresh agents could double-pick the same next item. Low severity
    (duplicate work, not data loss) but worth a simple claim marker.

**New in this message (not yet rated/designed):**
- Joe is now floating **retiring `/next-ai-prompt` and `/pickup` entirely** and folding their
  job into this system.
- He still wants *something* shaped like `/next-ai-prompt` (a one-command "here's where I left
  off, here's what's next") — but wants that command to essentially **be `/create-todo`**: ending
  a session writes a normal `ai_todos` entry (today's format, unchanged), and that new todo then
  gets appended into the ordered "plan" (the To Do lane), instead of `/next-ai-prompt` writing a
  separate, differently-shaped handoff note. That would collapse three artifact types
  (`ai_todos`, `next-ai-prompt` handoff notes, "the plan") down to two: `ai_todos` (backlog, and
  now also the landing spot for `/create-todo`-style handoffs) + the plan (pure ordering layer on
  top).
- Joe is considering eventually packaging this as a **Claude Code plugin**, tied together as one
  coherent tool — possibly to show off at the company he works at. Explicitly a "maybe, later"
  ambition, not a requirement for a first version.
- **Storage location is explicitly unresolved and flagged by Joe as probably wrong today.**
  Today's convention is `.for_bepy/ai_todos/` — per the root `CLAUDE.md`, `.for_bepy/` is
  documented as gitignored, personal, and **project-scoped only, never global**. Joe suspects
  that if this becomes a plugin / company-facing tool, `.for_bepy` (an informal, personal-sounding
  folder name) is the wrong home, and floated something like `.claude/.todos/` instead. He was
  explicit that this is for him and the higher-tier-model session to decide together, not
  something to implement now.

**Two invocation shapes Joe wants supported either way** (carried over from the original ask,
still open): (1) one main orchestrator agent dispatching each plan phase to subagents, or (2) a
chain of separate small/fresh agent sessions, each picking up just the next unfinished item —
whatever design comes out of this needs to work under both, not assume a single long-lived
orchestrator is always present.

## Approach

Sonnet's accumulated suggestions from this conversation — offered as input for the design
session, not decisions:

1. Keep the `ai_todos` file format completely unchanged as the backlog / single source of truth
   for task content. The plan should only ever store **references** (ids), never copies of
   descriptions — two sources of truth for the same task content is how these things silently
   drift stale.
2. Whatever reads "what's next" must skip/prune plan entries whose referenced todo file no
   longer exists — silently, not as an error state.
3. If the "chain of independent fresh agents" invocation shape is kept, add a minimal claim
   marker (timestamp or agent-id written into the plan entry when an agent picks it up) so two
   fresh agents can't silently double-work the same item.
4. On collapsing `/next-ai-prompt` + `/pickup` into `/create-todo` + the plan: check whether
   `/pickup` currently does anything beyond reading the handoff note (e.g. it's described
   elsewhere as running "the verify checklist" on resume) — if so, that behavior needs a new home
   in whatever replaces it, rather than quietly getting lost in the merge.
5. The storage-location change (`.for_bepy` → something like `.claude/.todos`) is bigger than it
   looks: `.for_bepy` is hardcoded into the root `CLAUDE.md`, `ai-todos-format.md`, and every
   skill that touches it (`/close`, `/create-todo`, `/batch-todos`). Moving it means updating all
   of those, not just adding a new folder — worth deciding explicitly up front rather than letting
   it happen implicitly mid-build.
6. If the plugin/company-facing ambition is real, dogfood on fibo alone for a few weeks first
   (this was also the top "how to raise the score" suggestion in the 8/10 rating) before
   generalizing or publishing — gives one real usage data point on whether the ordering actually
   gets kept up to date in practice.
7. None of the above is Sonnet's call to make. Storage location, whether to actually retire
   `/next-ai-prompt`/`/pickup`, plugin packaging, and the exact schema are explicitly deferred to
   Joe + the higher-tier model session.

## Acceptance

N/A — this is a design discussion, not an implementation task. Resolve by either replacing this
file with the real skill/plugin design once it's decided, or deleting it if the idea is dropped.
