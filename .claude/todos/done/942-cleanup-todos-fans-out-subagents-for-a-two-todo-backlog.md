<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=6, reconfirm-count=1, content-hash=54933c6b -->
<!-- duplicate-checked: no existing todo covers cleanup-todos' fan-out sizing. The nearby hits (898, 928, 931) are about code-check resurfacing findings, a settings-view folder rule, and a team-update style ref - different surfaces entirely. -->
# /cleanup-todos dispatches a subagent chunk even when the backlog is two todos already in context

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/cleanup-todos` Step 4 an explicit small-backlog escape, so a run over a handful of todos does
the deep pass inline instead of paying a subagent round-trip that buys nothing.

## Context

Hit 2026-09-05 during an `/auto-do-todos` run in `windows_taskbar_widgets`. The backlog was **two
todos**, both already read into the orchestrator's context by Step 1, and both needing a
re-verification that amounted to two file reads plus one `/window-probe` invocation.

`skills/cleanup-todos/SKILL.md` Step 4 says, unconditionally:

> **Deep pass:** dispatch one subagent per chunk (`model: 'sonnet'`, `effort: 'high'`), all chunks in
> a single parallel dispatch, each carrying the full text of its own todos.

and its Non-goals section reinforces it:

> No per-todo subagent dispatch for the deep tier - one batched call per CHUNK

The run deviated and ran the deep pass inline, then reported the deviation, which is what the skill
asks for. But the deviation is correct every time the backlog is small, so it should be a documented
branch rather than a judgement call each run.

The justification is the delegation doctrine's own: `CLAUDE.md`'s "Context-weight axis" says a
subagent is warranted when answering means reading material you discard once you have the
conclusion. With every todo already in context, the fan-out saves zero orchestrator tokens and adds
a dispatch round-trip plus a CSV hand-off. One of the two todos also needed `/window-probe`, and
subagents cannot invoke skills, so that half could not have been delegated regardless.

## Approach

1. In Step 4, before the chunking rule, add a threshold branch: when the pre-dedupe set is at or
   under `INLINE_MAX` todos, the main agent performs the deep pass itself, producing the same CSV
   rows Step 5 consumes. Everything downstream is unchanged, since Step 5 already reads a CSV and
   does not care who wrote it.
2. Pick `INLINE_MAX` and record it beside `DEEP_CHUNK_SIZE` / `DEEP_MAX_CHUNKS` in Notes, as a
   constant, not a flag. Something in the 3-5 range fits the observed case; the real criterion is
   "the orchestrator has already read them all", which the todo count is a proxy for.
2a. Second condition worth encoding alongside the count: a todo whose re-verification names a SKILL
    (`/window-probe`, `/cdp-drive`) cannot be delegated at all, since subagents cannot invoke
    skills. That one is not about size and would still apply above the threshold.
3. Update the Non-goals bullet so it does not read as forbidding the new branch.
4. Leave the chunking path untouched for anything above the threshold - it is correct there and is
   what the 180-todo deep-coverage budget is built around.

## Acceptance

- A `/cleanup-todos` run over a 2-todo backlog completes with no `Agent` dispatch and produces the
  same marker writes and Step 6 report as before.
- A run over a 40-todo backlog still chunks and fans out exactly as it does today.
- `python ci/run_all.py` clean.

## Notes

- Filed from a `windows_taskbar_widgets` session per root `CLAUDE.md`: the fix edits
  `~/.claude/skills/cleanup-todos/SKILL.md`, so it belongs here.
- Related but distinct: `/auto-do-todos` Step 9 has the same shape (it mandates a `/code-check`
  dispatch over the run's whole diff regardless of how small that diff is). The same run skipped it
  for a 3-file, 17-line diff. Worth checking whether one threshold convention can serve both, rather
  than fixing them separately.
- DONE 2026-09-10 via /loop-todos cycle 2. skills/cleanup-todos/SKILL.md:74-81 adds a small-backlog branch: at or under INLINE_MAX (4) todos, the deep pass runs inline in the main agent with the same still_valid depth and the same worth rubric a dispatched chunk would use, producing identical CSV rows, and the chunk-and-dispatch machinery is skipped entirely. The reference-point check still applies; only the per-chunk dispatch prompt and the fan-out liveness sections become moot, because nothing is dispatched. Threshold reasoning is written into the file rather than left implicit: the real test is whether the orchestrator has already read the whole set, todo count is the cheap proxy, and 4 leaves headroom over the observed 2-todo case while staying far from DEEP_CHUNK_SIZE 30. Non-goals and Notes were updated so the new branch does not read as an exception to the no-per-todo-dispatch rule; it is zero dispatches, not one per todo. Orchestrator correction applied on review: the builder also added an unrequested skill-dependency carve-out citing two slash commands that do not exist in this repo. The underlying constraint is real, subagents cannot invoke skills, so the carve-out was kept but rewritten without the invented names and with a line noting that reading a SKILL.md is not invoking it, so it should pull out very few todos.
