<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=5, reconfirm-count=1, content-hash=40bbb256 -->
<!-- duplicate-checked: the guard's five hits are vocabulary-only overlaps on generic words (step, skipped, silently, question, best) and none share this subject - 232 is clockify token rotation, 105 is the commit skill's step 1 enforcement gap, 242 is brainstorm's ask gate, 25 is AskUserQuestion badge labels, 29 is create-pr's foreground flag. The subject-keyed check against this backlog and its done/ is recorded in the Notes section below. -->
# clockify-reconciliator step 9a: a skipped "best-effort" visual should be flagged as a question, not decided silently

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/clockify-reconciliator` runs from unilaterally dropping the step 9a week-calendar visual
for effort/time reasons without surfacing that tradeoff to the dev first.

## Context

2026-09-03 run: after building and triple-verifying a 21-entry reconciliation plan, decided on my
own to skip building the step 9a HTML week calendar ("prioritized getting times exactly right over
building it") and told the dev so in the apply-decision message. The dev came back explicitly
asking to see it ("actually, before doing it, id love to see a visual breakdown"), so it got built
anyway, one round-trip later than necessary.

The skill's own wording for step 9a already says "best-effort" for the visual, which reads as
license to skip under time pressure - but the global CLAUDE.md rule ("Front-load all questions
before starting work, trivial or not... any pre-edit decision point") should have caught this: an
effort/scope tradeoff on a spec'd deliverable is exactly the kind of decision point that's
supposed to be asked about, not picked silently, even when the skill's own language sounds
permissive.

## Approach

- Reword `skills/clockify-reconciliator/SKILL.md` step 9a's "best-effort" framing so skipping it
  for effort reasons (as opposed to the tool being genuinely unavailable) requires a quick
  check-in rather than reading as ambient permission to drop it. Something like: "best-effort"
  covers tool unavailability (no `show_preview`/no working hook endpoint) - it does NOT cover
  choosing to skip it because the plan took a while to build; that case still needs the dev's
  go-ahead, same as any other scope cut.
- Alternative considered: leave the skill wording alone and treat this purely as a personal
  execution habit (don't silently narrow scope on a spec'd artifact, ever, regardless of how the
  spec words the exception) - lower blast radius fix, no skill file edit needed. Worth deciding
  which approach before implementing either.

## Acceptance

- A future `/clockify-reconciliator` run that considers skipping the visual either builds it
  anyway or asks first, rather than deciding and only telling the dev after the fact.

## Notes

Low-stakes here (cost was one extra round-trip), but the underlying pattern (interpreting a
skill's "best-effort"/optional language as license to skip a scope-affecting decision without
asking) is worth catching before it happens on a higher-stakes deliverable.

Relocated from todo 126 in `C:\Users\tecno\Desktop\Projects\zng-app` via /cleanup-todos 2026-09-05:
`clockify-reconciliator` is a global skill living under `~/.claude`, with no zng-app-specific
content, so a finding about it belongs in this repo's backlog per root CLAUDE.md. Content-duplicate
check against this backlog and its `done/` found no live or completed match on the subject: the
nearest are `done/905-clockify-visual-claims-weekly-remaining-on-a-single-day-run.md` (the target
bar's full-week gate) and `done/89-clockify-skill-weekly-screenshot-spec.md` (the HubStaff weekly
screenshot spec), both different subjects.
