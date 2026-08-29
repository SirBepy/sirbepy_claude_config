<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=6fda3393 -->
<!-- duplicate-checked -->
# A bare Agent-tool dispatch with no skill in the loop has zero signal about the preamble guard

**Type:** skill-improvement
**Origin:** ai

## Goal

Give a session dispatching via the top-level `Agent` tool directly - no `/delegate`,
`/auto-do-todos`, `/mega-todos`, or any other skill in the loop - some signal that
`hooks/dispatch-preamble-guard.py` will reject the call, before it gets rejected.

## Context

Hit 2026-08-25 in `claude_usage_in_taskbar`: dispatched a plain read-only Explore investigation via
the `Agent` tool with no project skill involved (an ad-hoc "go investigate this bug" call, not a
`/delegate` or `/auto-do-todos` run). Two dispatch attempts were rejected by
`hooks/dispatch-preamble-guard.py` before `refs/builder-preamble.md` was read and the correct
markers (including the `READ-ONLY DISPATCH` opt-out) were pasted in.

This is a different root cause than todos 392/409/373, which are all about a specific skill's
*embedded dispatch template* being stale - fixable by pointing that skill at
`refs/builder-preamble.md`. Here there was no skill template to fix: the `Agent` tool's own
tool-description (what the harness hands back for `ToolSearch`/the tool list) says nothing about
`dispatch-preamble-guard.py` at all, so a session with no prior memory of the doctrine has no way to
know the requirement exists until the first dispatch bounces.

**Reconfirmed 2026-08-27 (zng-app):** same failure, worse repro - a batch of 6 parallel `Agent`
dispatches (ad-hoc ticket-audit subagents, no skill in the loop) were ALL rejected simultaneously
by the guard on the first attempt, since none of the 6 prompts carried the preamble. Same
resolution as before: read `refs/builder-preamble.md` after the rejection, repaste into all 6,
redispatch clean. Two independent hits now, both first-dispatch-of-session, both an ad-hoc
`Agent` call with no skill involved - option 3's "only bites the first dispatch" holds so far in
both cases, but the batch-of-6 shape shows the cost scales with fan-out width, not just a flat
one-time tax.

## Approach

Options, not mutually exclusive:

1. **Amend the `Agent` tool's own description** (wherever it's generated/configured for this
   harness) to name the guard and point at `refs/builder-preamble.md`, so `ToolSearch`/the tool list
   itself carries the signal instead of only the hook's rejection message.
2. **Global `CLAUDE.md` reminder**, if the tool description is not editable (harness-owned): a line
   near the top-level Agent-tool guidance in global `CLAUDE.md` stating "any Agent dispatch, even
   ad-hoc with no skill involved, needs the canonical preamble - see `refs/builder-preamble.md`
   before the first dispatch of a session."
3. Confirm whether this only bites the *first* dispatch of a session (after which the guard's error
   message itself teaches the pattern) - if so, weigh whether a one-time two-strike cost per session
   is worth fixing versus accepting it as the guard doing its job cheaply.

## Acceptance

- A cold session's first-ever `Agent` dispatch, with zero project skills in the loop, either passes
  the guard on the first try or is told about the requirement somewhere it will actually read before
  dispatching (not just after rejection).

## Notes

Do not weaken `hooks/dispatch-preamble-guard.py` - same stance as todos 331/392: the guard is
correct, the gap is upstream discoverability. This is scoped narrower than 392 (which sweeps skill
templates) - this one is about the tool itself having no template to sweep.
