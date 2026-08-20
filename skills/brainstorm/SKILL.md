---
name: brainstorm
description: "Use before ANY creative or feature work: creating features, components, adding functionality, modifying behavior, or designing a change."
---

# /brainstorm

> Think before building. Explore, resolve genuine unknowns, pick an approach, then present a short plan and wait, unless a go-word or the triviality escape applies.

## When to use

Before starting any creative/implementation work:
- Creating a feature, component, page, or module.
- Adding functionality or modifying existing behavior.
- A non-trivial refactor or design decision.

**Don't use** for pure mechanical edits (rename, typo fix, dependency bump) or for answering a direct question that needs no design.

## Process

1. **Check the todos backlog first, then explore code.** Grep `.claude/todos/` and `.claude/todos/done/` for an existing todo matching the feature by keyword, before reading code. If a settled spec/handoff exists, read it in full and adopt its decisions as authoritative - a parallel session may have already resolved this exact design; don't re-derive it, only diverge with an explicit stated reason. Then read the relevant code and recent commits, inferring everything you can from the codebase, CLAUDE.md, and project memories. Delegate wide searches or large-file reads to an Explore subagent so raw bytes don't land in main context - keep only the conclusion.
   - **Greenfield exception:** if the target is a new standalone project (empty/near-empty repo, no existing feature to extend, the ask describes a product rather than a change), the codebase has nothing to infer from, so also sweep for existing free/open-source alternatives before any naming or architecture question - report what they do, what they cost, and which stated requirements they already meet. Use CLAUDE.md's delegation rule for the multi-query web research (subagent when available, inline when the harness blocks it). Skip this for a feature inside an existing codebase, where prior art is irrelevant.
2. **Resolve genuine unknowns only.** Ask when BOTH hold: either branch of a fork produces different visible behavior, AND neither branch is dictated 1:1 by the pattern being copied - not a domain-tag partition, the same bar CLAUDE.md's Communication front-load rule uses. Example: copying 4 sibling files to add a hotkey still hides one fork (fire unconditionally like its siblings, or only in one app state?), and now gets asked even though it wouldn't have before. On a greenfield target, the prior-art survey's scope question goes first, before naming or architecture: given what already exists, does the dev still want to build (options like trial-the-existing-apps / build-only-the-unserved-gap / build-it-anyway)? Front-load whatever forks exist, scope question included, in ONE `AskUserQuestion` (2-4 options, domain tag for how it's presented, per global CLAUDE.md). If nothing forks, ask nothing.
3. **Pick the approach internally.** Reason through the options and choose. Whether the pick gets presented is step 4/5's call, not this step's - don't write a full spec regardless, the step 5 plan (if it fires) is capped at ~5 lines. Do not chain into a separate planning/approval skill.
   - **Divergent-options exception:** for tasks that are fundamentally about generating many distinct creative/aesthetic options with no single "correct" answer (icon/logo concepts, naming, similar wide-open asks) rather than converging on one coherent approach, skip the solo pass and dispatch several `general-purpose` subagents (model: sonnet) from round one, each briefed with an explicitly different creative lens. A solo pass here tends to produce variations on one idea, not genuinely distinct ones (Hubbub favicon session, 2026-08-01: a solo pass produced 4 concepts, all rejected in one shot; parallel lensed subagents produced meaningfully more variety). The normal feature/component case (one coherent approach wanted) keeps the solo-pass default.
4. **Decide whether to skip the checkpoint.** Two escapes exist and they combine - either alone is enough to skip straight to build:
   - **Go-word.** The invoking prompt already signals pre-approval. Trigger phrases (this list is greppable and gets appended to as real misses show up): "then implement it", "just do it", "go", "and implement", "and build it". Match on intent-bearing phrases in the invoking text, not just these exact strings.
   - **Triviality escape.** All three hold: the change is confined to a single existing file, adds no new file, and adds no new skill / hook / global-rule / ref surface. Any one of the three failing means this escape does not apply.

   If an escape applies, emit a one-liner like "Planning done, implementing." and proceed straight to implementation.
5. **Otherwise, checkpoint.** Present a plan capped at roughly 5 lines (not an essay) via `AskUserQuestion` (2-4 options, domain tag, per global CLAUDE.md's Communication section) and wait for the go-ahead before writing any code.

## Gate-free only for the two escapes

The default is a checkpoint: present the capped plan and wait. The gate-free guarantee still holds, but only inside the two escape branches from step 4 - a go-word in the invocation, or a change trivial enough to hit all three triviality conditions. Inside either branch: no per-section design-approval checkpoint, no spec-review gate, no implementation-plan sign-off, and no separate execution-mode question - task size still decides subagent-driven vs inline per CLAUDE.md's execution-discipline rules. Outside both branches, the checkpoint in step 5 fires; there is no third path back to gate-free.

## What still holds

- A genuine fork (behavior differs, and no pattern dictates the branch) still earns ONE concise question.
- Hard stops (destructive/irreversible actions, secrets, package safety checks) are unchanged.
