<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=6, reconfirm-count=1, content-hash=7804502f -->
<!-- duplicate-checked -->
# Eighteen skills declare themselves slash-only in prose but are model-invocable in frontmatter

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide, per skill, whether each of the 18 skills whose `description:` opens "Triggers on /X only"
should carry `disable-model-invocation: true`. Flagging one removes its description from every
session's system prompt entirely; leaving it removes the misleading sentence instead.

## Context

Found 2026-08-25 while executing todo `400` (trim two over-budget descriptions). 400 treated this as
a two-skill problem. It is not.

Measured across all 85 skills: **20 descriptions open with "Triggers on /X only". Only 2 of them
(`heal-skill`, `obsidian`) actually carry `disable-model-invocation: true`.** The other 18 are
model-invocable, so their descriptions load into every session regardless of the sentence claiming
otherwise:

```
apply-styleguide 35   batch-todos 124   cleanup-todos 167   code-check 189
commit 118            favicon 26        github-pages-init 36  init-claude-md 33
inject-widgets 33     iterate-it 269    linear 118          meta-tags 28
preview 208           pwa 22            rate-it 271         readme 25
screenshot 230        sleep-when-done 153
```

**2,085 chars, paid on every session.** Todo 400 measured the whole remaining always-on description
budget at 5,892 chars after the 2026-08-18 audit, so this is roughly a third of it, spent on skills
that describe themselves as firing only on an explicit slash command.

`~/.claude-fibo/.../memory/reference_flagged_skills_excluded_from_listing.md` records the mechanism:
a flagged skill never loads into the listing, so the description budget genuinely does not apply to
it. Flagging is therefore a real saving, not a cosmetic one.

## Approach

**This is NOT a blanket flag-all-18.** At least two are model-invocable on purpose and flagging them
would break documented behaviour:

- `commit` - `CLAUDE.md` makes auto-commit a universal default, which means Claude decides to commit
  without the dev typing anything. That is model invocation.
- `rate-it` - its sibling `rate-it-and-commit` says "Model-invocable on purpose" in its own
  description, and calls `/rate-it` as a nested step.

So, per skill, pick one of three:

1. **Flag it** (`disable-model-invocation: true`) - the description is accurate, nothing auto-fires
   it. Saves its full char count.
2. **Keep it model-invocable and DELETE the "Triggers on /X only" sentence** - the sentence is
   simply false and is itself costing chars on every session.
3. **Keep both** - only where a written reason exists for why the skill must stay model-invocable
   while telling the model not to invoke it. Record that reason in the skill body.

Check each against `git log` and any `done/` todo before deciding: some were deliberately left
unflagged by the 2026-08-18 audit and reversing that silently would re-litigate a settled call.

## Acceptance

- Every one of the 18 has an explicit decision, none left by default.
- No skill both claims slash-only AND stays model-invocable without a recorded reason.
- `python ci/run_all.py` passes, with the skill count unchanged at 85.
- The saving is measured and stated, the same way todo 400 stated its 178 chars.

## Notes

Todo `400`'s own Notes line cites this follow-up as "todo 779". That was wrong: 779 was taken by a
concurrent session between the note being written and the id being reserved. This file is the
follow-up 400 meant.

- **Renumbered from id `780` to `842` on 2026-08-31** by todo `809`, executed from the main thread of
  a `/mega-todos` run. Two files shared the prefix `780`, so claiming or completing "todo 780" by id
  was ambiguous. This file was the one moved because a bare-`780` sweep across the whole backlog
  found only `809` itself and `803` referring to the id, and `803`'s reference is unambiguously to
  `780-guard-against-piping-cargo-test-output.md`, which keeps the id. `PLAN.md` named neither, so no
  PLAN.md edit was needed.
