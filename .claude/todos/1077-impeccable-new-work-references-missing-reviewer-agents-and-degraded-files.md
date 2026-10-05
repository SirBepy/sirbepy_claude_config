<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=8654864f -->
# impeccable's new-work flow points at reviewer/documenter agents and degraded/ files that don't exist

**Type:** skill-improvement
**Origin:** ai

## Goal

Every agent type and reference file that impeccable's `reference/new-work.md` section 7 tells the
model to use actually exists, or the text names the real fallback, so an unattended build can run
the finish review and documenter steps as written.

## Context

mc_plugins_tag session 2026-10-04 (overnight build of the sirbepys-minecraft-server website,
`/impeccable init` then new-work). Section 7 of `skills/impeccable/reference/new-work.md` says to
spawn `impeccable-finish-reviewer` and `impeccable-documenter`, and falls back to
`reference/degraded/finish-reviewer.md` / `reference/degraded/documenter.md` only when the
harness has no subagent tool at all.

Checked live that session:
- No `impeccable-finish-reviewer` or `impeccable-documenter` in the Agent tool's available types
  (only claude, Explore, general-purpose, Plan, statusline-setup), and none under `~/.claude/agents`.
- `reference/degraded/` does not exist in either `~/.claude-personal/skills/impeccable/reference/`
  or `~/.claude/skills/impeccable/reference/`.

So the documented path was unreachable both ways: subagents exist (so the degraded path is "not
allowed"), but the named agents don't. The session improvised a general-purpose sonnet reviewer
with a hand-written five-section prompt and wrote DESIGN.md itself from `document.md`. It worked,
but every future run will improvise differently. The `dispatch-preamble-guard` hook also rejected
the first improvised dispatch for lacking the staging line, one more round trip.

## Approach

1. Decide: ship the two agents (`agents/impeccable-finish-reviewer.md`,
   `agents/impeccable-documenter.md`, sonnet, read-only for the reviewer, with the builder
   preamble's staging line baked in), or restore `reference/degraded/*.md` and change section 7
   to "if the named agent type isn't available, use general-purpose with degraded/<file>.md as
   the prompt".
2. Check whether the impeccable install is a vendored upstream skill whose self-update would
   overwrite local edits (see todo 1037) before editing its reference files.
3. Same audit for `visualize.md`'s image-generation step and `serve-question.mjs`, which the
   session skipped because the dev had said not to ask.

## Acceptance

A fresh session following new-work section 7 can spawn the reviewer and documenter (or the named
fallback) without inventing a prompt, and the dispatch passes `dispatch-preamble-guard` first try.
