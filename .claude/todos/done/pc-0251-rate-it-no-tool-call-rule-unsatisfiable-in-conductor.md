<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=1, content-hash=a86b88f2 -->
# /rate-it's "no tool call in the rating turn" rule cannot be satisfied in Conductor

**Type:** skill-improvement
**Origin:** ai

## Goal

Resolve the contradiction between `/rate-it`'s post-rating rule and the Claude Conductor host's
requirement that every turn call `send_message`.

## Context

`skills/rate-it/SKILL.md`, "Post-rating prompt" section, says:

> Do NOT call `AskUserQuestion` in the same turn as the rating. Bundling a tool call with the
> rating text makes the harness (and the global "no work alongside messages" rule) swallow the
> rating - the dev ends up with a bare picker and no score. [...] deliver the full rating [...] as
> a complete text response and END the turn on it. No tool call in that turn.

In Claude Conductor that instruction is unsatisfiable. Assistant text is never rendered in the
chat at all: `send_message` is the only channel Joe sees, and the host requires it on every turn.
So "end the turn on text with no tool call" would deliver the rating to nobody.

Hit live on 2026-08-11 rating whether to commit the 517 untracked skill files. The rating was
delivered through `send_message` and rendered correctly, so the rule's underlying fear (a bare
picker with no score) did not materialise - the danger is specifically `AskUserQuestion`
swallowing preceding text, not any tool call at all.

## Approach

The rule conflates two different things: "do not bundle an `AskUserQuestion` with the rating" (the
real hazard, still correct) and "make no tool call at all" (over-broad, and impossible in a host
where the message channel is a tool).

Narrow the rule to name the actual hazard, and add the host carve-out: in a session where
user-visible output goes through a message tool, the rating is delivered via that tool and the
turn ends there. Check `skills/rate-it-and-commit/SKILL.md` and `skills/iterate-it/SKILL.md` for
the same wording before editing, since they chain `/rate-it` and may restate it.

**Also `skills/cleanup-todos/SKILL.md`**, found 2026-08-12 - its Step 6 carries the same absolute
form ("Deliver as the turn's FINAL message, no tool call after it") for a different reason (an
`AskUserQuestion` swallowing the report). Same fix, same carve-out; it is not a `/rate-it` sibling
so a search scoped to the rating skills alone will miss it. Sweep for the wording repo-wide rather
than editing a known list of three.

## Acceptance

- The rule names `AskUserQuestion` (and any picker-style tool) as the thing to keep out of the
  rating turn, rather than banning all tool calls.
- It states what to do when the host's only user-visible channel is itself a tool call.
- No sibling skill still carries the old absolute wording.

## Notes

- completed, commit 2d57b70
