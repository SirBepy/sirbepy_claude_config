<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hits are other surfaces (preview iframes, disk-doctor cards, Clockify scope, status reporting); none is about the brainstorming skill's prose questions -->
# Brainstorming asks its questions in chat prose; Joe wants them on the question card

**Type:** skill-improvement
**Origin:** ai
**Summary:** Every brainstorming question in a Conductor chat goes on the question card with options, never as a prose question in a message.

## Why

On 2026-10-27 Claude asked open questions in chat text and Joe said "why are u asking me questions like this, ask it properly".

## Goal

When `superpowers:brainstorming` (or the local `/brainstorm`) runs in a Conductor chat, every question goes on the
`ask_user_question` card with options and badges, never as a prose question in a message.

## Context

- 2026-10-27, dashboard-a "Project status check" chat: brainstorming the extraction answer key, Claude followed the
  skill's "each message ends with one question ... no list of example answers" and asked open questions in
  `send_message` text. Joe: "why are u asking me questions like this, ask it properly". The five remaining design
  questions then went on one card and he answered them all at once.
- Global `CLAUDE.md` (Communication) already says every question uses the question tool with 2-4 options and that
  all questions are front-loaded; the brainstorming skill's own conversation style pulls the other way, and the skill
  text wins in the moment.
- `superpowers:brainstorming` is a plugin skill (not editable here); dashboard-a uses it on purpose
  (`.claude/settings.local.json`, Joe 2026-10-20). The local `/brainstorm` skill is ours.

## Approach

1. In `~/.claude/skills/brainstorm/SKILL.md` (our replacement), state that questions go on the question card, batched
   per topic, with the brainstorming tone kept for playbacks only.
2. For the plugin skill, add one line to global `CLAUDE.md`'s Communication section or a hook reminder that the card
   rule overrides a skill's "ask one open question" style; check the instruction token budget
   (`ci/check_instruction_budget.py`) first.

## Acceptance

A brainstorming run in a Conductor chat asks its questions on cards; the rule is written where the next session reads
it before the skill's own conversation guidance.
