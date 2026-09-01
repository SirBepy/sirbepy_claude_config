<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=5, reconfirm-count=2, content-hash=20a71a92 -->
<!-- duplicate-checked -->
<!-- 392/409 cover skills MISSING the three markers. This is different: the markers were present
     and correct, but the ~80-line block had to be retyped into every dispatch by hand. 391 is
     about builders getting a tree baseline. Nothing covers the copying cost. -->
# /mega-todos' builder block is hand-copied into every dispatch

**Type:** skill-improvement
**Origin:** ai

## Goal

A `/mega-todos` run writes the same ~80 lines into every builder prompt: the canonical preamble
from `refs/builder-preamble.md`, plus the six-step injected commit block from
`skills/mega-todos/SKILL.md`, plus the HARD RULES list. Only three things actually vary per
dispatch: the owned/off-limits file lists, the task spec, and the commit message.

## Context

Measured on the run of 2026-08-21 in `claude_usage_in_taskbar`: 12 builder dispatches, each
carrying that block, retyped from the skill file every time.

Two real costs, both observed on that run:

1. **Orchestrator tokens.** ~80 duplicated lines x 12 is pure repetition in the main thread, which
   is the exact resource `/mega-todos` exists to conserve.
2. **Drift risk.** The block is the thing that makes a parallel run safe (branch guard, pathspec
   form, prefilters, the never-`git add -A` rule). Retyping it by hand 12 times is 12 chances to
   drop a line, and a dropped branch guard or a widened pathspec is exactly the class of bug the
   block prevents. `refs/builder-preamble.md`'s own header already documents a past drift incident
   (`bdb0323`) from retyping a template from memory.

Note this is NOT the marker-gap problem: on that run all three guard markers were present and the
dispatches passed `hooks/dispatch-preamble-guard.py`. See 392 and 409 for the missing-marker class.

## Approach

Give the orchestrator one substitution point instead of a copy target. Options, roughly in order of
preference:

1. A small script (`skills/mega-todos/build-dispatch.ps1` or `.mjs`) taking `-Owned`, `-OffLimits`,
   `-Task`, `-CommitMessage`, `-ExpectedBranch` and emitting the finished prompt string. The
   orchestrator writes only the varying parts. Keeps one canonical copy of the block on disk, which
   is what kills the drift risk.
2. Failing that, at minimum hoist the invariant tail (HARD RULES, prefilter commands, branch guard,
   marker step) into one named file both `/mega-todos` and `/delegate` point at, so there is a
   single edit site.

Check whether `/delegate` and `/autopilot` want the same helper before designing it - they build
similar prompts and a helper that only serves one skill is a third copy, not a fix.

Keep the literal marker strings intact in whatever the script emits: the guard is a pure string
check, so a helper that paraphrases them breaks every dispatch it generates.

## Acceptance

- A `/mega-todos` builder dispatch can be constructed without pasting the preamble or the commit
  block by hand.
- The emitted prompt still passes `hooks/dispatch-preamble-guard.py` (all three literal markers
  present) - prove it with one real dispatch, not by inspection.
- `refs/builder-preamble.md` remains the single source of the preamble text; the helper reads it
  rather than embedding a second copy.
