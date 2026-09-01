<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for arg parsing / chained command / slash argument: no match, live or done. -->
# Only /close documents the slash-arg chaining convention, so other skills get misread

**Type:** skill-improvement
**Origin:** ai

## Goal

Make "a `/`-prefixed argument is a chained command" a convention a session can find from any skill,
not one written down in exactly one place that a reader of a different skill will never open.

## Context

Filed 2026-09-01 from a `/close` retrospective, with a real incident behind it rather than a tidiness
argument.

2026-08-29, Joe typed `/cleanup-todos /mega-todos`. The session read `/mega-todos` as CONTEXT
modifying how `/cleanup-todos` should run (unattended mode), ran only the cleanup pass, and reported
it as complete. Joe's next message was "so did u even do /mega-todos". The real `/mega-todos` run,
44 todos and 48 commits, only began a full cycle later.

The convention that would have prevented it already exists, in `skills/close/SKILL.md`'s "Arg
parsing" section:

> A token starting with `/` opens a new chained command.
> Tokens between `/foo` and the next `/bar` are `/foo`'s args.

with worked examples (`/close /commit pushnbump`). That is unambiguous, and it is the repo's own
established reading. The problem is purely that it lives inside `/close`, and nothing in
`/cleanup-todos`, `/mega-todos` or any other skill points at it. A session invoking a non-`/close`
skill has no reason to open `/close`'s SKILL.md, so the convention is effectively invisible at the
moment it is needed.

`hooks/` cannot help here: the interpretation happens in the model's reading of the prompt, not in a
tool call, so there is nothing for a PreToolUse guard to inspect. This is a documentation-placement
problem.

## Approach

1. Read `skills/close/SKILL.md`'s "Arg parsing" section, which is the canonical text. Do not rewrite
   it; the goal is reachability, not a second copy that can drift.
2. Pick ONE home and point at it. Options, with the tradeoff named:
   - `CLAUDE.md`: most reliably read, but it currently sits at **6556 of a 6558-token ceiling**
     (`ci/check_instruction_budget.py`), so anything added must be offset by cutting elsewhere. Check
     the live number first; it may have moved.
   - `refs/`: a short `refs/slash-arg-parsing.md` holding the canonical rule, with `/close` reduced
     to a pointer and a one-line mention wherever skills are authored. Costs no always-loaded tokens.
   - Leave it in `/close` and accept the gap, recording that decision so it stops being re-noticed.
3. Whichever is chosen, state explicitly what to do when the reading is still ambiguous for a given
   pair: ask up front, per CLAUDE.md's front-load-all-questions rule, rather than picking silently.
4. Do NOT add the rule to every skill individually. That is the drift-generating option.

## Acceptance

- [ ] A session invoking any skill can reach the chaining rule without opening `skills/close/SKILL.md`
- [ ] The rule exists in exactly one canonical place; every other mention is a pointer
- [ ] The ambiguous-pair case names asking as the fallback
- [ ] If `CLAUDE.md` was touched, `python ci/check_instruction_budget.py` output pasted showing it
      still passes
- [ ] If the decision is "leave it", that decision and its reasoning are written down

## Notes

- Worth roughly a 5. One real incident, cheap to fix, but the behavioural half is already covered by
  a memory written the same day, so this is closing the durable-documentation half rather than
  preventing a recurrence outright.
- The counter-argument worth weighing before building: `/close` is the only skill that actually
  ACCEPTS a chain today. If no other skill ever will, documenting the convention globally may be
  solving a problem that only ever had one instance. Decide that first; it may make option 3 correct.
