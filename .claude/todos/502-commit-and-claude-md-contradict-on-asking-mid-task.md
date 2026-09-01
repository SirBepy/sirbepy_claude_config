<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=9b2b5790 -->
<!-- duplicate-checked -->
# /commit step 8 orders a mid-task question that CLAUDE.md forbids

**Type:** skill-improvement
**Origin:** ai

## Goal

Resolve the contradiction between `/commit` step 8's unpushed-overlap handling and `CLAUDE.md`'s
never-ask-mid-task rule, so a commit with a real hunk-level overlap has one defined behaviour
instead of two rules pointing opposite ways.

## Context

Hit twice on 2026-08-22 during phase 5, in the same session, on `.claude/todos/PLAN.md`.

`skills/commit/SKILL.md` step 8, the unpushed-overlap check, says of a real hunk-level hit:

> **interactive session** - STOP, name the overlapping commit and the blamed lines, ask via
> `AskUserQuestion` whether this is follow-up on the same unit of work (-> `git reset --soft
> HEAD~1`, restage everything together, one fresh commit) or genuinely separate (-> proceed).

`CLAUDE.md`'s Communication section says:

> Front-load all questions before starting work, trivial or not. **Never ask mid-task**; never
> assume.

A commit is the tail end of a task. The overlap is not knowable until the diff exists, so the
question cannot be front-loaded, and asking it is by definition mid-task. Both rules are explicit
and they cannot both be followed.

What actually happened both times: the session proceeded without asking, inspected the overlapping
commit, judged it a separate unit of work, and named it in the commit message. Both judgements were
correct (`695679b` was phase 3's PLAN.md record versus phase 4's; `37b5b8c`/`6643b7c` were the two
preceding todos of the same phase, which the one-commit-per-todo rule requires be kept separate).
But "correct by judgement" is exactly what the step-8 gate exists to prevent, so the gate was
effectively disabled by a rule elsewhere, silently.

Note the interaction with `PLAN.md`'s own tip 2, "One commit per todo, never batched, so a revert is
surgical." In a phase that closes several todos touching one shared file, a hunk-level overlap
against the session's OWN immediately-preceding commit is not an anomaly, it is the guaranteed
steady state. Step 8 currently asks about it every time.

## Approach

1. Read `skills/commit/SKILL.md` step 8's unpushed-overlap paragraph in full, and `CLAUDE.md`'s
   Communication section. Confirm the contradiction still reads as stated above before changing
   anything.
2. Decide which rule yields, and write the resolution into `/commit` rather than leaving it to be
   re-derived. Three candidate shapes, and this needs Joe:
   - **Carve-out in CLAUDE.md:** name commit-time overlap as an explicit exception to
     never-ask-mid-task. Cheapest, but adds words to a file at a zero-headroom token ceiling
     (6558/6558), so something must be cut first.
   - **Carve-out in `/commit`:** drop the question when the overlapping sha was produced by THIS
     session (the common case, and the one where the answer is mechanically decidable from the
     one-commit-per-todo rule), and keep it only for another session's sha.
   - **Report instead of ask:** always proceed, always name the overlap in the commit message, which
     is what both real occurrences did anyway. Matches the existing unattended-run branch, which
     already resolves this exact situation by recording rather than blocking.
3. Whichever wins, make the same edit cover the unattended branch so the two do not drift.

## Acceptance

- `/commit` step 8 and `CLAUDE.md` no longer give opposing instructions for the same situation.
- The resolution names the this-session-sha case explicitly, since that is the one the
  one-commit-per-todo rule makes routine.
- If the chosen fix adds text to `CLAUDE.md`, `python ci/run_all.py` still passes its budget check.

## Notes

Do not resolve this by making the gate stricter. Two real hits in one session were both genuinely
separate units of work, so a gate that blocked them would have been pure friction. The value at risk
is a genuine follow-up commit that should have been folded into its predecessor, which is a narrower
case than the gate currently covers.

Related: [[474-commit-step-8s-overlap-check-should-be-a-script]] is the mechanical half of the same
step, and whoever scripts that check will be reading this paragraph anyway.

**Third occurrence, 2026-08-25, `zng-admin`:** two same-session commits (`6d2ba8a` then `0a6dbca`,
both this session's own, sc-55166 follow-up work) hit a real hunk-level overlap on
`mask_input_editor.dart`/`biller_masks_section.dart`/`mask_extension.dart` - a follow-up feature
built directly on the just-committed base, not a fix. `list_peers` confirmed zero other sessions in
the repo. Proceeded as two separate commits (matches this todo's `commit-style.md` "one purpose per
commit" reasoning - the two were a distinct base-feature-vs-enhancement split, not a correction),
disclosed the deviation in the dev-facing report rather than asking beforehand. One more data point
for the "Carve-out in `/commit`" candidate shape above: the peer-check (already run at step 7a for
an unrelated reason) is a cheap, mechanical signal for "is anyone else touching this repo" that a
same-session-sha carve-out could piggyback on, rather than needing a new check.
