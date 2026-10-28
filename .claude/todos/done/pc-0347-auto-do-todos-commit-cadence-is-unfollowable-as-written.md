<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /auto-do-todos says "/commit after each todo" but re-invoking the skill 20+ times is not what a run actually does

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/auto-do-todos` Step 6's commit instruction describe what a real run can actually execute, so
a run does not have to quietly reinterpret it 20 times to get through the backlog.

## Context

Observed first-hand 2026-08-15. A run executed 21 todos and produced 25 commits.

`skills/auto-do-todos/SKILL.md` Step 6 item 5 says `/commit` after each completed todo, and its
Notes repeat "Never commit directly. `/commit` after each completed todo, same cadence as
`/batch-todos`." Global `CLAUDE.md` is stricter still: "NEVER commit directly. Always invoke
`/commit` first and follow it, every commit, no exceptions."

What the run actually did, and what any run will do: invoked `/commit` once at the start, read it
in full, wrote the session marker, then followed its procedure directly for the remaining commits
without re-loading the skill. That is almost certainly the intended behaviour, and the design
supports it - `skills/commit/SKILL.md` says the session marker "is never consumed, so every later
commit in the same session needs no marker write at all", and step 1 says to read
`commit-style.md` "once per session". But no file says the SKILL itself only needs loading once,
so the literal instruction and the practical one disagree.

The gap matters because the wording is what an unattended run reads when deciding whether it is
compliant. A run that took it literally would re-load a long skill file 20 times; a run that did
not is technically deviating from a rule marked "no exceptions".

## Approach

State the intended cadence explicitly in both places rather than leaving it to inference.

1. `skills/auto-do-todos/SKILL.md` Step 6 item 5 and its Notes bullet: say that `/commit` is
   invoked and read in full once per run, and that subsequent commits follow its procedure
   directly, including the prefilters and the pathspec form, without re-invoking the skill.
2. Check whether `/batch-todos` Step 6 item 5 needs the same clarification, since `/auto-do-todos`
   points at it for cadence. Keep the two consistent.
3. Decide whether global `CLAUDE.md`'s "always invoke `/commit` first and follow it" needs the same
   once-per-session qualifier. It probably does, but that file is a bottleneck and the rule is
   load-bearing, so make the smallest change that removes the contradiction rather than rewriting
   the section.

Do not weaken the actual guarantee. The point of the rule is that no commit happens outside
`/commit`'s procedure, and that must stay true. This is about how many times the procedure is
READ, not about which commits follow it.

## Acceptance

- A cold run reading Step 6 knows without inferring how many times to invoke `/commit`.
- The prefilter and pathspec requirements still apply to every commit.
- `/auto-do-todos` and `/batch-todos` agree.

## Notes

- Done 2026-08-16, commit 7bb8751. CLAUDE.md, /auto-do-todos Step 6 and /batch-todos Step 6 now all say /commit is invoked and read in full once per run, with every later commit following its procedure directly. The guarantee is preserved by an explicit clause naming the session marker, prefilters, pathspec form and branch/overlap checks as still applying to every commit. /autopilot and /delegate carry the same latent ambiguity and were left for a follow-up todo.
