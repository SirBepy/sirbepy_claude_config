<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=5, reconfirm-count=2, content-hash=591b5cc2 -->
# brainstorm: widen step-2 ask-gate to full CLAUDE.md parity (any genuine UX/ARCH/SEC/DATA/TOOLING fork, not just uninferable facts)

**Type:** skill-improvement

## Goal

`skills/brainstorm/SKILL.md`'s Step 2 currently only fires a question for facts that
"truly cannot be inferred from the codebase or context" (an API key, an external
business rule, a hard product constraint). The global CLAUDE.md's execution-discipline
rule is broader: it requires asking BEFORE the first Edit/Write whenever there's "any
pre-edit decision point... a UX/ARCH/SEC/DATA/TOOLING decision that isn't already
dictated 1:1 by an existing pattern being copied" - which includes genuine DESIGN forks
(not just missing facts) that a smart engineer could reasonably resolve two different
ways, even when both options are individually inferable in isolation. Widen brainstorm's
gate to this full parity. Joe has explicitly flagged that this trades against the
skill's stated "gate-free" intent, and has accepted filing it anyway for consideration -
this is NOT a request to implement unconditionally, it's a request to have the tradeoff
weighed deliberately later.

## Context

`skills/brainstorm/SKILL.md` (as of 2026-08-01), Step 2, line 22:
```
2. **Resolve genuine unknowns only.** Identify facts that truly cannot be inferred from
the codebase or context (an external API key, a business rule visible nowhere, a hard
product constraint). If any exist, front-load them in ONE `AskUserQuestion` (2-4 options,
domain tag, per global CLAUDE.md). If everything is inferable, ask nothing.
```
And the "Gate-free by design" section, lines 26-28:
```
No per-section design-approval checkpoint, no spec-review gate, no implementation-plan
sign-off, and no separate execution-mode question - task size decides subagent-driven vs
inline per CLAUDE.md's execution-discipline rules. There are no built-in gates, so no
full-auto opt-out snippet is needed to suppress them.
```

Compare the global CLAUDE.md's actual rule (from `~/.claude-personal/CLAUDE.md`,
"Execution Discipline" section, as quoted in this todo's own dispatch context):
> Front-load all questions before starting work, trivial or not. Never ask mid-task;
> never assume. This includes any pre-edit decision point: right before the first
> Edit/Write on a task, check whether there's a UX/ARCH/SEC/DATA/TOOLING decision that
> isn't already dictated 1:1 by an existing pattern being copied - if so, ask it now,
> before writing any code. Applies even to tasks that look like mechanical pattern
> replication (copying 4 files from an existing pattern can still hide 1 genuine
> behavioral fork, e.g. should a new hotkey fire unconditionally like its siblings, or
> only in one app state?).

`brainstorm`'s Step 2 as written is narrower: it only catches missing FACTS (things that
literally cannot be known without asking), not DESIGN FORKS where multiple defensible
answers exist and the codebase doesn't dictate one. The CLAUDE.md example given (a new
hotkey firing unconditionally vs only in one app state) is exactly the kind of thing
`brainstorm`'s current wording would NOT catch, since both behaviors are individually
"inferable" in the sense that Claude could pick either and justify it - the gap is that
neither is DICTATED by the pattern being copied, which is a different (and broader) bar
than "cannot be inferred at all."

## Approach

**This is explicitly a tradeoff to weigh, not a mechanical fix - do not implement
silently.** When picked up:

1. Re-read `skills/brainstorm/SKILL.md` in full, and the global CLAUDE.md's
   execution-discipline section in full, to confirm the gap described above still exists
   (behavior may have shifted since this todo was filed on 2026-08-01).
2. Surface the tradeoff explicitly before changing anything: widening the gate to full
   CLAUDE.md parity means MORE `AskUserQuestion` interruptions during brainstorm's flow,
   which cuts directly against the skill's stated purpose ("Local gate-free replacement
   for superpowers:brainstorming" and the "Gate-free by design" section's explicit
   framing). Consider whether a `/rate-it` or `/iterate-it` pass on this specific tradeoff
   (widen vs keep narrow) is warranted before committing to either, given Joe explicitly
   flagged this as needing deliberate weighing rather than a default-yes implementation.
3. If the decision is to widen: change Step 2's wording from "facts that truly cannot be
   inferred" to also cover "a genuine UX/ARCH/SEC/DATA/TOOLING fork not dictated 1:1 by
   an existing pattern being copied," matching the CLAUDE.md language closely enough that
   future readers see the parity is deliberate, not accidental drift. Keep the "front-load
   in ONE AskUserQuestion" batching behavior - widening the trigger condition should not
   also change the batching/format rules.
4. If the decision is to keep it narrow: close this todo with a one-line note in `done/`
   (or wherever the resolution gets recorded) explaining why gate-free was chosen to win
   over full parity for this specific skill, so a future audit doesn't re-flag the same
   gap without context.

## Acceptance

- A deliberate decision gets made and recorded (either the wording changes to full
  parity, or an explicit rationale is written for why brainstorm stays narrower than
  CLAUDE.md's general rule) - this todo is NOT done just because SOME edit happened; it's
  done when the tradeoff has actually been weighed, per Joe's explicit ask.
- If widened: Step 2's new wording is tested mentally against the CLAUDE.md's own hotkey
  example (a mechanical-looking pattern-copy task hiding one behavioral fork) to confirm
  it would actually catch that case.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] [ARCH] Widen /brainstorm's step 2 ask-gate from "facts that truly cannot be inferred" to full CLAUDE.md parity (UX/ARCH/SEC/DATA/TOOLING forks)? You flagged this yourself as a tradeoff needing weighing rather than a default yes: it catches more forks up front, but adds AskUserQuestion interruptions to a skill whose stated purpose is being gate-free. Options: (a) full CLAUDE.md parity; (b) keep it narrow, facts only; (c) widen only for SEC, DATA and ARCH forks and keep inferring UX and TOOLING. Recommended: (c), as the defensible middle.
