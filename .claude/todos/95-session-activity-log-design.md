<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=2, reconfirm-count=7, content-hash=75cd15eb -->
# Session activity log design, parked

**Type:** task

## Goal
Preserve the concrete design and the verified file locations for logging session activity to a local file, so none of it has to be rediscovered. **Do NOT build this unless Joe asks.** He explicitly stopped the build on 2026-07-30 and moved the discussion to another chat about a general persistent-memory vault for Claude Code agents.

## Context
Idea: `/close` records what was actually worked on to a local append-only log, and `/clockify-reconciliator` reads it as evidence for placing and describing entries. Nothing writes to Clockify at close time.

Everything needed already exists on disk, verified 2026-07-30:

- `~/.claude/sessions/<pid>.json` has `sessionId`, `cwd`, `startedAt` (epoch ms), `name`. `~/.claude-personal/skills/close/rename-session.ps1` already resolves the current session by walking to the claude.exe ancestor pid and matching this file, so reuse that, do not invent a second way.
- `~/.claude/projects/<project-slug>/<sessionId>.jsonl` timestamps every line. Slug for this repo is `c--Users-tecno-Desktop-Projects-zng-app`.
- **Parsing gotcha:** `type == "user"` includes tool results. A genuine human turn is `type == "user"` AND `message.content` is a STRING. On session `49fc376b-54b7-4f98-80b0-583cd9984f84` the naive filter gave 162 and the correct one gave 31, first turn 15:30:50 local, last 17:51:47. Use those numbers as the test fixture.
- Conductor's `interactive-sessions.json` has `started_at` but is live-only and vanishes on close. Its `companion.db` has `skill_events`, `token_records`, `usage_snapshots` and **no** persistent session-lifecycle table.
- Clockify project resolution: match session `cwd` against the `repos:` lists in `~/.claude-personal/skills/clockify-reconciliator/projects/*.md`.

## Approach
Store RAW human-turn timestamps, never a precomputed duration. Idle thresholds must stay a read-time decision, because collapsing to a number destroys the evidence permanently. Record shape: `sessionId`, `cwd`, `project`, `startedAt`, `endedAt`, `humanTurns[]`, `wallClockSeconds`, `gitCommits[]`, `loggedAt`. Append-only JSONL at `~/.claude/activity/sessions.jsonl`, idempotent per `sessionId` so a second close updates rather than duplicates.

Multiple Claude sessions run concurrently on the same repo (three on zng-app on 2026-07-30), so overlapping records are expected and are NOT double work. The consumer merges overlapping windows rather than summing them.

Consumer rules still bind: never create entries in empty time ranges, never touch an entry with a non-empty description, never overlap, `billable: false` always.

## Acceptance
Only actionable if Joe revives it. If the vault idea from the other chat supersedes this, close this todo as superseded rather than building a parallel system.

## Park reconfirmed 2026-08-16

Asked again by `/auto-do-todos` and answered by Joe, verbatim: *"i think this deserves a whole
session, and its a lot more complex, its a question of permanent memory, and its something im very
passionate for claudes usages, but i think its best we shelf it for now, that should be brainstormed
in its own session, grilled down, all of that jazz."*

So the park stands, and its shape is now explicit: this is **not** a build task waiting for a green
light. **It is a `/brainstorm` task**, in its own session, framed as the permanent-memory question
rather than as an activity-log implementation. That reframing is the reason the old question below
is closed rather than carried forward: the answer was never "build it or not".

The 2026-08-12 question (build now vs leave parked) is therefore resolved. Do not re-ask it. The
only thing a future run may do with this file is hand it to a dedicated brainstorm session.

Note the Obsidian vault has since taken over the cross-project-memory role this design partly
overlapped, so any brainstorm starts by asking what the vault does NOT already cover.

## Merged in (2026-08-11)

Absorbed todos 206 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
