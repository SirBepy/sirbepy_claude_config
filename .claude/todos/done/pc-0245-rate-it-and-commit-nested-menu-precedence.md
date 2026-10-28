<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=6e687c42 -->
# rate-it-and-commit: define nested-menu precedence so rate-it's post-rating menu is suppressed when nested

**Type:** skill-improvement

## Goal

`skills/rate-it-and-commit/SKILL.md` Step 1 invokes `/rate-it` internally, but
`/rate-it` itself always ends its own turn with a "Post-rating prompt" - a plain-text
follow-up line offering "apply all / apply some / ignore" as the next move. When
`/rate-it` is invoked NESTED inside `/rate-it-and-commit`, this creates two competing
terminal questions in the same flow: `/rate-it`'s own post-rating menu, and
`/rate-it-and-commit`'s own threshold-based next-step logic (auto-commit, or its own
below-threshold `AskUserQuestion`). Define explicit precedence: `/rate-it-and-commit`
owns the terminal question when nested; `/rate-it`'s own post-rating menu must be
suppressed in that case.

## Context

`skills/rate-it/SKILL.md`, "Post-rating prompt" section (lines 112-128), always applies
after a rating is delivered:
```
So: deliver the full rating (verdict + reasoning + How-to-raise) as a complete text
response and END the turn on it. No tool call in that turn.

Close the rating message with a single plain-text follow-up line offering the next move
(this is a menu appended to the deliverable, not a standalone question, so it stays
inline text - do not promote it to an AskUserQuestion):

> Next move: **apply all** the suggestions, **apply some** (say which), or **ignore** and
> carry on?
```

`skills/rate-it-and-commit/SKILL.md`'s own "Flow" section (lines 28-33) invokes
`/rate-it` as step 1, then makes its OWN decision in step 2 based on the score:
```
1. **Rate it.** Invoke the `/rate-it` skill, passing the resolved diff content as the
   thing to rate. Use solo mode (no panel) unless the user explicitly passed a panel
   size.
2. **Check threshold.**
   - Score >= threshold: show a one-line summary `"Score X/10 - committing."` then
     invoke `/commit`...
   - Score < threshold: ask via AskUserQuestion (see below). Do NOT auto-commit.
```
Nothing in either file currently says whether `/rate-it`'s own "Next move: apply all /
apply some / ignore?" line should still print when `/rate-it` is invoked from inside
`/rate-it-and-commit`'s step 1. As written, a literal reading of both files independently
would have `/rate-it` print its own next-move line, THEN `/rate-it-and-commit` either
auto-commits or asks its OWN "Score is X/10 - below threshold... what now?" question
right after - two stacked menus in one flow, confusing and redundant (both are
functionally offering overlapping choices: `/rate-it`'s "apply all/some suggestions" vs
`/rate-it-and-commit`'s "accept suggestions, then commit").

## Approach

1. Read both `skills/rate-it/SKILL.md` and `skills/rate-it-and-commit/SKILL.md` in full
   before editing.
2. Add an explicit suppression note to `skills/rate-it/SKILL.md`'s "Post-rating prompt"
   section: when `/rate-it` is invoked BY another skill (nested, not directly by the
   dev), the invoking skill owns the terminal question/menu and `/rate-it` must NOT print
   its own "Next move" line - it should return just the verdict + reasoning +
   How-to-raise block and let the caller decide what happens next. Word this generally
   (not `/rate-it-and-commit`-specific) since other skills may also nest `/rate-it` in the
   future (check whether any currently do - grep this repo for other `Invoke the
   \`/rate-it\` skill` references before assuming `/rate-it-and-commit` is the only
   caller).
3. Add a corresponding note to `skills/rate-it-and-commit/SKILL.md`'s Step 1 ("Rate it")
   making the precedence explicit from the calling side too: "this skill owns the
   terminal question; `/rate-it`'s own post-rating menu is suppressed for this nested
   invocation."
4. Confirm the fix doesn't break `/rate-it`'s OWN documented example flow (the "If the
   dev then replies choosing a path, act on it on the following turn" logic, lines
   124-128) for the DIRECT (non-nested) invocation case - that logic must stay intact
   when the dev calls `/rate-it` directly, only the nested-from-another-skill case
   changes.

## Acceptance

- `skills/rate-it/SKILL.md` explicitly documents that its post-rating menu is skipped
  when invoked as a nested call from another skill.
- `skills/rate-it-and-commit/SKILL.md` explicitly documents that it owns the terminal
  question in that flow.
- Running `/rate-it-and-commit` end to end (both above- and below-threshold cases)
  produces exactly ONE terminal question/menu per run, not two stacked ones.
- Running `/rate-it` directly (not nested) still shows its own post-rating menu unchanged.

## Notes

- completed, commit 2d57b70

## Merged in (2026-08-11)

Absorbed todos 204 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
