<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=611f4dc7 -->
<!-- duplicate-checked -->
# /auto-do-todos asks questions it has already answered itself

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/auto-do-todos`'s Step 5 round from putting a question to Joe when the run can already name a
defensible answer. A question carrying a recommendation is a decision, not a question.

## Context

Observed 2026-09-05 on the countoff backlog, and Joe rejected the round mid-turn.

The run triaged an 18-todo backlog, then fired Step 5 and asked **12 questions in one card**.
Eleven of the twelve carried a written recommendation with a one-line reason, and all twelve carried
the skill's mandated "you decide - autopilot it" escape. Joe's reply:

> "before asking me, how bout you first check which of these i actually need to answer... myb theyre
> not necessary... myb you can just /iterate-it ? i gotta go sleep now"

Re-checked afterwards: **zero of the twelve genuinely blocked.** Each had a smaller, reversible,
defensible default, and the run went on to decide all twelve itself in about fifteen minutes,
recording each decision plus its reasoning into the todo files. Two items were genuinely Joe's (a
credential revocation, and a fact only he holds about whether a data migration ever ran), and
neither is a *choice* - one is a physical action, one is a question with no options to pick between.

**Why the skill let this happen.** Two mechanisms, both individually reasonable:

- `SKILL.md`'s Step 4 says "Lean AUTO, not DEV" and even warns that "'it's a design decision' is not
  a reason, that is what `/iterate-it` is for". But nothing operationalises it, so a cautious triage
  pass still buckets DEV and the prose loses.
- Step 5's second trigger fires when "one or more todos carry a pre-written `## Open questions` block
  from a previous run", on the stated grounds that "the dev already knows those are coming". That
  reasoning is wrong in the common case: those blocks are written by Step 8, which requires "a
  recommendation whenever one exists". So Step 8 systematically produces questions that already
  carry their own answers, and Step 5 then treats the existence of those blocks as evidence Joe wants
  to be asked. The two steps compound instead of cancelling.

Note the skill *already litigated* the trigger and concluded it was self-correcting (see its
"Decided 2026-09-04 (todo 915)" note, which measured a 67-todo backlog carrying 20 such blocks and
called the two triggers "self-correcting across repeated invocations"). That analysis was about
whether the round fires OFTEN ENOUGH. This is the opposite failure and it was not considered.

## Approach

The fix belongs in `~/.claude/skills/auto-do-todos/SKILL.md`, and it should be a gate, not a louder
restatement of "lean AUTO" - the file already says that and it did not bind.

- **Add a recommendation gate to Step 5's Shape section.** Before a question enters the round, test
  it: can the run name a defensible answer and a reason? If yes it is not a question - take it,
  record the decision and its reasoning in the todo file, and continue. Only what fails that test is
  asked. Concretely, this means a question that would carry a "Recommended: **(x)**" line is
  disqualified from the round by construction.
- **Narrow Step 5's trigger 2 to match.** It should fire on pre-written `## Open questions` entries
  that carry NO recommendation, not on the mere existence of an `## Open questions` block. Keep the
  empty-AUTO-queue trigger and cleanout mode as they are.
- **Change what Step 8 parks.** Have it write a `## Decided` block for anything it can answer, with
  the decision and the reason, and reserve `## Open questions` for the genuine residue: physical
  actions, facts only the dev holds, and taste with no argument either way. This is what the
  countoff run ended up doing by hand, and it is the shape that makes the next run cheap.
- Keep the "you decide - autopilot it" option for whatever genuinely survives. It is a good escape;
  it just should not be needed twelve times.
- Check whether `/autopilot` shares this shape before editing, since `/auto-do-todos` adopts its
  behaviour contract by reference and a fix in one may belong in both.

## Acceptance

- `SKILL.md`'s Step 5 states the recommendation gate as a test a question must pass to be asked, not
  as advice.
- Step 5's trigger 2 is scoped to recommendation-free open questions.
- Step 8 documents the `## Decided` versus `## Open questions` split and says which content goes
  where.
- Re-reading the skill cold, it is unambiguous that a question with a recommendation is a decision
  the run owes the dev in the todo file, not a card.

## Notes

Joe's own framing, worth keeping verbatim in whatever the fix becomes: the alternative to asking is
not guessing, it is `/iterate-it`. The skill already knows this and says so in Step 4; the gap is
purely that nothing enforces it at the moment the round is assembled.

Related memory written the same day in the countoff project store:
`a-recommendation-means-dont-ask`.
