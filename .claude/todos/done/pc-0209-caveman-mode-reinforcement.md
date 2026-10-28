<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Caveman mode fades over long/mixed-content sessions

**Type:** skill-improvement

## Goal

The `SessionStart` hook activates caveman mode once, at session start ("CAVEMAN MODE ACTIVE... Code/commits/security: write normal"). In a 2026-07-16/17 session mixing technical explanation, architecture decisions, and code edits, replies drifted back to normal-length structured prose for the non-code portions instead of staying in terse fragment style. The one-shot injection doesn't hold attention over a long, topic-mixed session.

## Context

Noticed during this session's own `/close` Phase 1 retrospective. Not a "be more careful" fix - hooks only fire on session start, there's no built-in periodic reinforcement mechanism for a mode like this.

## Approach

Investigate whether a lighter-weight reinforcement is worth adding, e.g.:
- A `UserPromptSubmit` hook that re-appends a short one-line caveman reminder every N turns (needs a counter mechanism - check what state a hook can persist between invocations).
- Or: accept this as a known limitation of one-shot SessionStart hooks and don't build anything - the cost/benefit may not be worth a new hook for a communication-style nudge.

Read `~/.claude/hooks/` and the caveman skill (`caveman:caveman`) first to see what's already there before adding anything new.

## Acceptance

- Either a periodic-reinforcement mechanism exists and is verified to actually re-fire mid-session, or a explicit decision is made to leave it as-is with the reasoning recorded here (update this file, don't just delete it).

## Notes

- Dropped via /cleanup-todos 2026-08-11: moot - the caveman plugin is uninstalled, replaced by snippets/terse-replies.md. Confirmed by dev 2026-08-11.
