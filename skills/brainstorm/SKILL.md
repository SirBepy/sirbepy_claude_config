---
name: brainstorm
description: Use before ANY creative or feature work - creating features, components, adding functionality, modifying behavior, or designing a change. Local gate-free replacement for superpowers:brainstorming; explores context, resolves only genuinely unknowable facts, then implements directly.
---

# /brainstorm

> Think before building. Explore, resolve genuine unknowns, pick an approach, implement. No ceremony.

## When to use

Before starting any creative/implementation work:
- Creating a feature, component, page, or module.
- Adding functionality or modifying existing behavior.
- A non-trivial refactor or design decision.

**Don't use** for pure mechanical edits (rename, typo fix, dependency bump) or for answering a direct question that needs no design.

## Process

1. **Check the todos backlog first, then explore code.** Grep `.claude/todos/` and `.claude/todos/done/` for an existing todo matching the feature by keyword, before reading code. If a settled spec/handoff exists, read it in full and adopt its decisions as authoritative - a parallel session may have already resolved this exact design; don't re-derive it, only diverge with an explicit stated reason. Then read the relevant code and recent commits, inferring everything you can from the codebase, CLAUDE.md, and project memories. Delegate wide searches or large-file reads to an Explore subagent so raw bytes don't land in main context - keep only the conclusion.
   - **Greenfield exception:** if the target is a new standalone project (empty/near-empty repo, no existing feature to extend, the ask describes a product rather than a change), the codebase has nothing to infer from, so also sweep for existing free/open-source alternatives before any naming or architecture question - report what they do, what they cost, and which stated requirements they already meet. Use CLAUDE.md's delegation rule for the multi-query web research (subagent when available, inline when the harness blocks it). Skip this for a feature inside an existing codebase, where prior art is irrelevant.
2. **Resolve genuine unknowns only.** Identify facts that truly cannot be inferred from the codebase or context (an external API key, a business rule visible nowhere, a hard product constraint). On a greenfield target, the prior-art survey's scope question goes first, before naming or architecture: given what already exists, does the dev still want to build (options like trial-the-existing-apps / build-only-the-unserved-gap / build-it-anyway)? Front-load whatever unknowns exist, scope question included, in ONE `AskUserQuestion` (2-4 options, domain tag, per global CLAUDE.md). If everything is inferable, ask nothing.
3. **Pick the approach internally.** Reason through the options and choose. Do not present the design for approval. Do not write a spec for the user to read. Do not chain into a separate planning/approval skill.
   - **Divergent-options exception:** for tasks that are fundamentally about generating many distinct creative/aesthetic options with no single "correct" answer (icon/logo concepts, naming, similar wide-open asks) rather than converging on one coherent approach, skip the solo pass and dispatch several `general-purpose` subagents (model: sonnet) from round one, each briefed with an explicitly different creative lens. A solo pass here tends to produce variations on one idea, not genuinely distinct ones (Hubbub favicon session, 2026-08-01: a solo pass produced 4 concepts, all rejected in one shot; parallel lensed subagents produced meaningfully more variety). The normal feature/component case (one coherent approach wanted) keeps the solo-pass default.
4. **State it in one line and build.** Emit a one-liner like "Planning done, implementing." then proceed straight to implementation. A short internal plan or task list is fine; user sign-off on it is not required.

## Gate-free by design

No per-section design-approval checkpoint, no spec-review gate, no implementation-plan sign-off, and no separate execution-mode question - task size decides subagent-driven vs inline per CLAUDE.md's execution-discipline rules. There are no built-in gates, so no full-auto opt-out snippet is needed to suppress them.

## What still holds

- Genuine ambiguity that cannot be inferred still earns ONE concise question.
- Hard stops (destructive/irreversible actions, secrets, package safety checks) are unchanged.
