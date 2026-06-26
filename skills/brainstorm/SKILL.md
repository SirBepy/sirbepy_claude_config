---
name: brainstorm
description: Use before ANY creative or feature work - creating features, components, adding functionality, modifying behavior, or designing a change. Local lightweight replacement for superpowers:brainstorming. Explores context, asks only for genuinely unknowable facts, picks the approach internally, then implements. No approval gates, no spec hand-off, no plan sign-off.
---

# /brainstorm

> Think before building. Explore, resolve genuine unknowns, pick an approach, implement. No ceremony.

This skill REPLACES `superpowers:brainstorming` for this user. It deliberately strips out every user-facing approval checkpoint that skill imposes (see "What this omits"). When a creative task arrives, use THIS skill, never `superpowers:brainstorming`.

## When to use

Before starting any creative/implementation work:
- Creating a feature, component, page, or module.
- Adding functionality or modifying existing behavior.
- A non-trivial refactor or design decision.

**Don't use** for pure mechanical edits (rename, typo fix, dependency bump) or for answering a direct question that needs no design.

## Process

1. **Explore for context.** Read the relevant code and recent commits. Infer everything you can from the codebase, CLAUDE.md, and project memories. Delegate wide searches or large-file reads to an Explore subagent so raw bytes don't land in main context - keep only the conclusion.
2. **Resolve genuine unknowns only.** Identify facts that truly cannot be inferred from the codebase or context (an external API key, a business rule visible nowhere, a hard product constraint). If any exist, front-load them in ONE `AskUserQuestion` (2-4 options, domain tag, per global CLAUDE.md). If everything is inferable, ask nothing.
3. **Pick the approach internally.** Reason through the options and choose. Do not present the design for approval. Do not write a spec for the user to read. Do not chain into a separate planning/approval skill.
4. **State it in one line and build.** Emit a one-liner like "Planning done, implementing." then proceed straight to implementation. A short internal plan or task list is fine; user sign-off on it is not required.

## What this omits (vs superpowers:brainstorming)

Intentionally gate-free. The following are NOT part of this flow:
- The per-section "Does this design look right so far?" approval checkpoint.
- The "Please review the spec before we proceed" gate.
- The "Approve the implementation plan before I start" gate.
- The writing-plans execution-mode question ("subagent-driven or inline?") - decide that yourself by task size per CLAUDE.md's execution-discipline rules.

Because there are no built-in gates, no full-auto opt-out snippet is needed to suppress them.

## What still holds

- Global CLAUDE.md rules (one command per call, PowerShell on Windows, `/commit`-only, em-dash ban, question formatting).
- Genuine ambiguity that cannot be inferred still earns ONE concise question.
- Hard stops (destructive/irreversible actions, secrets, package safety checks) are unchanged.
