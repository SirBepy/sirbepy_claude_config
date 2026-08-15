<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=9, reconfirm-count=1, content-hash=65c2df74 -->
# Memory-index size warning demands a destructive compaction it can't justify

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop the Auto Memory index-size warning from pushing sessions into deleting memories mid-task.
Either make its advice non-destructive, or give it a policy it can actually follow.

## Context

Filed 2026-08-13 from a zng-app session (share-to-claim epic 54968, worktree
`lenderless-54968`). Mid-ticket, right after a routine one-line append to the project's
`MEMORY.md`, a `PostToolUse:Edit` system-reminder fired:

> The memory index at MEMORY.md is 160 lines, approaching the 200-line read limit. Compact it to
> under 140 lines now: keep one line per entry, move detail into topic files, and merge or drop
> stale entries.

Three problems with it:

1. **The advice does not apply.** The index was already one line per entry with a short hook -
   there was no detail to "move into topic files". It is 160 lines because there are 159 distinct
   memories. Getting to 140 means **deleting about 20 of them**, which the message frames as
   routine housekeeping.
2. **It fires mid-task and says "now".** The session was mid-verification on a ticket. Deciding
   which accumulated knowledge to discard is the dev's call and deserves its own pass
   (`/cleanup-memory` exists for exactly this), not a silent detour triggered by an unrelated
   append.
3. **It is not one of Joe's hooks.** Grepped all of `~/.claude/hooks/` and both `settings.json`
   and `settings.local.json`: nothing references `MEMORY.md`. The configured `PostToolUse` hook
   is `impeccable/scripts/hook.mjs` only. So this is **built-in harness behaviour** from the Auto
   Memory system, not a rule Joe wrote - which also means there is nothing in `~/.claude` to edit
   to change the wording.

The session declined to act on it and surfaced it to Joe instead. Joe: "what kind of stupid ass
hook made you do that, log that as a bug to look into in ~/.claude".

## Approach

Confirm the source first, since the fix depends on it:

1. Re-grep `~/.claude` (hooks, settings, plugins, any MCP server config) for `MEMORY.md`,
   `200-line`, and `Compact it to under`. If a local source turns up, this is a normal hook edit -
   soften it to "consider running /cleanup-memory" and drop the "now".
2. If nothing turns up (expected), it is harness-internal. Then the useful work is on our side:
   - Add a line to global `CLAUDE.md`'s Memory Discipline section stating plainly that the
     index-size warning is **advisory**, that compaction means deleting memories, and that it is
     never actioned mid-task or without Joe - it becomes a `/cleanup-memory` invocation or a todo.
   - Consider having `/cleanup-memory` also prune the index, so there is a real answer to point
     the warning at.
3. Optional, only if the index genuinely gets unwieldy: teach `/cleanup-memory` to group index
   lines under `##` topic headings (Shortcut, Playwright/e2e, Flutter, process). That cuts
   scan cost without deleting anything, which is the actual goal the warning is groping at.

Rejected: merging clusters of memory files to shrink the index. Checked the tightest cluster
(six Playwright/e2e reference memories) - they total ~45KB. Merging them produces one enormous
file that is worse to load and worse to recall against. The index length is a symptom of a large
useful corpus, not of bad structure.

## Acceptance

- A future session that trips the warning knows, from `CLAUDE.md` alone, that it is advisory and
  that the correct response is to surface it rather than delete memories.
- No session silently drops memories to satisfy a line count.

## Notes

Per-project detail: the index in question is
`C:\Users\tecno\.claude-personal\projects\c--Users-tecno-Desktop-Projects-zng-app\memory\MEMORY.md`.
Other long-running projects will hit the same threshold, so this is not zng-app specific.

**2026-08-13, later the same day: it happened for real, and the threshold is BYTES not lines.**

While a `/cleanup-memory` audit was running against this exact index, a concurrent session acted on
the warning and compacted `MEMORY.md` from 160 lines to 138 (just under the "under 140" the message
demanded). **Three entries were dropped out of the index while their files stayed on disk**, so they
silently stopped loading in every session:
`project_registration_slug_attribution_gap` (inside the epic-protection zone Joe had set for that
run), `project_sc54084_not_reproducible`, `reference_flutter_bump_procedure`. All three were restored
by hand afterwards. This is no longer a hypothetical risk, it is a reproduced loss event.

Also correct a premise above: the live warning measures **KB, not lines** - "the memory index at
MEMORY.md is 20.2KB, approaching the 24.4KB read limit. Compact it to under 17.1KB now". So the
session that compacted to 139 lines was optimising the wrong quantity entirely. Any fix should talk
about bytes, and note that the warning re-fires on every single edit to the file.

**See 323, which pulls the opposite way and must be reconciled with this one.** A `/cleanup-memory`
run on 2026-08-13 found 23 of that project's 182 memory files absent from `MEMORY.md` (they never
load into any session) and proposed re-indexing 18, taking the index 160 -> 178. So the index needs
ADDITIONS at the same time this todo is worried about its length. This todo's own option 3 (group
index lines under `##` headings) is the most likely way to hold both.
