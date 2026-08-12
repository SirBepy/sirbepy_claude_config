<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=7da3de67 -->
# bepy-project-setup-web: drop Step-1 skip-picker and `auto` flag, run everything per auto-run taste

**Type:** skill-improvement

## Goal

`skills/bepy-project-setup-web/SKILL.md` Step 1 asks the dev "Run everything" vs "Let me
pick what to skip" via `AskUserQuestion` unless an explicit `auto` flag was passed. Per
the codebase's documented "auto-run" preference (project memory: "Skill steps prefer
auto-run over prompting" - "Default to running checks/checklists automatically; only add
a prompt if there's a genuine cost reason") this default-to-asking behavior should
flip: run everything by default (matching the `auto` flag's current behavior), and drop
the picker/flag distinction entirely.

## Context

`skills/bepy-project-setup-web/SKILL.md` (as of 2026-08-01):

- "Flags" section (lines 10-12):
  ```
  ## Flags

  - `auto` - Skip all prompts, run everything, auto-yes all questions (including PWA).
    No user interaction at all.
  ```
- Step 1 (lines 25-38):
  ```
  ## Step 1 - Ask what to skip

  If `auto` flag is passed, skip nothing and proceed to Step 2.

  Otherwise, first ask using AskUserQuestion:

  - "Run everything"
  - "Let me pick what to skip"

  If the user picks "Run everything", skip nothing and proceed to Step 2.

  If the user picks "Let me pick what to skip", use AskUserQuestion with multiSelect to
  ask:

  "Which skills do you want to SKIP? (Everything else will run)"
  ...
  ```
- Step 3 ("Ask about PWA," lines 61-70) has the SAME pattern: asks unless `auto` was
  passed.

This is a two-tier prompt gate (Step 1's skip-picker, Step 3's PWA question) that only
goes away entirely when the dev remembers to type the `auto` flag - the default,
un-flagged invocation always stops for at least one and usually two `AskUserQuestion`
calls, which is the opposite of the documented auto-run preference for skill checklists.

## Approach

1. Read `skills/bepy-project-setup-web/SKILL.md` in full before editing.
2. Remove the `auto` flag from the "Flags" section (or repurpose it, if there's still a
   need for an opt-IN to the old interactive picker behavior - decide during
   implementation whether keeping a `--pick` / `--interactive` opt-in flag for the rare
   case the dev DOES want to skip specific steps is worth preserving, versus dropping the
   picker capability entirely and relying on the dev just saying "skip favicon and
   readme" in free text if they ever want to exclude something).
3. Rewrite Step 1 to skip the `AskUserQuestion` entirely by default: proceed straight to
   Step 2 (run all skills in order) unless the dev's invocation text explicitly names
   something to skip (parse free text per the codebase's free-form-args convention,
   matching how `/obsidian`'s planned rewrite - todo 29 in this same backlog - is meant
   to work).
4. Apply the same default-to-auto change to Step 3's PWA question - proceed with
   `/pwa` by default, skip only if the dev's text says not to set up a PWA.
5. Update the "Notes" section (lines 101-105) if it references the `auto` flag or
   skip-by-user framing in a way that no longer matches the new default behavior.

## Acceptance

- Invoking `/bepy-project-setup-web` with no special flag/text runs every skill in Step
  2's order AND sets up PWA, with zero `AskUserQuestion` interruptions - matching what
  the OLD `auto` flag used to require explicitly.
- A dev who explicitly names something to skip (in free text) still gets that respected -
  confirm the skip mechanism still works, just without requiring a formal picker flow by
  default.
- Re-read the full file after editing to confirm Step 1 and Step 3's numbering/logic
  still flow correctly into Step 2's "run skills in order" and Step 4's "commit" steps.
