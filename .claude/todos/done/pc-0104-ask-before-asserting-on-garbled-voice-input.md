<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Ask before asserting when voice-dictated context is garbled or ambiguous

**Type:** skill-improvement

## Goal

Close an enforcement gap: when a dev's voice-transcribed message is garbled/self-correcting and touches either (a) two similarly-named but distinct systems, or (b) who has decision authority, Claude should stop and ask via `AskUserQuestion` instead of asserting a recommendation.

## Context

Session 2026-08-04/05 (zng-app, Johanna/Amplitude thread). Joe asked how to answer Johanna about Amplitude event tracking for biller/partner registrations. Claude answered by citing an unrelated BE feature (the `partnerSlug`/`billerGroupSlug` field PATCHed onto the user record, ticket 54840) instead of the FE Amplitude event Johanna actually asked about - conflating two systems that share vocabulary. Joe corrected: "did you not read the whole chat... why would you tell her, oh, hey, you no longer need to do it?"

Joe then gave a garbled voice-dictated explanation (visible repetition/self-correction in the transcript: "th things... some things... things as logged through frontend and some through backend") about Peter's preference. Claude asserted "Peter wants this, so let's do a dedicated event" - Joe corrected again: "Its not peters decision... Dw bout it. Ill figure it out," i.e. Claude over-read "Peter wants X" as "Peter decides X," and Joe abandoned the thread rather than correct a third time.

Full memory of the incident: `feedback_reverify_garbled_voice_context_before_asserting` in this project's Auto Memory.

No single skill file owns this - it's a gap in CLAUDE.md's "front-load all questions... never assume" rule combined with the existing `feedback_dont_present_inference_as_finding` and `feedback_slack_msg_drafting_scope` memories, none of which currently flag "garbled/voice-transcribed input" or "two similarly-named systems" as an explicit trigger to ask rather than assert.

## Approach

Not a code change - a rule-authoring task. Options to weigh:

1. Add an explicit trigger to the global CLAUDE.md question-gating rule (or a new snippet) naming "voice-dictated/garbled input" and "two systems with overlapping vocabulary" as conditions that force an `AskUserQuestion` before drafting anything stakeholder-facing.
2. Fold it into `feedback_slack_msg_drafting_scope.md` as a new numbered point, since the trigger (Joe hands over context, asks "how do I answer") is identical to that memory's scope.

Leaning toward (2) since it's the same actual workflow trigger already documented there - just add a point about re-grepping which system is being discussed and not upgrading "X wants Y" into "X decided Y" when the source is a garbled dictation. Don't draft new skill files inline; this todo is the surfaced candidate, not the fix.

## Acceptance

- The rule change (wherever it lands) explicitly names both failure triggers from this incident: system conflation and decision-authority over-reading from garbled voice input.
- A future similar garbled-voice, multi-system question results in a clarifying `AskUserQuestion` before any draft is produced.

## Notes

This is a repeat pattern of an existing memory category (inference presented as finding), not a brand-new failure mode - so the fix is likely a targeted addition to existing memory/rule text rather than a wholly new mechanism.
- Dropped via /cleanup-todos 2026-08-11: already done - feedback_reverify_garbled_voice_context_before_asserting.md already written. Confirmed by dev 2026-08-11.
