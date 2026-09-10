---
name: create-todo
description: Files one todo mid-session; bare invocation = session handoff pinned to PLAN.md.
disable-model-invocation: true
argument-hint: "[what to defer - empty = hand off this session]"
---

# /create-todo

> Write one todo right now. Bare call = hand this session off to the next AI. For an explicit
> handoff, `/handoff` is the dedicated alias for this same mode - same file, same steps.

All file rules (location `.claude/todos/`, filename/id, template, git-policy self-heal) live in
`~/.claude/skills/close/ai-todos-format.md` - follow it exactly.

If there's no project (no repo root for `.claude/todos/` to live under), say so and stop.

## Step 0 - Target repo

Default target is the current repo. Per `ai-todos-format.md`'s "Which repo's backlog" rule, a
todo whose Approach/Acceptance would change a DIFFERENT repo's files belongs in that repo's
`.claude/todos/` instead, even when this session never otherwise touches that repo - most often
work on `~/.claude` itself (skill, hook, global rule, `CLAUDE.md`) spotted from inside a project
session, or a finding surfaced in repo A whose fix lives in repo B. When the invocation or the
surrounding conversation names a specific other repo, or the content being drafted only makes
sense against files outside the current repo, that other repo is the target. If genuinely
ambiguous between two candidates, ask once via AskUserQuestion naming both.

Same-repo target: continue with Step 1 below. Cross-repo target: Step 1 and Step 2 still apply
(mode and Type are unaffected by where the file lands), then file under "Cross-repo filing"
instead of Step 3/Step 4.

## Step 1 - Detect mode

Parse the args as natural language, not rigid syntax:

- **Handoff mode** when: the invocation is bare, or the dev's message reads as "continue this in
  another chat" / "let's pick this up later" / frustration with the current session, or the args
  start with `next`. The deliverable is a handoff of THIS session's work. (The explicit
  `/handoff` command always runs this mode directly - no detection needed there.)
- **Deferral mode** otherwise: the args describe a discrete thing to note for later (a fix, an
  observation, an offer that was declined for now).

If genuinely ambiguous, ask once via AskUserQuestion.

## Step 2 - Determine Type

- `task` - something Claude can execute later (code, config, analysis). Handoffs are tasks.
- `skill-improvement` - a skill gap, a "did this differently than the skill said" note, or a
  "this project keeps needing X" observation. Approach names the skill file involved.

Infer from context; ask only if genuinely ambiguous.

`**Origin:**` is always `dev` for this skill, both modes - `/create-todo` only fires on the dev's
own invocation (`disable-model-invocation: true`), so the dev is always the one asking.

## Step 3 - Write the file

**Deferral mode:** fill Goal/Context/Approach/Acceptance from the discussion. If there isn't
enough to fill Context/Approach meaningfully, ask one clarifying question rather than write a
thin file.

**Handoff mode:** follow the contract's "Handoff mode" section in `ai-todos-format.md` exactly -
Type, fill instructions, PLAN.md pin, and confirm wording all live there (shared with the
explicit `/handoff` command so the two never drift apart).

## Step 4 - Confirm (deferral mode)

Print the filename and a one-line summary. Do not execute the todo - this skill only files it.
Handoff mode's confirm wording is defined in the contract's "Handoff mode" section.

## Cross-repo filing (target repo != current repo)

Filing into another repo's backlog is still a WRITE into that backlog, so it takes the same
three guards a same-repo write takes - all specified once in `ai-todos-format.md` and reused
here by reference, never restated:

1. **Content-duplicate guard against the DESTINATION.** Run `ai-todos-format.md`'s
   "Content-duplicate guard" against the target repo's `.claude/todos/` and `done/`, not the
   current repo's - grep the destination, read hits in full, resolve via its three outcomes.
2. **Id reservation against the DESTINATION.**
   `~/.claude/skills/close/reserve-todo-id.ps1 -RepoRoot <target repo root>`. It already takes
   an explicit root and creates `<target>/.claude/todos/` if missing - a real side effect,
   state it in the confirm line below rather than doing it silently.
3. **Git-policy exclude self-heal against the DESTINATION.** Apply `ai-todos-format.md`'s
   "Git policy" three lines to `<target repo root>/.git/info/exclude`, idempotently, whether or
   not the destination had a `.claude/todos/` before this call.

Sequence (this skill owns all four steps in one invocation, instead of a hand-executed
four-step manual sequence):

a. Run the Content-duplicate guard (1) against the target repo.
b. Reserve the id (2) against the target repo.
c. Write `<target repo>/.claude/todos/<id>-<slug>.md` using the reserved id, in the normal
   template from `ai-todos-format.md`.
d. Delete `<target repo>/.claude/todos/<id>-.reserved`.
e. Self-heal the exclude file (3) against the target repo.

**Confirm:** print the target repo path, the filename, a one-line summary, and whether
`.claude/todos/` was newly created in that repo. Do not execute the todo, and do not switch the
session's working context to the target repo - filing it is the whole job. Cross-repo todo
EXECUTION is out of scope for this skill; work belonging to another repo is done from a session
in that repo, not this one.

## Anti-patterns

- Filing a todo for something that needs the dev's physical action (credentials, hardware,
  browser login) - say it directly instead.
- Batching multiple unrelated asks into one file. One todo per invocation.
- Finalizing new todo content without a backlog-overlap check: before finalizing, grep the
  destination backlog for keywords tied to the new todo's subject (tool/component names, the
  specific question being posed) and read any hits in full. A match: fold its findings in, or
  explicitly supersede it (note the old id and why). Never leave two todos silently disagreeing.
