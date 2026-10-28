<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=6ebfb411 -->
# UserPromptSubmit hook did not inject /handoff

**Type:** skill-improvement
**Origin:** ai

## Goal

`/handoff` must be injected by the UserPromptSubmit hook the same way `/pickup`
and `/close` are, so a session can never conclude the skill doesn't exist.

## Context

2026-08-11, revaire-mobile session. Joe typed `/handoff`. **No hook context was
injected.** Because `~/.claude/skills/handoff/SKILL.md` carries
`disable-model-invocation: true`, it is also absent from the model's Skill tool
listing â€” so with no hook injection there was no signal it existed at all.

I told Joe *"`/handoff` isn't a skill in this setup"* and wrote a freeform
handoff to `.for_bepy/` instead. He corrected me: *"it is indeed a skill in this
setup... youre wrong, and a hook should have helped you prevent making the
mistake that there is no such skill."* A filesystem check then found it
immediately at `C:\Users\tecno\.claude\skills\handoff\SKILL.md`.

This is an enforcement gap, not carelessness. Two skills with **identical**
frontmatter behaved differently in the same session:

- `/pickup` â€” `disable-model-invocation: true` â€” hook fired, full SKILL.md injected
- `/close` â€” `disable-model-invocation: true` â€” hook fired, full SKILL.md injected
- `/handoff` â€” `disable-model-invocation: true` â€” **hook silent**

The injected text for the two that worked even carries the line *"never report
it as unavailable, missing, or a listing hiccup"* â€” the exact failure that
occurred for the one that didn't fire.

Cost: the handoff was written in the wrong format and location (freeform
markdown in `.for_bepy/` rather than a todo pinned to `PLAN.md`), then had to be
redone, at the tail of a long session where context was already scarce.

## Approach

1. Find the UserPromptSubmit hook that performs skill injection (likely under
   `~/.claude/hooks/`) and determine how it enumerates candidate skills.
2. Work out why `handoff` is missed while `pickup` and `close` are matched.
   Plausible causes to check, not assumed: a hardcoded allowlist that was never
   extended; a glob that misses single-word names; a name-collision or
   ordering bug; the skill being newer than the hook's cached index.
3. Fix so that **every** `~/.claude/skills/*/SKILL.md` with
   `disable-model-invocation: true` is injected on a `/<name>` mention.
4. Add a fallback: if a prompt names `/<word>` that matches no known skill and no
   injection happened, have the hook emit a short note telling the model to check
   the filesystem before asserting non-existence.

## Acceptance

- Typing `/handoff` in a fresh session injects its SKILL.md, same as `/pickup`.
- A newly created skill with `disable-model-invocation: true` is injected without
  any hook edit.
- Verified by adding a throwaway skill and confirming injection, then removing it.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - flagged-skill-mention.py is a generic glob-based injector now, and a live test confirmed /handoff injects correctly. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).

- Renumbered 100 -> 298 on 2026-08-13 (todo 286): id 100 was claimed by two different files. The other file kept it because it was filed earlier. Any older reference to todo 100 may mean this one.
